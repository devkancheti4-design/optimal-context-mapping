# Payments service

The payments service charges customer cards for orders. Failed charges are retried with exponential backoff.
A declined card is never retried. Refunds are handled by the separate refunds service, owned by the billing team.
Run the tests with `pytest -q` from the repository root.
