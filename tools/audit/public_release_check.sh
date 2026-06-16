#!/usr/bin/env bash
set -euo pipefail

# description: Hard gate for converting this staging tree to public.

usage() {
	cat <<'USAGE'
usage:
	tools/audit/public_release_check.sh [--strict]

normal mode fails for structural problems and sanitize-scan BLOCKER findings.
--strict also fails for sanitize-scan REVIEW_REQUIRED findings.
USAGE
}

strict=0
while [[ $# -gt 0 ]]; do
	case "$1" in
		--strict) strict=1; shift ;;
		-h|--help) usage; exit 0 ;;
		*) echo "unknown arg: $1" >&2; usage; exit 2 ;;
	esac
done

repo_root="$(pwd)"
cd "$repo_root"

fail() {
	echo "FAIL: $*" >&2
	exit 1
}

summary_value() {
	local key="$1"
	local text="$2"
	awk -F= -v k="$key" '$1 == k { print $2 }' <<<"$text"
}

echo "public_release_check: repo=$(pwd)"

required_paths=(
	"README.md"
	"tools/audit/sanitize_scan.sh"
	"tools/audit/public_release_check.sh"
)

for p in "${required_paths[@]}"; do
	[[ -e "$p" ]] || fail "missing required path: $p"
done

[[ ! -e .git ]] || fail ".git exists in this staging tree"
[[ ! -e private ]] || fail "private/ exists. Remove it from the public/export tree before release."

for forbidden_dir in \
	"DerivedData" \
	"__pycache__" \
	".pytest_cache" \
	".mypy_cache" \
	".ruff_cache"
do
	if [[ -e "$forbidden_dir" ]]; then
		fail "runtime/cache artifact exists: $forbidden_dir"
	fi
done

forbidden_re='(\.sqlite3?$|\.db$|(^|/)\.env$|\.env$|\.pem$|\.key$|id_rsa$|id_ed25519$|\.ppk$|\.p12$|\.pfx$|\.log$|\.jsonl$|\.pcap$|\.pcapng$)'
bad=0
while IFS= read -r f; do
	[[ -n "${f:-}" ]] || continue

	if grep -Eiq "$forbidden_re" <<<"$f"; then
		echo "FORBIDDEN exported file: $f" >&2
		bad=1
	fi
done < <(find . -path './.git' -prune -o -type f -print | sed 's#^\./##')

if [[ $bad -eq 1 ]]; then
	fail "forbidden runtime or credential files are present (see list above)"
fi

[[ -x tools/audit/sanitize_scan.sh ]] || fail "missing executable tools/audit/sanitize_scan.sh"

scan_status=0
if [[ "$strict" -eq 1 ]]; then
	scan_summary="$(tools/audit/sanitize_scan.sh --strict)" || scan_status=$?
else
	scan_summary="$(tools/audit/sanitize_scan.sh)" || scan_status=$?
fi
echo "$scan_summary"

blockers="$(summary_value "BLOCKER" "$scan_summary")"
review_required="$(summary_value "REVIEW_REQUIRED" "$scan_summary")"
blockers="${blockers:-0}"
review_required="${review_required:-0}"

if [[ "$blockers" -gt 0 ]]; then
	fail "sanitize_scan.sh reported $blockers blocker finding(s)"
fi

if [[ "$strict" -eq 1 && "$review_required" -gt 0 ]]; then
	fail "strict mode: sanitize_scan.sh reported $review_required review-required finding(s)"
fi

if [[ "$scan_status" -ne 0 ]]; then
	fail "sanitize_scan.sh exited with status $scan_status"
fi

if [[ "$review_required" -gt 0 ]]; then
	echo "REVIEW_REQUIRED findings need human review before release, but do not fail normal mode."
fi

echo "PASS: repo cleared for public release gate"
