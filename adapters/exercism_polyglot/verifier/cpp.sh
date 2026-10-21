clean_workspace() {
  rm -rf /app/test /app/build
}

run_tests() {
  local build
  build="$(mktemp -d)"
  cmake -S /app -B "$build" -DEXERCISM_RUN_ALL_TESTS=1 && timeout 270 cmake --build "$build" -j 2
}
