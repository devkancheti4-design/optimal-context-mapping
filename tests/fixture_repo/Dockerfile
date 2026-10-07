FROM python:3.12-slim
WORKDIR /app
COPY src/ /app/src/
# Four workers serve the payments API.
CMD ["fastapi", "run", "--workers", "4", "src/payments.py"]
