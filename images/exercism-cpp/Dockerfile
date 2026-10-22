FROM ghcr.io/node-q/hbench-envs:base-debian-trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad

ENV TZ=UTC
RUN printf '%s\n' \
    'Types: deb' \
    'URIs: http://snapshot.debian.org/archive/debian/20261021T000000Z' \
    'Suites: trixie trixie-updates' \
    'Components: main' \
    'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
    'Check-Valid-Until: no' \
    > /etc/apt/sources.list.d/debian.sources \
  && apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends g++ cmake make libboost-date-time-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
