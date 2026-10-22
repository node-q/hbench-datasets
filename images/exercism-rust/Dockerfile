FROM ghcr.io/node-q/hbench-envs:base-rust-1.99.1-slim-trixie@sha256:e6cd1d294a300601eaaa4a294b337e5f0826f427fb2d481e9f76e69e7981e244

ENV TZ=UTC CARGO_TARGET_DIR=/opt/exercism-rust/target
COPY prefetch /opt/exercism-rust/prefetch
RUN cargo build --locked --manifest-path /opt/exercism-rust/prefetch/Cargo.toml
ENV CARGO_NET_OFFLINE=true

WORKDIR /app
