export TZ=UTC
tests_directory="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
cd "$exercise_directory" || exit 0
clean_workspace
cp -R "$tests_directory/workspace/." "$exercise_directory/"
restore_embedded_files
if run_tests; then
  echo 1 > /logs/verifier/reward.txt
fi
