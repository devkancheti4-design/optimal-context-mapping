from .config import MAX_CHARGE_RETRIES, RETRY_BACKOFF_SECONDS
import time


class ChargeDeclined(Exception):
    """Raised when the card network declines a charge for good (no retry will help)."""


def charge(card, amount, gateway):
    """Charge a card, retrying transient gateway errors with exponential backoff."""
    delay = RETRY_BACKOFF_SECONDS
    for attempt in range(MAX_CHARGE_RETRIES + 1):
        result = gateway.charge(card, amount)
        if result.ok:
            return result.id
        if result.code == "declined":
            raise ChargeDeclined(result.message)
        time.sleep(delay)
        delay *= 2
    raise TimeoutError("gateway kept failing")
