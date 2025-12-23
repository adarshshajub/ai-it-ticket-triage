import logging
import json
from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from tickets.models import Ticket
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from django.db.models import Count
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

# Admin dashboard view with stats and charts
def admin_dashboard(request):
    logger.info("Admin dashboard accessed.")
    if request.user.is_staff:
        # --- Handle simple GET filters ---
        category_filter = request.GET.get("category", "").strip()
        status_filter = request.GET.get("status", "").strip()
        # days window for time-series charts (default 7)
        try:
            days = int(request.GET.get("days", 7))
            if days < 1 or days > 90:
                days = 7
        except ValueError:
            days = 7

        # Base queryset (all tickets)
        qs = Ticket.objects.all()

        # Apply filters
        if category_filter:
            qs = qs.filter(category=category_filter)
        if status_filter:
            qs = qs.filter(ticket_creation_status=status_filter)

        total_tickets = Ticket.objects.count()
        new_tickets = Ticket.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        filtered_total = qs.count()  # total after filter (for the table)
        pending_tickets = Ticket.objects.filter(ticket_creation_status="pending").count()
        created_tickets = Ticket.objects.filter(ticket_creation_status="created").count()
        failed_tickets = Ticket.objects.filter(ticket_creation_status="failed").count()
        # open = not final states (customize as needed)
        open_tickets = Ticket.objects.exclude(
            servicenow_ticket_status__in=["resolved", "closed", "cancelled"]
        ).count()
        email_tickets = Ticket.objects.filter(request_type="email").count()

        # Model accuracy placeholder - replace with real metric storage if available
        model_accuracy = getattr(request, "model_accuracy", None) or 87.5

        # Tickets by category (in choice order)
        cat_qs = Ticket.objects.values("category").annotate(count=Count("id"))
        CATEGORY_ORDER = [c[0] for c in Ticket.CATEGORY_CHOICES]
        CATEGORY_LABELS = {c[0]: c[1] for c in Ticket.CATEGORY_CHOICES}
        category_counts_map = {item["category"] or "": item["count"] for item in cat_qs}
        category_labels = [CATEGORY_LABELS.get(k, k.title()) for k in CATEGORY_ORDER]
        category_counts = [category_counts_map.get(k, 0) for k in CATEGORY_ORDER]

        # Tickets by assignment group (top 8)
        group_counts = (
            Ticket.objects.values("assignment_group_id", "assigned_team")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )

        # Top reporters (users who created most tickets) - requires created_by relation
        top_reporters = (
            Ticket.objects.values("created_by__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )

        # Time series: tickets per day for last `days`
        today = timezone.localdate()
        time_labels = []
        time_counts = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            time_labels.append(d.strftime("%b %d"))
            # Count using date part to be timezone-safe
            time_counts.append(Ticket.objects.filter(created_at__date=d).count())

        # Recent tickets and recent errors
        recent_tickets = Ticket.objects.order_by("-created_at")[:5]
        recent_errors = Ticket.objects.filter(ticket_creation_status="failed").order_by(
            "-last_sync_attempt"
        )[:10]

        # Paginated table (apply filters)
        page_number = request.GET.get("page", 1)
        paginator = Paginator(qs.order_by("-created_at"), 5)  # adjust per-page
        page_obj = paginator.get_page(page_number)
        tickets_page = page_obj.object_list

        # ServiceNow sync stats & success rate
        created_count = created_tickets
        failed_count = failed_tickets
        snow_success_rate = (
            round((created_count / (created_count + failed_count) * 100), 1)
            if (created_count + failed_count) > 0
            else 0
        )
        last_sync_obj = (
            Ticket.objects.exclude(last_sync_attempt__isnull=True)
            .order_by("-last_sync_attempt")
            .first()
        )
        snow_last_sync = last_sync_obj.last_sync_attempt if last_sync_obj else None

        # Keep query params for pagination links
        query_params = request.GET.copy()
        if "page" in query_params:
            query_params.pop("page")
        query_string = query_params.urlencode()

        context = {
            # counts
            "total_tickets": total_tickets,
            "new_tickets": new_tickets,
            "filtered_total": filtered_total,
            "pending_tickets": pending_tickets,
            "open_tickets": open_tickets,
            "created_tickets": created_tickets,
            "failed_tickets": failed_tickets,
            "email_tickets": email_tickets,
            # model / chart data
            "model_accuracy": model_accuracy,
            "category_labels": mark_safe(json.dumps(category_labels)),
            "category_counts": mark_safe(json.dumps(category_counts)),
            "time_labels": mark_safe(json.dumps(time_labels)),
            "time_counts": mark_safe(json.dumps(time_counts)),
            # lists
            "recent_tickets": recent_tickets,
            "recent_errors": recent_errors,
            "group_counts": group_counts,
            "top_reporters": top_reporters,
            # pagination & table
            "tickets": tickets_page,
            "is_paginated": page_obj.has_other_pages(),
            "page_obj": page_obj,
            "query_string": query_string,
            # ServiceNow metrics
            "snow_synced": created_count,
            "snow_errors": failed_count,
            "snow_last_sync": snow_last_sync,
            "snow_success_rate": snow_success_rate,
            # UI helpers
            "last_updated": timezone.now().strftime("%Y-%m-%d %H:%M"),
            "now": timezone.now(),
        }

        return render(request, "admin_dashboard.html", context)
    else:
        return redirect("dashboard:user_dashboard")

# User dashboard view with personal stats
@login_required
def user_dashboard(request):
    user = request.user
    if user.is_staff:
        return redirect("dashboard:admin_dashboard")
    else:
        logger.info(f"User dashboard accessed by {user.username}")
        # Aggregates for current user
        total_by_user = Ticket.objects.filter(created_by=user).count()
        open_by_user = (
            Ticket.objects.filter(created_by=user)
            .exclude(servicenow_ticket_status__in=["closed", "resolved", "cancelled"])
            .count()
        )
        resolved_issue = (
            Ticket.objects.filter(created_by=user)
            .filter(servicenow_ticket_status__in=["closed", "resolved", "cancelled"])
            .count()
        )
        recent_tickets = (
            Ticket.objects.filter(created_by=user).order_by("-created_at")[:1].count()
        )

        # Paginate user's all tickets (optional, for "my tickets" view on same page)
        page_number = request.GET.get("page", 1)
        all_user_qs = Ticket.objects.filter(created_by=user).order_by("-created_at")
        paginator = Paginator(all_user_qs, 6)
        page_obj = paginator.get_page(page_number)
        tickets_page = page_obj.object_list

        context = {
            "total_by_user": total_by_user,
            "open_by_user": open_by_user,
            "resolved_tickets": resolved_issue,
            "recent_tickets": recent_tickets,
            "tickets": tickets_page,
            "is_paginated": page_obj.has_other_pages(),
            "page_obj": page_obj,
            "now": timezone.now(),
        }
        return render(request, "user_dashboard.html", context)
