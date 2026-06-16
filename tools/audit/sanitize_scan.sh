#!/usr/bin/env bash
set -euo pipefail

# description: Redacted public-release scanner. Normal mode prints summary
# counts only. Verbose mode prints classification:path:line:risk_category.

usage() {
	cat <<'USAGE'
usage:
	tools/audit/sanitize_scan.sh [--verbose] [--strict] [--path <dir_or_file>]...

default:
	scans git-tracked files when run inside a Git repository; otherwise scans
	the current working tree.

exit status:
	normal mode fails only for BLOCKER findings.
	--strict also fails for REVIEW_REQUIRED findings.
USAGE
}

verbose=0
strict=0
scan_paths=()
while [[ $# -gt 0 ]]; do
	case "$1" in
		--verbose)
			verbose=1
			shift
			;;
		--strict)
			strict=1
			shift
			;;
		--path)
			shift
			[[ $# -gt 0 ]] || { echo "missing arg for --path" >&2; exit 2; }
			scan_paths+=("$1")
			shift
			;;
		-h|--help) usage; exit 0 ;;
		*) echo "unknown arg: $1" >&2; usage; exit 2 ;;
	esac
done

tmp="$(mktemp)"
findings="$(mktemp)"
cleanup() { rm -f "$tmp" "$findings"; }
trap cleanup EXIT

if [[ ${#scan_paths[@]} -gt 0 ]]; then
	for p in "${scan_paths[@]}"; do
		if [[ -d "$p" ]]; then
			find "$p" -path "$p/.git" -prune -o -type f -print 2>/dev/null || true
		elif [[ -f "$p" ]]; then
			echo "$p"
		fi
	done
elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	git ls-files
else
	find . -path './.git' -prune -o -type f -print 2>/dev/null | sed 's#^\./##'
fi | sort -u >"$tmp"

add_finding() {
	local classification="$1"
	local path="$2"
	local line_number="$3"
	local risk_category="$4"

	printf '%s:%s:%s:%s\n' "$classification" "$path" "$line_number" "$risk_category" >>"$findings"
}

is_audit_tool() {
	case "$1" in
		tools/audit/sanitize_scan.sh|tools/audit/public_release_check.sh) return 0 ;;
		*) return 1 ;;
	esac
}

is_public_fixture_path() {
	case "$1" in
		examples/routes/chicago-loyola-*|docs/chicago-reference-scenario.md|demo/fixtures/*.json) return 0 ;;
		*) return 1 ;;
	esac
}

is_text_skippable_binary_or_runtime() {
	case "$1" in
		*.png|*.jpg|*.jpeg|*.gif|*.webp|*.pdf|*.zip|*.tar|*.gz|*.pyc|*.pyo) return 0 ;;
		*) return 1 ;;
	esac
}

is_runtime_artifact_path() {
	case "$1" in
		*.sqlite|*.sqlite3|*.db|*.log|*.jsonl|*.pcap|*.pcapng) return 0 ;;
		*) return 1 ;;
	esac
}

is_non_example_env_path() {
	case "$1" in
		.env|*/.env|*.env) [[ "$1" != *.env.example ]] ;;
		*) return 1 ;;
	esac
}

is_doc_safe_ip() {
	local ip="$1"
	case "$ip" in
		127.*|0.0.0.0|192.0.2.*|198.51.100.*|203.0.113.*|198.18.*|198.19.*) return 0 ;;
		*) return 1 ;;
	esac
}

is_private_ip() {
	local ip="$1"
	case "$ip" in
		10.*|192.168.*|172.16.*|172.17.*|172.18.*|172.19.*|172.20.*|172.21.*|172.22.*|172.23.*|172.24.*|172.25.*|172.26.*|172.27.*|172.28.*|172.29.*|172.30.*|172.31.*) return 0 ;;
		*) return 1 ;;
	esac
}

is_public_safe_ip_context() {
	local path="$1"
	local ip="$2"
	local line="$3"

	case "$path:$ip" in
		nodes/home-lan-target/homekit-automation/web/runserver.sh:1.1.1.1)
			[[ "$line" == *"ip route get"* ]]
			;;
		*) return 1 ;;
	esac
}

is_public_safe_domain_context() {
	local path="$1"
	local domain="$2"
	local line="$3"

	case "$path:$domain" in
		nodes/home-lan-target/homekit-automation/ingest_enrich.py:archive-api.open-meteo.com)
			[[ "$line" == *"https://archive-api.open-meteo.com/v1/archive"* ]]
			;;
		*) return 1 ;;
	esac
}

is_placeholder_line() {
	local line="$1"
	[[ "$line" =~ (example\.invalid|[A-Za-z0-9._-]+\.example\.internal|presence-relay-demo-token|replace-with-long-random-token|REPLACE_WITH_|127\.0\.0\.1|localhost|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.) ]]
}

has_public_chicago_coordinate() {
	local line="$1"
	[[ "$line" =~ (41\.99[0-9]{4}|42\.00[0-9]{4}|-87\.65[0-9]{4}|-87\.66[0-9]{4}) ]]
}

classify_ip_tokens() {
	local path="$1"
	local line_number="$2"
	local line="$3"
	local matches token ip

	matches="$(grep -Eo '(^|[^0-9.])([0-9]{1,3}\.){3}[0-9]{1,3}([^0-9.]|$)' <<<"$line" || true)"
	[[ -n "$matches" ]] || return 0

	while IFS= read -r token; do
		[[ -n "$token" ]] || continue
		ip="$(sed -E 's/^[^0-9]*//; s/[^0-9.]*$//' <<<"$token")"
		if is_public_safe_ip_context "$path" "$ip" "$line"; then
			add_finding "PUBLIC_SAFE" "$path" "$line_number" "IP_ADDRESS"
		elif is_doc_safe_ip "$ip" || is_placeholder_line "$line"; then
			add_finding "EXPECTED_PLACEHOLDER" "$path" "$line_number" "IP_ADDRESS"
		elif is_private_ip "$ip"; then
			add_finding "REVIEW_REQUIRED" "$path" "$line_number" "PRIVATE_IP"
		else
			add_finding "REVIEW_REQUIRED" "$path" "$line_number" "IP_ADDRESS"
		fi
	done <<<"$matches"
}

classify_domain_tokens() {
	local path="$1"
	local line_number="$2"
	local line="$3"
	local matches token domain

	matches="$(grep -Eio '(^|[^A-Za-z0-9._-])([A-Za-z0-9][A-Za-z0-9._-]*\.)+(com|org|net|edu|io|dev|local|invalid|internal)([^A-Za-z0-9._-]|$)' <<<"$line" || true)"
	[[ -n "$matches" ]] || return 0

	while IFS= read -r token; do
		[[ -n "$token" ]] || continue
		domain="$(sed -E 's/^[^A-Za-z0-9]*//; s/[^A-Za-z0-9._-]*$//' <<<"$token")"
		case "$domain" in
			example.invalid|*.example.invalid|*.example.internal|example.com|example.org|example.net|localhost.local)
				add_finding "EXPECTED_PLACEHOLDER" "$path" "$line_number" "DOMAIN"
				;;
			*)
				if is_public_safe_domain_context "$path" "$domain" "$line"; then
					add_finding "PUBLIC_SAFE" "$path" "$line_number" "DOMAIN"
				elif is_audit_tool "$path"; then
					:
				else
					add_finding "REVIEW_REQUIRED" "$path" "$line_number" "DOMAIN"
				fi
				;;
		esac
	done <<<"$matches"
}

classify_line() {
	local path="$1"
	local line_number="$2"
	local line="$3"

	if is_runtime_artifact_path "$path"; then
		add_finding "BLOCKER" "$path" "$line_number" "RUNTIME_ARTIFACT"
		return
	fi

	if is_non_example_env_path "$path"; then
		add_finding "BLOCKER" "$path" "$line_number" "NON_EXAMPLE_ENV"
		return
	fi

	if [[ "$line" =~ BEGIN[[:space:]]+(RSA[[:space:]]+|OPENSSH[[:space:]]+|EC[[:space:]]+|DSA[[:space:]]+)?PRIVATE[[:space:]]+KEY ]]; then
		add_finding "BLOCKER" "$path" "$line_number" "PRIVATE_KEY"
	fi

	if [[ "$line" =~ (token|secret|password|WEBHOOK_TOKEN|EVENT_AUTH_TOKEN)[A-Za-z0-9_[:space:]-]*(=|:)[[:space:]]*[\"\']?[A-Za-z0-9_./+=-]{20,} ]] && ! is_placeholder_line "$line"; then
		add_finding "BLOCKER" "$path" "$line_number" "CREDENTIAL_ASSIGNMENT"
	fi

	if is_audit_tool "$path"; then
		return
	fi

	classify_ip_tokens "$path" "$line_number" "$line"
	classify_domain_tokens "$path" "$line_number" "$line"

	if [[ "$line" =~ (/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/) ]]; then
		add_finding "REVIEW_REQUIRED" "$path" "$line_number" "HOME_PATH"
	fi

	if [[ "$line" =~ [A-Za-z0-9+/]{40,}={0,2} ]] && ! is_placeholder_line "$line"; then
		add_finding "REVIEW_REQUIRED" "$path" "$line_number" "HIGH_ENTROPY_STRING"
	fi

	if is_public_fixture_path "$path"; then
		if has_public_chicago_coordinate "$line" || [[ "$line" =~ (Chicago|Loyola|Edgewater|Lakefront|synthetic-example|route_id|place_id|coordinates|latitude|longitude|lat|lon|home|school) ]]; then
			add_finding "PUBLIC_FIXTURE" "$path" "$line_number" "CHICAGO_REFERENCE"
		fi
		return
	fi

	if is_placeholder_line "$line"; then
		add_finding "EXPECTED_PLACEHOLDER" "$path" "$line_number" "PLACEHOLDER"
	fi

	if [[ "$line" =~ (X-Auth-Token|WEBHOOK_TOKEN|EVENT_AUTH_TOKEN|Authorization:|PrivateKey|PresharedKey|token|secret|password|ssh|SSH|WireGuard|wg0|PI_SSH_HOST|sqlite|sqlite3|database|raw_json|raw_line|jsonl|log|latitude|longitude|lat|lon|coordinates|GPS|geofence|iPhone|Shortcut|home|school) ]]; then
		add_finding "GENERIC_SECURITY_TERM" "$path" "$line_number" "GENERIC_SECURITY_TERM"
	fi
}

while IFS= read -r f; do
	[[ -n "${f:-}" && -f "$f" ]] || continue

	if is_text_skippable_binary_or_runtime "$f"; then
		continue
	fi

	if is_runtime_artifact_path "$f" || is_non_example_env_path "$f"; then
		add_finding "BLOCKER" "$f" "0" "FORBIDDEN_FILE"
		continue
	fi

	lineno=0
	while IFS= read -r line || [[ -n "$line" ]]; do
		lineno=$((lineno + 1))
		classify_line "$f" "$lineno" "$line"
	done <"$f"
done <"$tmp"

count_classification() {
	local classification="$1"
	grep -Ec "^${classification}:" "$findings" || true
}

blockers="$(count_classification "BLOCKER")"
review_required="$(count_classification "REVIEW_REQUIRED")"
expected_placeholder="$(count_classification "EXPECTED_PLACEHOLDER")"
public_fixture="$(count_classification "PUBLIC_FIXTURE")"
public_safe="$(count_classification "PUBLIC_SAFE")"
generic_security_term="$(count_classification "GENERIC_SECURITY_TERM")"

if [[ "$verbose" -eq 1 ]]; then
	cat "$findings"
else
	printf 'BLOCKER=%s\n' "$blockers"
	printf 'REVIEW_REQUIRED=%s\n' "$review_required"
	printf 'EXPECTED_PLACEHOLDER=%s\n' "$expected_placeholder"
	printf 'PUBLIC_FIXTURE=%s\n' "$public_fixture"
	printf 'PUBLIC_SAFE=%s\n' "$public_safe"
	printf 'GENERIC_SECURITY_TERM=%s\n' "$generic_security_term"
fi

if [[ "$blockers" -gt 0 ]]; then
	exit 1
fi

if [[ "$strict" -eq 1 && "$review_required" -gt 0 ]]; then
	exit 1
fi
