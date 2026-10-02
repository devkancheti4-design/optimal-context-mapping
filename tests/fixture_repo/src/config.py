"""Settings for the payments service."""

# How many times a failed card charge is retried before the order is marked failed.
MAX_CHARGE_RETRIES = 3

# Seconds to wait between retries; doubles after each attempt.
RETRY_BACKOFF_SECONDS = 2

DEFAULT_CURRENCY = "INR"
