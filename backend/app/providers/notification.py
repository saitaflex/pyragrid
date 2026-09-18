"""notification.py — NotificationProvider interface + OutboxProvider (§5.1, §5.7).

Email outbox only in the MVP. Replay never sends real email.
"""
from __future__ import annotations

from app import config
from app.models import Alert, OutboxEmail


class NotificationProvider:
    def email_for(self, alert: Alert, customer_id: str) -> OutboxEmail:
        raise NotImplementedError


class OutboxProvider(NotificationProvider):
    def email_for(self, alert: Alert, customer_id: str) -> OutboxEmail:
        to = config.NOTIFY_TO.get(customer_id, f"ops@{customer_id}.example")
        return OutboxEmail(
            alert_id=alert.alert_id,
            to=to,
            subject=f"[{alert.to_level}] {alert.site_name}: {alert.headline}",
            body=(f"{alert.site_name} escalated {alert.from_level} -> {alert.to_level} "
                  f"at {alert.at} (score {alert.score}). "
                  f"Open the platform for factors and actions."),
            channel="email",
            status="outbox",
        )
