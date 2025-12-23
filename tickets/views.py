import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import Ticket, EmailTicket
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from .forms import TicketForm, TicketAdminEditForm
from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from .utils.mailer import send_email_reply
from ai.views import predict_category, predict_category_confidence, predict_priority, predict_priority_confidence

logger = logging.getLogger(__name__)


# create the ticket view from user input
@login_required
def ticket_create(request):
    logger.info("Ticket create view accessed.")
    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            # Predict category
            try:
                ai_input_txt = ticket.title + " " + ticket.description
                ticket.category = predict_category(ai_input_txt)
                ticket.category_confidence = round(predict_category_confidence(ai_input_txt),4)
                ticket.priority = predict_priority(ai_input_txt)
                ticket.priority_confidence = round(predict_priority_confidence(ai_input_txt),4)
                logger.info(f"Predicted category: {ticket.category}, Predicted category confidence: {ticket.category_confidence}, Predicted priority: {ticket.priority}, Predicted priority confidence: {ticket.priority_confidence}")
            except Exception as e:
                logger.error(f"ML prediction failed: {e}")
                if not ticket.category:
                    ticket.category = "application"

            # Save with pending status
            ticket.ticket_creation_status = "pending"
            ticket.created_by = request.user
            ticket.save()

            logger.info(f"Ticket #{ticket.id} created")

            # Redirect to waiting page that will poll for status
            return redirect("tickets:ticket_processing", ticket_id=ticket.id)
        else:
            logger.warning(f"Form validation failed: {form.errors}")
    else:
        form = TicketForm()

    return render(request, "tickets/submit_issues.html", {"form": form})

# create ticket from email
def email_ticket_create(email_uid, sender, subject, body, raw_email, user, account_key):
    logger.info("Email ticket view accessed.")

    # check if email ticket with uid already exists
    email_ticket = EmailTicket.objects.filter(uid=email_uid).first()
    if email_ticket and email_ticket.ticket:
        logger.debug(f"Email ticket with UID {email_uid} already exists.")
        return email_ticket.ticket, email_ticket

    # create the ticket if not exists
    ai_input_txt =  subject + " " + body
    predicted_category = predict_category(ai_input_txt)
    predicted_category_confidence = round(predict_category_confidence(ai_input_txt),4)
    predicted_priority = predict_priority(ai_input_txt)
    predicted_priority_confidence = round(predict_priority_confidence(ai_input_txt),4)

    logger.debug(f"Creating ticket for email UID {email_uid} from sender {sender}")
    with transaction.atomic():
        ticket = Ticket.objects.create(
            title=subject[:200] if subject else "No subject",
            description=body or "",
            category=predicted_category or "Application",
            category_confidence=predicted_category_confidence,
            priority=predicted_priority,
            priority_confidence=predicted_priority_confidence,
            created_by=user,  
            request_type="email",
        )
    logger.debug(f"Ticket #{ticket.id} created for email UID {email_uid}")

    logger.debug(f"Creating EmailTicket for UID {email_uid}")
    email_ticket, created = EmailTicket.objects.get_or_create(
        uid=email_uid,
        defaults={
            "sender": sender,
            "subject": subject,
            "body": body,
            "raw_email": raw_email,
            "ticket": ticket,
            "received_at": timezone.now(),
        },
    )
    logger.debug(f"EmailTicket for UID {email_uid} created.")

    logger.debug(f"Linking EmailTicket UID {email_uid} to Ticket #{ticket.id}")
    if not created and email_ticket.ticket is None:
        email_ticket.ticket = ticket
        email_ticket.save(update_fields=["ticket"])
        logger.debug(f"Linked EmailTicket UID {email_uid} to Ticket #{ticket.id}")

    logger.debug(f"Sending email reply to {sender} with ticket number.")
    ticket_number = Ticket.objects.filter(id=ticket.id).first().servicenow_ticket_number
    send_email_reply(account_key, ticket_number, sender, subject)
    logger.debug(f"Email reply sent to {sender} for Ticket #{ticket.id}")
    return ticket, email_ticket

# Ticket processing view - shows status while syncing
@login_required
def ticket_processing(request, ticket_id):
    logger.info(f"Ticket processing view accessed for ticket ID: {ticket_id}")
    ticket = get_object_or_404(Ticket, id=ticket_id)
    # If already processed, redirect to appropriate page
    if ticket.ticket_creation_status == "created":
        return redirect("tickets:ticket_success", ticket_id=ticket.id)
    elif ticket.ticket_creation_status == "failed":
        return redirect("tickets:ticket_error", ticket_id=ticket.id)

    context = {"ticket": ticket, "ticket_number": ticket.servicenow_ticket_number}

    return render(request, "tickets/processing.html", context)

# Ticket success view
@login_required
def ticket_success(request, ticket_id):
    logger.info(f"Ticket success view accessed for ticket ID: {ticket_id}")
    ticket = get_object_or_404(Ticket, id=ticket_id)
    # Ensure ticket is actually synced
    if ticket.ticket_creation_status != "created":
        return redirect("tickets:ticket_processing", ticket_id=ticket.id)
    context = {"ticket": ticket, "ticket_number": ticket.servicenow_ticket_number}
    return render(request, "tickets/success.html", context)

# Ticket success view
@login_required
def ticket_error(request, ticket_id):
    logger.info(f"Ticket error view accessed for ticket ID: {ticket_id}")
    ticket = get_object_or_404(Ticket, id=ticket_id)
    # Ensure ticket actually failed
    if ticket.ticket_creation_status == "created":
        return redirect("tickets:ticket_success", ticket_id=ticket.id)
    context = {
        "ticket": ticket,
        "error": ticket.error_message or "Failed to sync with ServiceNow",
    }

    return render(request, "tickets/error.html", context)

# Check ticket status API 
@login_required
def check_ticket_status_api(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return JsonResponse(
        {
            "status": ticket.ticket_creation_status,
            "servicenow_number": ticket.servicenow_ticket_number,
            "sync_attempts": ticket.sync_attempts,
            "error_message": ticket.error_message,
        }
    )

# Retry ticket sync view
@login_required
def retry_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.ticket_creation_status in ["failed", "pending"]:
        ticket.sync_attempts = 0
        ticket.ticket_creation_status = "pending"
        ticket.save()

        # sync_ticket_to_servicenow(ticket.id, retry_count=0, schedule=0)
        return redirect("tickets:ticket_processing", ticket_id=ticket_id)
    else:
        messages.info(
            request, f"Ticket #{ticket_id} is already {ticket.ticket_creation_status}"
        )
        return redirect("tickets:ticket_list")


# Ticket list view with filters and pagination
@login_required
def ticket_list(request):
    user = request.user
    logger.info("Ticket list view accessed.")
    page_number = request.GET.get("page", 1)
    if user.is_staff:
        all_user_qs = Ticket.objects.all().order_by("-created_at")
    else:
        all_user_qs = Ticket.objects.filter(created_by=user).order_by("-created_at")

    category_filter = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "").strip()
    search_q = request.GET.get("q", "").strip()

    if category_filter:
        all_user_qs = all_user_qs.filter(category=category_filter)
    if status_filter:
        all_user_qs = all_user_qs.filter(ticket_creation_status=status_filter)
    if search_q:
        all_user_qs = all_user_qs.filter(
            Q(title__icontains=search_q)
            | Q(description__icontains=search_q)
            | Q(servicenow_ticket_number__icontains=search_q)
        )

    paginator = Paginator(all_user_qs, 10)  # 8 tickets per page
    page_obj = paginator.get_page(page_number)
    tickets_page = page_obj.object_list
    context = {
        "tickets": tickets_page,
        "is_paginated": page_obj.has_other_pages(),
        "page_obj": page_obj,
        "now": timezone.now(),
    }
    return render(request, "tickets/ticket_list.html", context)

# Ticket detail view
@login_required
def ticket_detail(request, ticket_id):
    logger.info(f"Ticket detail view accessed for ticket ID: {ticket_id}")
    ticket = get_object_or_404(Ticket, id=ticket_id)

    user_tickets = Ticket.objects.filter(created_by=request.user)
    if not request.user.is_staff and ticket not in user_tickets:
        raise PermissionDenied("You do not have permission to view this ticket.")

    return render(request, "tickets/ticket_detail.html", {"ticket": ticket})

# Admin ticket edit view
@staff_member_required
def ticket_edit(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    try:
        if request.method == "POST":
            form = TicketAdminEditForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save()
                messages.success(request, f"Ticket #{ticket.id} updated successfully.")
                return redirect("tickets:ticket_detail", ticket.id)
        else:
            form = TicketAdminEditForm(instance=ticket)
    except Exception as e:
        logger.error(f"Error editing ticket #{ticket.id}: {e}")
        messages.error(request, "An error occurred while updating the ticket.")
        return redirect("tickets:ticket_detail", ticket.id)

    return render(request, "tickets/ticket_edit.html", {"form": form, "ticket": ticket})

# Admin ticket update view 
@staff_member_required
@require_POST
def admin_update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Read posted values (use .get to allow partial updates)
    status = request.POST.get("ticket_creation_status")
    assigned_team = request.POST.get("assigned_team")
    servicenow_ticket_number = request.POST.get("servicenow_ticket_number")

    changed = False

    # Validate status against defined choices
    if status is not None:
        valid_statuses = [s[0] for s in Ticket.STATUS_CHOICES]
        if status not in valid_statuses:
            if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
                return JsonResponse(
                    {"ok": False, "error": "invalid_status"}, status=400
                )
            else:
                raise ValidationError("Invalid status value")

        if status != ticket.ticket_creation_status:
            ticket.ticket_creation_status = status
            changed = True

    if assigned_team is not None and assigned_team != ticket.assigned_team:
        ticket.assigned_team = assigned_team
        changed = True

    if (
        servicenow_ticket_number is not None
        and servicenow_ticket_number != ticket.servicenow_ticket_number
    ):
        ticket.servicenow_ticket_number = servicenow_ticket_number
        changed = True

    if changed:
        ticket.save()
        messages.success(request, f"Ticket #{ticket.id} updated successfully.")

    # return JSON with a display label for status
    if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
        # compute human-readable status (get_status_display assumes field is 'ticket_creation_status')
        try:
            status_display = ticket.get_ticket_creation_status_display()
        except Exception:
            # fallback: attempt generic get_<field>_display or just use the raw value
            status_display = getattr(ticket, "ticket_creation_status", "")

        return JsonResponse(
            {"ok": True, "ticket_id": ticket.pk, "status_display": status_display}
        )

    # fallback redirect to admin dashboard or referrer
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)