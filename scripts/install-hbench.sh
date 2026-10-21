#!/usr/bin/env bash
set -euo pipefail

readonly HBENCH_REPOSITORY=node-q/hbench
readonly HBENCH_RELEASE_WORKFLOW=node-q/hbench/.github/workflows/release.yml

fail() {
  echo "install-hbench.sh: $*" >&2
  exit 1
}

[[ $# -eq 2 ]] || fail "usage: install-hbench.sh <release> <install directory>"
release_tag="v${1#v}"
install_directory="$2"
[[ "$release_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]] || fail "'$1' is not an hbench release such as v0.3.0"

case "$(uname -m)" in
  x86_64) target=x86_64-unknown-linux-musl ;;
  aarch64) target=aarch64-unknown-linux-musl ;;
  *) fail "no hbench release archive for $(uname -m)" ;;
esac

archive="hbench-$release_tag-$target.tar.gz"
download_directory="$(mktemp -d)"
trap 'rm -rf "$download_directory"' EXIT

gh release download "$release_tag" --repo "$HBENCH_REPOSITORY" --dir "$download_directory" \
  --pattern "$archive" --pattern SHA256SUMS

checksum_lines="$(awk -v name="$archive" '$2 == name' "$download_directory/SHA256SUMS")"
[[ -n "$checksum_lines" && "$(wc -l <<<"$checksum_lines")" -eq 1 ]] || fail "SHA256SUMS of $release_tag lists $archive no or several times"
(cd "$download_directory" && sha256sum --check --strict <<<"$checksum_lines")

gh attestation verify "$download_directory/$archive" \
  --repo "$HBENCH_REPOSITORY" \
  --signer-workflow "$HBENCH_RELEASE_WORKFLOW" \
  --source-ref "refs/tags/$release_tag" \
  --deny-self-hosted-runners

tar -xzf "$download_directory/$archive" -C "$download_directory"
mkdir -p "$install_directory"
install -m 0755 "$download_directory/hbench-$release_tag-$target/hbench" "$install_directory/hbench"

installed_version="$("$install_directory/hbench" --version)"
[[ "$installed_version" == *" ${release_tag#v}" ]] || fail "installed binary reports '$installed_version', expected ${release_tag#v}"
echo "Installed $installed_version from $HBENCH_REPOSITORY $release_tag ($archive, checksum and build provenance verified)"
