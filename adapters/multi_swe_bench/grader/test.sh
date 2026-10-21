#!/bin/bash

python3 -X utf8 /tests/grade.py \
  --config /tests/config.json \
  --artifacts /logs/artifacts/swebench \
  --verifier-logs /logs/verifier
