#!/bin/bash
set -uo pipefail

export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'
patch_file="$(cd "$(dirname "$0")" && pwd)/gold.patch"
cd @REPOSITORY@ || exit 1
for apply in "git apply --verbose" "git apply --verbose --3way" "git apply --verbose --reject" "patch --batch --forward --fuzz=5 -p1 -i"; do
  if $apply "$patch_file"; then
    exit 0
  fi
  git reset --hard --quiet
  git clean -fd --quiet
done
git apply --check --reverse "$patch_file"
