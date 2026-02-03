#!/bin/bash

# Remote parallel command runner with key-first and password fallback.
# Usage: remote-parallel.sh [-v] "<server>" "<cmd1>" "<cmd2>" ...

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
  echo "Usage: $(basename "$0") [-v] \"<server>\" \"<cmd1>\" \"<cmd2>\" ..."
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
  local verbose=0

  if [ $# -ge 1 ] && [ "$1" = "-v" ]; then
    verbose=1
    shift
  fi

  if [ $# -lt 2 ]; then
    usage
    exit 2
  fi

  local server_raw="$1"
  shift
  local -a cmds=("$@")
  local total_cmds="${#cmds[@]}"
  local server_target
  # Resolve target with default SSH user if needed.
  server_target="$(resolve_ssh_target "$server_raw")"
  local beauty_level="${REMOTE_BEAUTY_LEVEL:-2}"

  local tmp_dir
  tmp_dir="$(mktemp -d)"

  local -a pids
  local -a rc_files
  local -a out_files
  local -a err_files
  local -a start_times
  local -a durations

  # Header rendering based on beauty level.
  if [ "$beauty_level" -ge 2 ] && type print_ascii_banner >/dev/null 2>&1; then
    print_ascii_banner "PARALLEL EXECUTION" 2
    echo -e "  $(get_colored_icon 'network') ${BOLD}Target${NC}: $(gradient_text "$server_target" 51 87)"
    echo -e "  $(get_colored_icon 'package') ${BOLD}Commands${NC}: ${LIGHT_CYAN}${total_cmds}${NC} tasks"
    print_separator "─" 60 "$GRAY"
    echo -e "${BOLD}${LIGHT_YELLOW}Task Queue:${NC}"
    local i
    for i in "${!cmds[@]}"; do
      echo -e "  ${CYAN}[$((i + 1))]${NC} ${cmds[$i]}"
    done
    print_separator "─" 60 "$GRAY"
    echo
  elif [ "$beauty_level" -eq 1 ]; then
    echo -e "${CYAN}━━━ Parallel Remote Execution ━━━${NC}"
    echo -e "${CYAN}Target:${NC} ${server_target}"
    echo -e "${CYAN}Tasks:${NC} ${total_cmds}"
    echo -e "${CYAN}────────────────────────────────${NC}"
    echo -e "${BOLD}Commands:${NC}"
    local i
    for i in "${!cmds[@]}"; do
      echo "  [$((i + 1))] ${cmds[$i]}"
    done
    echo
  else
    echo "Executing ${total_cmds} commands on ${server_target} in parallel..."
  fi

  local start_time
  start_time="$(date +%s)"

  if [ "$beauty_level" -ge 1 ]; then
    print_status "processing" "Starting parallel execution..." ""
    echo
  fi

  # Start all commands in background.
  local i
  for i in "${!cmds[@]}"; do
    local out_file="${tmp_dir}/stdout_${i}"
    local err_file="${tmp_dir}/stderr_${i}"
    local rc_file="${tmp_dir}/rc_${i}"

    out_files[$i]="$out_file"
    err_files[$i]="$err_file"
    rc_files[$i]="$rc_file"
    start_times[$i]="$(date +%s)"

    (
      run_with_fallback "$server_target" "${cmds[$i]}" "$out_file" "$err_file"
      echo $? >"$rc_file"
    ) &
    pids[$i]=$!
  done

  # Progress display based on beauty level.
  if [ "$beauty_level" -ge 2 ] && type show_advanced_progress >/dev/null 2>&1; then
    echo -e "${BOLD}${LIGHT_CYAN}Progress:${NC}"
    local completed=0
    while [ $completed -lt $total_cmds ]; do
      completed=0
      for i in "${!cmds[@]}"; do
        if [ -f "${rc_files[$i]}" ]; then
          completed=$((completed + 1))
        fi
      done
      show_advanced_progress "$completed" "$total_cmds" 40 "($completed/$total_cmds)"
      if [ $completed -lt $total_cmds ]; then
        sleep 0.3
      fi
    done
    echo
  fi

  if [ "$beauty_level" -eq 1 ]; then
    echo -ne "${CYAN}Executing"
  fi

  for i in "${!cmds[@]}"; do
    wait "${pids[$i]}"
    local end_time
    end_time="$(date +%s)"
    durations[$i]=$((end_time - start_times[$i]))
    if [ "$beauty_level" -eq 1 ]; then
      echo -ne "."
    fi
  done

  if [ "$beauty_level" -eq 1 ]; then
    echo -e " Done!${NC}"
  fi

  local end_time
  end_time="$(date +%s)"
  local elapsed
  elapsed=$((end_time - start_time))

  # Collect status summary.
  local success_count=0
  local fail_count=0
  local -a status_list
  for i in "${!cmds[@]}"; do
    local rc=1
    if [ -f "${rc_files[$i]}" ]; then
      rc="$(cat "${rc_files[$i]}")"
    fi
    status_list[$i]="$rc"
    if [ "$rc" -eq 0 ]; then
      success_count=$((success_count + 1))
    else
      fail_count=$((fail_count + 1))
    fi
  done

  local final_rc=0
  if [ $fail_count -gt 0 ]; then
    final_rc=1
  fi

  # Results rendering based on beauty level.
  if [ "$beauty_level" -ge 2 ]; then
    if type print_colored_table_header >/dev/null 2>&1; then
      print_rainbow_separator 60 "═"
      echo
      echo -e "${BOLD}$(gradient_text 'EXECUTION SUMMARY' 196 226)${NC}"
      print_colored_table_header "Metric" "Value"
      print_colored_table_row "Total Tasks" "${total_cmds}"
      print_colored_table_row "Successful" "${GREEN}${success_count}${NC}"
      print_colored_table_row "Failed" "${RED}${fail_count}${NC}"
      print_colored_table_row "Time Elapsed" "$(format_duration "$elapsed")"
      if [ "$total_cmds" -gt 0 ]; then
        print_colored_table_row "Avg Time/Task" "$(format_duration $((elapsed / total_cmds)))"
      fi
      print_colored_table_footer 2
      echo
    else
      echo "Results: Time ${elapsed}s | Success ${success_count} | Failed ${fail_count}"
    fi

    for i in "${!cmds[@]}"; do
      local rc="${status_list[$i]}"
      print_status "info" "Command #$((i + 1))" ""
      if [ $verbose -eq 1 ]; then
        print_status "info" "Cmd: ${cmds[$i]}" ""
      fi
      print_status "info" "Duration: $(format_duration "${durations[$i]}")" ""
      print_status "info" "Exit: ${rc}" ""
      print_frame_from_file "STDOUT" "${out_files[$i]}"
      local err_file="${err_files[$i]:-}"
      if [ -n "$err_file" ] && [ -s "$err_file" ]; then
        print_frame_from_file "STDERR" "$err_file"
      fi
      if [ $i -lt $((total_cmds - 1)) ]; then
        print_separator "─" 80 "$CYAN"
      fi
    done
  elif [ "$beauty_level" -eq 1 ]; then
    echo
    echo -e "${CYAN}═══════════════════════════════${NC}"
    echo -e "${BOLD}Results:${NC}"
    echo -e "Time: ${elapsed}s | Success: ${GREEN}${success_count}${NC} | Failed: ${RED}${fail_count}${NC}"
    echo -e "${CYAN}═══════════════════════════════${NC}"

    for i in "${!cmds[@]}"; do
      local rc="${status_list[$i]}"
      local out_file="${out_files[$i]}"
      local err_file="${err_files[$i]:-}"
      echo
      echo -e "${CYAN}--- Command $((i + 1)): ${cmds[$i]} ---${NC}"
      if [ "$rc" -eq 0 ]; then
        echo -e "${GREEN}✓ SUCCESS${NC}"
      else
        echo -e "${RED}✗ FAILED (exit code: $rc)${NC}"
      fi
      if [ -s "$out_file" ]; then
        cat "$out_file"
      fi
      if [ -n "$err_file" ] && [ -s "$err_file" ] && [ $verbose -eq 1 ]; then
        echo -e "${RED}Error:${NC}"
        cat "$err_file"
      fi
    done

    echo
    if [ $fail_count -eq 0 ]; then
      echo -e "${GREEN}✓ All tasks completed successfully!${NC}"
    else
      echo -e "${YELLOW}⚠ ${fail_count} task(s) failed${NC}"
    fi
  else
    echo -e "\nResults:"
    echo "Time: ${elapsed}s | Success: ${success_count} | Failed: ${fail_count}"

    for i in "${!cmds[@]}"; do
      local rc="${status_list[$i]}"
      local out_file="${out_files[$i]}"
      local err_file="${err_files[$i]:-}"
      echo -e "\n--- Command: ${cmds[$i]} ---"
      if [ "$rc" -eq 0 ]; then
        echo "Status: SUCCESS"
      else
        echo "Status: FAILED (exit code: $rc)"
      fi
      if [ -s "$out_file" ]; then
        cat "$out_file"
      fi
      if [ -n "$err_file" ] && [ -s "$err_file" ] && [ $verbose -eq 1 ]; then
        echo -e "Error:"
        cat "$err_file"
      fi
    done
  fi

  rm -rf "$tmp_dir"
  return $final_rc
}

main "$@"
