FROM ghcr.io/node-q/hbench-envs:base-python-3.12-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2

ENV TZ=UTC PIP_ROOT_USER_ACTION=ignore PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt /opt/exercism-python/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes --only-binary :all: -r /opt/exercism-python/requirements.txt

WORKDIR /app
