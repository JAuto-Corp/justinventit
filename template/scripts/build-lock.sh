#!/usr/bin/env bash
# Shared kernel capacity; extracted source and lifetime limits: docs/HOST_CAPACITY.md.
# PID/age metadata is diagnostic. Closing our FD must not unlock descendants.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/lib/jv-project.sh"
readonly MIN_MEM_MB=4096

fail() { printf 'build-lock: %s\n' "$*" >&2; exit 74; }
for key in JAUTO_BUILD_LOCK_FD BUILD_LOCK_TEST_MODE BUILD_LOCK_TEST_DIR BUILD_LOCK_TEST_AVAILABLE_MB; do
  [[ ! -v "$key" ]] || fail 'legacy configuration refused; set the explicit JV project and host roots'
done
_jv_project_configure
_jv_verify_store
[[ "${JV_HOST_ROOT:-}" == /* && "$JV_HOST_ROOT" != / ]] || fail 'JV_HOST_ROOT must be an explicit absolute host directory'
JV_HOST_ROOT=${JV_HOST_ROOT%/}
case "$JV_HOST_ROOT" in *//*|*/./*|*/../*|*/.|*/..) fail 'host root must not contain dot or empty components';; esac
LOCK_DIR="$JV_HOST_ROOT/locks"
LOCK_FILE="$LOCK_DIR/build.lock"
INFO_FILE="$LOCK_DIR/info"

check_paths() {
  local path="$LOCK_DIR"
  while [[ "$path" != / ]]; do
    [[ ! -L "$path" ]] || fail 'symlink in host directory path'
    [[ ! -e "$path" || -d "$path" ]] || fail 'host path is not a directory'
    [[ ! -d "$path" || -x "$path" ]] || fail 'host directory is not searchable'
    path=${path%/*}; [[ -n "$path" ]] || path=/
  done
  for path in "$LOCK_FILE" "$INFO_FILE"; do
    [[ ! -L "$path" ]] || fail 'symlink in host file path'
    [[ ! -e "$path" || -f "$path" ]] || fail 'host path is not a regular file'
  done
}
check_paths

get_available_mb() {
  local result
  result=$(awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo 2>/dev/null) || result=
  if [[ "$result" =~ ^[0-9]{1,12}$ ]]; then printf '%s\n' "$((10#$result))"; else printf '%s\n' -1; fi
}

# 0 held, 1 unheld, 74 unknown. Only explicit conflict status proves held.
lock_held() {
  [[ -f "$LOCK_FILE" ]] || return 1
  local probe_fd rc=0
  exec {probe_fd}<"$LOCK_FILE" || return 74
  flock -n -E 75 "$probe_fd" || rc=$?
  exec {probe_fd}>&-
  case "$rc" in 75) return 0;; 0) return 1;; *) return 74;; esac
}

read_info() {
  [[ -f "$INFO_FILE" ]] || return 0
  # Metadata is bounded display data, never sourced or used to grant a slot.
  head -c 4096 -- "$INFO_FILE" | sed -n "s/^${1}=//p" | head -n 1
}

holder_summary() {
  local holder held_at now age=unknown
  holder=$(read_info project_id) || holder=unknown
  held_at=$(read_info held_at_epoch) || held_at=
  now=$(date +%s) || now=
  if [[ "$held_at" =~ ^[0-9]{1,10}$ && "$now" =~ ^[0-9]{1,10}$ ]]; then
    age=$((10#$now - 10#$held_at))
  fi
  printf "held by '%s' for %ss" "${holder:-pending}" "$age"
}

write_info() {
  INFO_TMP=$(mktemp "$LOCK_DIR/.info.XXXXXXXX") || return 74
  LOCK_TOKEN=${INFO_TMP##*/}
  local now
  now=$(date +%s) || return 74
  cat > "$INFO_TMP" <<META
token=$LOCK_TOKEN
pid=$$
project_id=$JV_PROJECT_ID
held_at_epoch=$now
META
  # Check explicitly: a failed write must never be followed by publication.
  local rc=$?
  [[ "$rc" == 0 ]] || return 74
  chmod 600 -- "$INFO_TMP" || return 74
  mv -f -- "$INFO_TMP" "$INFO_FILE" || return 74
  INFO_TMP=
}

lock_cleanup() {
  local rc=$?
  trap - EXIT
  [[ -z "${INFO_TMP:-}" ]] || rm -f -- "$INFO_TMP" || true
  if [[ -n "${LOCK_TOKEN:-}" && -f "$INFO_FILE" ]] &&
      [[ "$(read_info token)" == "$LOCK_TOKEN" ]]; then
    rm -f -- "$INFO_FILE" || true
  fi
  if [[ -n "${LOCK_FD:-}" ]]; then
    # Never flock-unlock or delete the inode: a descendant may retain this OFD.
    exec {LOCK_FD}>&-
  fi
  exit "$rc"
}

refuse_inherited_fd() {
  printf 'build-lock: invalid inherited ownership: %s\n' "$1" >&2
  return 65
}

verify_inherited_fd() {
  local fd="${JV_BUILD_LOCK_FD:-}" lock_identity fd_identity probe_fd rc=0
  [[ "$fd" =~ ^[1-9][0-9]*$ && -f "$LOCK_FILE" && -e "/proc/self/fd/$fd" ]] ||
    { refuse_inherited_fd 'descriptor or file absent'; return 65; }
  lock_identity=$(stat -Lc '%d:%i' -- "$LOCK_FILE") ||
    { refuse_inherited_fd 'cannot inspect file'; return 65; }
  fd_identity=$(stat -Lc '%d:%i' -- "/proc/self/fd/$fd") ||
    { refuse_inherited_fd 'cannot inspect descriptor'; return 65; }
  [[ "$fd_identity" == "$lock_identity" ]] ||
    { refuse_inherited_fd 'descriptor points to another inode'; return 65; }
  exec {probe_fd}<"$LOCK_FILE" ||
    { refuse_inherited_fd 'cannot open probe'; return 65; }
  flock -n -E 75 "$probe_fd" || rc=$?
  exec {probe_fd}>&-
  [[ "$rc" == 75 ]] ||
    { refuse_inherited_fd 'probe did not establish kernel contention'; return 65; }
  flock -n -E 75 "$fd" ||
    { refuse_inherited_fd 'descriptor does not own the lock'; return 65; }
}

do_run() {
  [[ $# -ge 1 ]] || { printf 'Usage: build-lock.sh run <command> [args...]\n' >&2; return 64; }
  local available rc=0
  available=$(get_available_mb)
  if (( available >= 0 && available < MIN_MEM_MB )); then
    printf 'build-lock: insufficient memory (%s MiB; need %s)\n' "$available" "$MIN_MEM_MB" >&2
    return 2
  fi
  if (( available < 0 )); then
    printf 'build-lock: warning: memory observation unavailable; continuing under kernel lock\n' >&2
  fi
  if [[ -v JV_BUILD_LOCK_FD ]]; then
    verify_inherited_fd || return $?
    "$@" || rc=$?
    printf 'build-lock: nested command completed with status %s\n' "$rc" >&2
    return "$rc"
  fi
  umask 077
  mkdir -p -- "$LOCK_DIR" || fail 'cannot create host lock directory'
  check_paths
  exec {LOCK_FD}>>"$LOCK_FILE" || fail 'cannot open lock file'
  flock -n -E 75 "$LOCK_FD" || rc=$?
  if [[ "$rc" != 0 ]]; then
    exec {LOCK_FD}>&-
    if [[ "$rc" == 75 ]]; then
      printf 'build-lock: contention: %s\n' "$(holder_summary)" >&2
      return 1
    fi
    fail 'kernel lock acquisition unknown'
  fi
  trap lock_cleanup EXIT
  write_info || fail 'cannot publish holder metadata'
  JV_BUILD_LOCK_FD="$LOCK_FD" "$@" || rc=$?
  printf 'build-lock: command completed with status %s\n' "$rc" >&2
  return "$rc"
}

do_status() {
  local rc=0
  lock_held || rc=$?
  case "$rc" in
    0) printf 'build-lock: held\n  %s\n' "$(holder_summary)" ;;
    1) printf 'build-lock: unheld\n' ;;
    *) printf 'build-lock: inspection unknown\n' >&2; return 74 ;;
  esac
  printf 'memory_available_mb=%s\n' "$(get_available_mb)"
}

case "${1:-}" in
  run) shift; do_run "$@" ;;
  verify-inherited) [[ $# == 1 ]] || exit 64; verify_inherited_fd ;;
  status|wait-info) [[ $# == 1 ]] || exit 64; do_status ;;
  acquire|release) printf 'build-lock: one-shot acquire/release retired; use build-guarded.sh <command>\n' >&2; exit 64 ;;
  *) printf 'Usage: build-lock.sh {run <command> [args...]|verify-inherited|status|wait-info}\n' >&2; exit 64 ;;
esac
