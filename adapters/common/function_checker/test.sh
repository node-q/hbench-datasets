#!/bin/bash

tests_directory="$(dirname "$0")"
mkdir -p /logs/verifier
PYTHONHASHSEED=0 python3 "$tests_directory/check_solution.py" \
  --solution /app/solution.py \
  --summary /logs/verifier/humaneval-plus.json
checker_status=$?
rm -f /logs/verifier/reward.json
if [ "$checker_status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
