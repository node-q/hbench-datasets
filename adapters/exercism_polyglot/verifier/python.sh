clean_workspace() {
  find /app -name __pycache__ -prune -exec rm -rf {} +
}

run_tests() {
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 timeout 270 \
    python3 -P -s -m pytest -q -p no:cacheprovider --noconftest -c /dev/null --rootdir=/app "${test_files[@]}"
}
