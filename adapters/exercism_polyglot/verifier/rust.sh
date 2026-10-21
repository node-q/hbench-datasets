clean_workspace() {
  rm -rf /app/tests /app/build.rs /app/.cargo
}

run_tests() {
  CARGO_NET_OFFLINE=true timeout 270 cargo test --offline -- --include-ignored
}
