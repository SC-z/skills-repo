#!/bin/bash

# Remote command executor with key-first and password fallback.
# Usage: remote-executor.sh "<server>" "<command>"

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=remote-beautify-lib.sh
source "${SCRIPT_DIR}/remote-beautify-lib.sh"

# Respect caller-provided REMOTE_BEAUTY_LEVEL (no forced override).

SSH_TIMEOUT=10
SSH_OPTS_COMMON=(
  -o ConnectTimeout=${SSH_TIMEOUT}
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
  -o LogLevel=ERROR
)
SSH_OPTS_KEY=(
  -o BatchMode=yes
  -o PreferredAuthentications=publickey
)
SSH_OPTS_PWD=(
  -o BatchMode=no
  -o PreferredAuthentications=password,keyboard-interactive
  -o PubkeyAuthentication=no
)

PASSWORDS=("Cljslrl0620!" "letsg0" "cljslrl0620")

# Resolved SSH options/passwords (set via resolve_* helpers).
SSH_OPTS_PORT=()
SSH_PASSWORD_LIST=()

usage() {
  echo "Usage: $(basename "$0") \"<server>\" \"<command>\""
}

# Resolve SSH target from server input.
# Args: <server>
# Returns: <target> (user@host or original)
resolve_ssh_target() {
  local server="$1"
  if [[ "$server" == *"@"* ]]; then
    echo "$server"
    return 0
  fi
  local user="${REMOTE_SSH_USER:-root}"
  echo "${user}@${server}"
}

# Resolve SSH password list, honoring REMOTE_SSH_PASSWORD if set.
# Returns: sets global SSH_PASSWORD_LIST array
resolve_passwords() {
  SSH_PASSWORD_LIST=()
  if [ -n "${REMOTE_SSH_PASSWORD:-}" ]; then
    SSH_PASSWORD_LIST+=("$REMOTE_SSH_PASSWORD")
  else
    SSH_PASSWORD_LIST=("${PASSWORDS[@]}")
  fi
}

# Resolve SSH port options, honoring REMOTE_SSH_PORT if set.
# Returns: sets global SSH_OPTS_PORT array
resolve_ssh_port() {
  SSH_OPTS_PORT=()
  if [ -n "${REMOTE_SSH_PORT:-}" ]; then
    SSH_OPTS_PORT=(-p "$REMOTE_SSH_PORT")
  fi
}

# Detect auth-related failures to decide whether to fallback to password.
# Args: <stderr_file>
# Returns: 0 if auth failure, 1 otherwise
is_auth_failure() {
  local err_file="$1"
  if grep -Eqi "Permission denied|Authentication failed|publickey|keyboard-interactive|No supported authentication methods available|Too many authentication failures" "$err_file"; then
    return 0
  fi
  return 1
}

# Run SSH with key auth.
# Args: <server> <command> <out_file> <err_file>
# Returns: ssh exit code
ssh_key_attempt() {
  local server="$1"
  local cmd="$2"
  local out_file="$3"
  local err_file="$4"

  # Build ssh command safely to avoid set -u on empty arrays.
  local -a ssh_cmd
  ssh_cmd=(ssh "${SSH_OPTS_COMMON[@]}" "${SSH_OPTS_KEY[@]}")
  if [ ${#SSH_OPTS_PORT[@]} -gt 0 ]; then
    ssh_cmd+=("${SSH_OPTS_PORT[@]}")
  fi
  ssh_cmd+=("$server" "$cmd")
  "${ssh_cmd[@]}" >"$out_file" 2>"$err_file"
  return $?
}

# Run SSH with password auth via sshpass.
# Args: <server> <command> <password> <out_file> <err_file>
# Returns: ssh exit code
ssh_password_attempt() {
  local server="$1"
  local cmd="$2"
  local password="$3"
  local out_file="$4"
  local err_file="$5"

  # Build sshpass command safely to avoid set -u on empty arrays.
  local -a ssh_cmd
  ssh_cmd=(sshpass -p "$password" ssh "${SSH_OPTS_COMMON[@]}" "${SSH_OPTS_PWD[@]}")
  if [ ${#SSH_OPTS_PORT[@]} -gt 0 ]; then
    ssh_cmd+=("${SSH_OPTS_PORT[@]}")
  fi
  ssh_cmd+=("$server" "$cmd")
  "${ssh_cmd[@]}" >"$out_file" 2>"$err_file"
  return $?
}

# Copy attempt outputs into final output files.
# Args: <tmp_out> <tmp_err> <final_out> <final_err>
finalize_output() {
  local tmp_out="$1"
  local tmp_err="$2"
  local final_out="$3"
  local final_err="$4"

  cat "$tmp_out" >"$final_out"
  cat "$tmp_err" >"$final_err"
}

# Run remote command with key-first and password fallback.
# Args: <server> <command> <final_out> <final_err>
# Returns: ssh exit code
run_with_fallback() {
  local server="$1"
  local cmd="$2"
  local final_out="$3"
  local final_err="$4"

  # Resolve port/passwords for this run.
  resolve_ssh_port
  resolve_passwords

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  local tmp_out="${tmp_dir}/out"
  local tmp_err="${tmp_dir}/err"

  # Key attempt
  : >"$tmp_out"
  : >"$tmp_err"
  ssh_key_attempt "$server" "$cmd" "$tmp_out" "$tmp_err"
  local rc=$?
  if [ $rc -eq 0 ]; then
    finalize_output "$tmp_out" "$tmp_err" "$final_out" "$final_err"
    rm -rf "$tmp_dir"
    return 0
  fi

  if ! is_auth_failure "$tmp_err"; then
    finalize_output "$tmp_out" "$tmp_err" "$final_out" "$final_err"
    rm -rf "$tmp_dir"
    return $rc
  fi

  if ! command -v sshpass >/dev/null 2>&1; then
    echo "sshpass not found; aborting password fallback." >"$final_err"
    rm -rf "$tmp_dir"
    return 127
  fi

  # Password attempts
  local password
  for password in "${SSH_PASSWORD_LIST[@]}"; do
    : >"$tmp_out"
    : >"$tmp_err"
    ssh_password_attempt "$server" "$cmd" "$password" "$tmp_out" "$tmp_err"
    rc=$?
    if [ $rc -eq 0 ]; then
      finalize_output "$tmp_out" "$tmp_err" "$final_out" "$final_err"
      rm -rf "$tmp_dir"
      return 0
    fi
    if ! is_auth_failure "$tmp_err"; then
      finalize_output "$tmp_out" "$tmp_err" "$final_out" "$final_err"
      rm -rf "$tmp_dir"
      return $rc
    fi
  done

  # All auth attempts failed; keep last error
  finalize_output "$tmp_out" "$tmp_err" "$final_out" "$final_err"
  rm -rf "$tmp_dir"
  return $rc
}

# Print framed output using the beautify library.
# Args: <title> <file>
print_frame_from_file() {
  local title="$1"
  local file="$2"

  print_output_frame_start "$title"
  if [ -s "$file" ]; then
    while IFS= read -r line; do
      print_output_frame_line "$line"
    done <"$file"
  else
    print_output_frame_line "(empty)"
  fi
  print_output_frame_end
}

main() {
  if [ $# -lt 2 ]; then
    usage
    exit 2
  fi

  local server_raw="$1"
  shift
  local cmd="$1"
  local server_target
  # Resolve target with default SSH user if needed.
  server_target="$(resolve_ssh_target "$server_raw")"
  local beauty_level="${REMOTE_BEAUTY_LEVEL:-2}"

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  local stdout_file="${tmp_dir}/stdout"
  local stderr_file="${tmp_dir}/stderr"

  # Header rendering based on beauty level.
  if [ "$beauty_level" -ge 2 ] && type print_ascii_banner >/dev/null 2>&1; then
    print_ascii_banner "REMOTE" 2
    print_separator "─" 80 "$CYAN"
    echo -e "  $(get_colored_icon 'server') ${BOLD}Server${NC}: ${LIGHT_CYAN}${server_target}${NC}"
    echo -e "  $(get_colored_icon 'file') ${BOLD}Command${NC}: ${LIGHT_CYAN}${cmd}${NC}"
    print_separator "─" 80 "$CYAN"
  elif [ "$beauty_level" -eq 1 ]; then
    echo -e "${CYAN}━━━ Remote Command Execution ━━━${NC}"
    echo -e "${CYAN}Host:${NC} ${server_target}"
    echo -e "${CYAN}Command:${NC} ${cmd}"
    echo -e "${CYAN}────────────────────────────────${NC}"
  else
    echo "Executing on ${server_target}: ${cmd}"
  fi

  # Start timing after header is printed.
  local start_time
  start_time="$(date +%s)"

  run_with_fallback "$server_target" "$cmd" "$stdout_file" "$stderr_file"
  local rc=$?

  local end_time
  end_time="$(date +%s)"
  local duration
  duration=$((end_time - start_time))

  if [ "$beauty_level" -ge 2 ]; then
    print_status "processing" "Command output" ""
    print_frame_from_file "STDOUT" "$stdout_file"
    if [ -s "$stderr_file" ]; then
      print_frame_from_file "STDERR" "$stderr_file"
    fi

    if [ $rc -eq 0 ]; then
      print_status "success" "Command succeeded (rc=0)" ""
    else
      print_status "error" "Command failed (rc=${rc})" ""
    fi
    print_status "info" "Duration: $(format_duration "$duration")" ""
  elif [ "$beauty_level" -eq 1 ]; then
    echo -e "${CYAN}Output:${NC}"
    cat "$stdout_file"
    if [ -s "$stderr_file" ]; then
      echo -e "${RED}Error:${NC}"
      cat "$stderr_file"
    fi
    if [ $rc -eq 0 ]; then
      echo -e "${GREEN}✓${NC} Command executed successfully"
    else
      echo -e "${RED}✗${NC} Command failed (rc=${rc})"
    fi
    echo -e "${CYAN}Duration:${NC} ${duration}s"
  else
    cat "$stdout_file"
    if [ -s "$stderr_file" ]; then
      cat "$stderr_file"
    fi
  fi

  rm -rf "$tmp_dir"
  return $rc
}

main "$@"
