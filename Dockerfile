# Model D team server: maps the repositories mounted at /repos and serves the shared workspace on port 7700.
# The embedding model is fetched while the image builds, so the running server never reaches the internet.
#   docker compose up -d            (see docker-compose.yml and DEPLOY.md)
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 HF_HOME=/opt/modeld/hf PYTHONUNBUFFERED=1

# CPU build of PyTorch keeps the image small; the embedding model runs on CPU.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY pyproject.toml README.md LICENSE NOTICE THIRD_PARTY_NOTICES /src/
COPY ocm /src/ocm
RUN pip install /src && rm -rf /src && modeld fetch-model

ENV OCM_OFFLINE=1
VOLUME ["/repos", "/workspace"]
EXPOSE 7700
CMD ["modeld", "serve", "/workspace", "--build", "/repos", "--host", "0.0.0.0", "--port", "7700"]
