FROM ghcr.io/node-q/hbench-envs:base-python-3.12-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2

# The open Actuaria test sets (adapters/taskfolders): Python 3.12 with its standard library, which every
# instruction promises, and Node.js and npm from Debian for the AI tools that need them. hbench copies each
# task's environment/ (its documents) into /app; the answer goes to /app/output.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/output
WORKDIR /app
