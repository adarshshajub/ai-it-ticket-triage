import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.conf import settings
from imapclient import IMAPClient
from email import message_from_bytes
from email.utils import parseaddr
from tickets.utils.extractmail import decode_header_value, get_email_body
from tickets.views import email_ticket_create
from account.utils.emailuser import get_or_create_user_by_email

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def email_monitoring():
    """ Monitor inbox, create tickets, and send reply emails """
    account_key = "support"
    accounts = getattr(settings, "EMAIL_ACCOUNTS", {})
    config = accounts[account_key]
    host = settings.EMAIL_IMAP_HOST
    username = config["EMAIL_HOST_USER"]
    password = config["EMAIL_HOST_PASSWORD"]

    logger.info("Started the mail monitoring...")

    try:
        with IMAPClient(host, ssl=True) as client:
            client.login(username, password)
            logger.info("Logged in to IMAP as %s", username)

            client.select_folder("INBOX", readonly=False)
            uids = client.search(["UNSEEN"])
            logger.debug("Found %d unseen messages", len(uids))

            for uid in uids:
                data = client.fetch(uid, ["RFC822"])
                raw = data[uid][b"RFC822"]
                msg = message_from_bytes(raw)

                subject = decode_header_value(msg["Subject"])
                body = get_email_body(msg)
                sender = parseaddr(msg["From"])[1]

                logger.debug("\n" + "=" * 60)
                logger.debug(f"Processing email UID {uid}")
                logger.debug(f"From: {sender}")
                logger.debug(f"Subject: {subject}")

                user = User.objects.filter(email__iexact=sender).first()
                if not user:
                    user, reset_url = get_or_create_user_by_email(
                        sender, True, account_key
                    )

                ticket, email_ticket = email_ticket_create(
                    email_uid=uid,
                    sender=sender,
                    subject=subject,
                    body=body,
                    raw_email=raw.decode("utf8", errors="replace"),
                    user=User.objects.filter(email__iexact=sender).first(),
                    account_key=account_key,
                )

                # Mark as seen
                client.add_flags(uid, [r"\Seen"])
                logger.info("Email UID %s marked as seen.", uid)
                logger.info("Processed email UID %s.", uid)

    except Exception as e:
        logger.error("Exception in monitoring loop: %s", str(e))

