"""
Transactional email via Azure Communication Services (ACS) Email.

Required environment variables:
  ACS_EMAIL_CONNECTION_STRING  — from ACS resource ``lexmateph-comms`` → Keys → Connection string
  ACS_SENDER_EMAIL             — any **verified** sender, e.g.
                                 DoNotReply@<guid>.azurecomm.net (default Azure domain), or
                                 e.g. DoNotReply@lexmateph.com (after custom domain is verified)

**Using your own mail domain (e.g. lexmateph.com for the site https://www.lexmateph.com):**
  Email is sent from addresses on the **apex** domain (``@lexmateph.com``), not the ``www.``
  website hostname. The app only reads ``ACS_SENDER_EMAIL``; no code change is required
  after Azure + DNS are done.

  In this subscription, the Email Communication Service is ``lexmateph-email`` (resource group
  ``LexMatePH``). It currently has only the Azure-managed domain (``.azurecomm.net``). To add
  ``lexmateph.com``:
  1) Azure Portal: open ``lexmateph-email`` → Email → **Domains** → **Add domain** → choose
     customer-managed domain, or use ``az communication email domain create`` with
     ``--domain-management CustomerManaged`` (CLI extension: communication, preview).
  2) In your DNS (where **lexmateph.com** is hosted), add the **TXT** / **SPF** / **DKIM**
     records shown in the portal. Wait until all verification steps show *Verified*.
  3) Add a **MailFrom** address in Azure (e.g. local part ``DoNotReply``), or
     ``az communication email domain sender-username create`` for the new domain resource.
  4) Set ``ACS_SENDER_EMAIL`` to the full address (e.g. ``DoNotReply@lexmateph.com``) in
     ``local.settings.json`` and in the **Function App** application settings in Azure.
  5) Keep using the same ``ACS_EMAIL_CONNECTION_STRING`` from ``lexmateph-comms``.

  See: https://learn.microsoft.com/en-us/azure/communication-services/concepts/email/prepare-email-communication-resource

The azure-communication-email package must be in requirements.txt.
If the env vars are not set the functions are no-ops (log a warning only)
so missing config never crashes a payment webhook.
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://lexmateph.com").rstrip("/")
_ADMIN_NOTIFY_EMAIL = "rnlarboleda18@gmail.com"


def _get_client():
    """Return an ACS EmailClient, or None if not configured."""
    conn_str = (os.environ.get("ACS_EMAIL_CONNECTION_STRING") or "").strip()
    if not conn_str:
        logger.warning("ACS_EMAIL_CONNECTION_STRING not set — email skipped")
        return None
    try:
        from azure.communication.email import EmailClient
        return EmailClient.from_connection_string(conn_str)
    except ImportError:
        logger.warning(
            "azure-communication-email not installed — email skipped. "
            "Add it to requirements.txt."
        )
        return None
    except Exception as e:
        logger.error("ACS EmailClient init failed: %s", e)
        return None


def _sender() -> str:
    return (os.environ.get("ACS_SENDER_EMAIL") or "").strip()


# ─── Templates ────────────────────────────────────────────────────────────────

def _cancellation_html(tier_label: str, access_until: str, resubscribe_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Your LexMatePH subscription has been cancelled</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#7c3aed 0%,#6d28d9 50%,#4f46e5 100%);
                        padding:32px 40px;text-align:center;">
              <h1 style="margin:0;font-size:26px;font-weight:800;color:#ffffff;
                          letter-spacing:-0.5px;">LexMate<span style="color:#fbbf24;">PH</span></h1>
              <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);
                         letter-spacing:0.08em;text-transform:uppercase;font-weight:600;">
                Your All-in-One Legal Companion
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 40px 28px;">
              <h2 style="margin:0 0 12px;font-size:20px;font-weight:700;color:#1e1b4b;">
                We&rsquo;re sorry to see you go 😔
              </h2>
              <p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#374151;">
                Your <strong style="color:#7c3aed;">{tier_label}</strong> subscription has been
                successfully cancelled. No further charges will be made to your payment method.
              </p>

              <!-- Access Until Box -->
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#faf5ff;border:1.5px solid #ddd6fe;border-radius:12px;
                             margin-bottom:24px;">
                <tr>
                  <td style="padding:18px 24px;">
                    <p style="margin:0 0 4px;font-size:12px;font-weight:700;
                               text-transform:uppercase;letter-spacing:0.1em;color:#7c3aed;">
                      You still have full access until
                    </p>
                    <p style="margin:0;font-size:22px;font-weight:800;color:#4c1d95;">
                      {access_until}
                    </p>
                    <p style="margin:6px 0 0;font-size:13px;color:#6b7280;">
                      After this date, your account will automatically move to the Free plan.
                      Your progress, bookmarks, and history are always saved.
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 8px;font-size:15px;line-height:1.7;color:#374151;">
                Bar exams don&rsquo;t wait — and neither does your preparation. Whenever you&rsquo;re
                ready to get back on track, resubscribing takes less than a minute.
              </p>
              <p style="margin:0 0 28px;font-size:15px;line-height:1.7;color:#374151;">
                Your <strong>case digests, flashcard progress, and LexPlay history</strong> are
                all still here waiting for you. ✨
              </p>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding-bottom:28px;">
                    <a href="{resubscribe_url}"
                       style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#4f46e5);
                               color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;
                               padding:14px 36px;border-radius:12px;
                               box-shadow:0 4px 12px rgba(124,58,237,0.35);">
                      Resume My Subscription →
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 8px;font-size:13px;color:#9ca3af;text-align:center;">
                Questions? Reply to this email or reach us at
                <a href="mailto:support@lexmateph.com"
                   style="color:#7c3aed;text-decoration:none;">support@lexmateph.com</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                        padding:20px 40px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
                LexMatePH &bull; Philippine Legal Study Platform<br/>
                You&rsquo;re receiving this because you cancelled your subscription.<br/>
                &copy; 2026 LexMatePH. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _cancellation_text(tier_label: str, access_until: str, resubscribe_url: str) -> str:
    return f"""Your LexMatePH {tier_label} subscription has been cancelled.

We're sorry to see you go!

IMPORTANT: You still have full {tier_label} access until {access_until}.
After that date your account moves to the Free plan automatically — no action needed.

Your case digests, flashcard progress, and LexPlay history are all saved.

Whenever you're ready to get back to your bar prep, resubscribing takes less than a minute:
{resubscribe_url}

Questions? Email us at support@lexmateph.com

— The LexMatePH Team
"""


# ─── Public API ───────────────────────────────────────────────────────────────

def send_cancellation_email(
    to_email: str,
    tier_label: str,
    access_until: str,
) -> bool:
    """
    Send a subscription cancellation notice to the user.

    Args:
        to_email:     recipient email address
        tier_label:   human-readable plan name, e.g. "Barrister"
        access_until: formatted date string, e.g. "June 25, 2026"

    Returns True on success, False on any failure (non-blocking).
    """
    client = _get_client()
    sender = _sender()
    if not client or not sender:
        return False

    resubscribe_url = f"{_FRONTEND_URL}/decisions?subscribe=barrister_monthly"

    try:
        message = {
            "senderAddress": sender,
            "recipients": {"to": [{"address": to_email}]},
            "content": {
                "subject": "Your LexMatePH subscription has been cancelled",
                "html": _cancellation_html(tier_label, access_until, resubscribe_url),
                "plainText": _cancellation_text(tier_label, access_until, resubscribe_url),
            },
        }
        poller = client.begin_send(message)
        result = poller.result()
        logger.info(
            "Cancellation email sent to %s — messageId=%s",
            to_email,
            result.get("id") if isinstance(result, dict) else result,
        )
        return True
    except Exception as e:
        logger.error("send_cancellation_email failed for %s: %s", to_email, e)
        return False


# ─── Founding promo admin notification ────────────────────────────────────────

def _founding_promo_notify_html(user_name: str, user_email: str, slot: int | None) -> str:
    slot_label = f"#{slot}" if slot else "—"
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>New Founding Member</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:16px;overflow:hidden;
                      box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:600px;width:100%;">
          <tr>
            <td style="background:linear-gradient(135deg,#7c3aed 0%,#6d28d9 50%,#4f46e5 100%);
                        padding:32px 40px;text-align:center;">
              <h1 style="margin:0;font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">
                LexMate<span style="color:#fbbf24;">PH</span>
              </h1>
              <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);
                         letter-spacing:0.08em;text-transform:uppercase;font-weight:600;">
                Admin Notification
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:36px 40px 28px;">
              <h2 style="margin:0 0 16px;font-size:20px;font-weight:700;color:#1e1b4b;">
                New Founding Member Registered
              </h2>
              <table width="100%" cellpadding="0" cellspacing="0"
                     style="background:#faf5ff;border:1.5px solid #ddd6fe;border-radius:12px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0 0 8px;font-size:13px;font-weight:700;text-transform:uppercase;
                               letter-spacing:0.1em;color:#7c3aed;">Founding Slot</p>
                    <p style="margin:0 0 16px;font-size:28px;font-weight:800;color:#4c1d95;">{slot_label}</p>
                    <p style="margin:0 0 4px;font-size:13px;color:#6b7280;font-weight:600;">Name</p>
                    <p style="margin:0 0 12px;font-size:15px;color:#111827;">{user_name}</p>
                    <p style="margin:0 0 4px;font-size:13px;color:#6b7280;font-weight:600;">Email</p>
                    <p style="margin:0 0 12px;font-size:15px;color:#111827;">{user_email}</p>
                    <p style="margin:0 0 4px;font-size:13px;color:#6b7280;font-weight:600;">Registered at</p>
                    <p style="margin:0;font-size:15px;color:#111827;">{now_str}</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:20px 40px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
                LexMatePH Admin &bull; Automated notification
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _founding_promo_notify_text(user_name: str, user_email: str, slot: int | None) -> str:
    slot_label = f"#{slot}" if slot else "—"
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    return f"""[LexMatePH] New Founding Member

Slot:       {slot_label}
Name:       {user_name}
Email:      {user_email}
Registered: {now_str}

— LexMatePH Admin Notification
"""


def send_founding_promo_notification(
    user_name: str,
    user_email: str,
    slot: int | None,
) -> bool:
    """Notify the admin when a new founding promo member registers. Non-blocking."""
    client = _get_client()
    sender = _sender()
    if not client or not sender:
        return False

    slot_label = f"Slot #{slot}" if slot else "New Member"
    try:
        message = {
            "senderAddress": sender,
            "recipients": {"to": [{"address": _ADMIN_NOTIFY_EMAIL}]},
            "content": {
                "subject": f"[LexMatePH] New Founding Member — {slot_label}: {user_name}",
                "html": _founding_promo_notify_html(user_name, user_email, slot),
                "plainText": _founding_promo_notify_text(user_name, user_email, slot),
            },
        }
        poller = client.begin_send(message)
        result = poller.result()
        logger.info(
            "Founding promo notification sent for %s slot=%s — messageId=%s",
            user_email,
            slot,
            result.get("id") if isinstance(result, dict) else result,
        )
        return True
    except Exception as e:
        logger.error("send_founding_promo_notification failed for %s: %s", user_email, e)
        return False
