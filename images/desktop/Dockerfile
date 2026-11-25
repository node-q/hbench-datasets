FROM ghcr.io/node-q/hbench-envs:base-python-3.12-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2

# The desktop for computer-use test sets (computer-use-browser): Xvfb, an XFCE session and Chromium, which hbench's
# computer-1 agent drives through screenshots, mouse and keyboard. The same Dockerfile as node-q's own desktop image,
# from the same pinned base; README.md lists what is in it and under which licences.

# Debian's archive as it stood at this moment (snapshot.debian.org), so every package resolves to the same version on
# every build; the named packages are also pinned to the versions that snapshot holds.
ARG SNAPSHOT=20261124T000000Z

RUN printf '%s\n' \
        'Types: deb' "URIs: http://snapshot.debian.org/archive/debian/${SNAPSHOT}" 'Suites: trixie trixie-updates' \
        'Components: main' 'Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp' '' \
        'Types: deb' "URIs: http://snapshot.debian.org/archive/debian-security/${SNAPSHOT}" 'Suites: trixie-security' \
        'Components: main' 'Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp' \
        > /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Retries=5 update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates=20250419+deb13u1 curl=8.14.1-2+deb13u7 procps=2:4.0.4-9 dbus-x11=1.16.2-2 \
        xvfb=2:21.1.16-1.3+deb13u4 xfce4-session=4.20.2-2 xfwm4=4.20.0-1 xfconf=4.20.0-1 \
        chromium=156.0.8078.108-1~deb13u1 \
        xdotool=1:3.20160805.1-5.1 wmctrl=1.07+git20240228.1105759-1 imagemagick=8:7.1.1.43+dfsg1-1+deb13u14 \
        scrot=1.12.1-1 x11vnc=0.9.17-1 \
        fonts-dejavu-core=2.37-8 fonts-liberation=1:2.1.5-3 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/output
WORKDIR /app
