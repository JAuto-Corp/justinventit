#!/usr/bin/env bash
# Shared project identity and state guard. See docs/CLUSTER_PROVENANCE.md.

_jv_fail() { printf 'ERROR (project): %s\n' "$*" >&2; exit 2; }

# Reject aliases before opening a lock, identity, log, view or cursor. This is
# a cooperating-filesystem check, not a hostile concurrent-swap defense.
_jv_check_state_paths() {
  local alias
  [[ ! -L "$JV_STORE" ]] || _jv_fail "symlink in project state"
  [[ -e "$JV_STORE" ]] || return 0
  [[ -d "$JV_STORE" ]] || _jv_fail "project store is not a directory"
  alias="$(find -P "$JV_STORE" -type l -print -quit)" || _jv_fail "cannot inspect project state"
  [[ -z "$alias" ]] || _jv_fail "symlink in project state"
}

_jv_init_store() (
  # Lock the existing project directory BEFORE creating state. A failed
  # bootstrap lock leaves no artifacts; it is local to this project root.
  flock -x 205 || _jv_fail "cannot acquire project identity bootstrap lock"
  _jv_check_state_paths
  if [[ -d "$JV_STORE" && ! -e "$JV_STORE/project.json" && ! -e "$JV_STORE/.identity.lock" ]]; then
    local entry
    entry="$(find -P "$JV_STORE" -mindepth 1 -maxdepth 1 -print -quit)" || _jv_fail "cannot inspect project store"
    [[ -z "$entry" ]] || _jv_fail "nonempty unmarked project store"
  fi
  mkdir -p -- "$JV_STORE"
  # This second lock serializes attempts to bind one ID from different roots.
  (
    flock -x 206 || _jv_fail "cannot acquire project identity store lock"
    _jv_check_state_paths
    if [[ -e "$JV_STORE/project.json" ]]; then
      [[ -f "$JV_STORE/project.json" ]] || _jv_fail "invalid project identity record"
      jq -e --arg id "$JV_PROJECT_ID" --arg root "$JV_PROJECT_ROOT" \
        '.project_id == $id and .project_root == $root' "$JV_STORE/project.json" >/dev/null 2>&1 \
        || _jv_fail "project identity is bound to a different root or invalid"
    else
      local entry tmp
      entry="$(find -P "$JV_STORE" -mindepth 1 -maxdepth 1 ! -name .identity.lock -print -quit)" \
        || _jv_fail "cannot inspect unmarked project store"
      [[ -z "$entry" ]] || _jv_fail "nonempty unmarked project store"
      tmp="$(mktemp "$JV_STORE/.identity.XXXXXXXX")" || _jv_fail "cannot prepare project identity"
      trap 'rm -f -- "$tmp"' EXIT
      jq -cn --arg id "$JV_PROJECT_ID" --arg root "$JV_PROJECT_ROOT" \
        '{schema_version:1,project_id:$id,project_root:$root}' > "$tmp"
      mv -- "$tmp" "$JV_STORE/project.json"
      trap - EXIT
    fi
    mkdir -p -- "$JV_STORE/$1"
  ) 206>>"$JV_STORE/.identity.lock"
) 205<"$JV_PROJECT_ROOT"

_jv_project_configure() {
  [[ "${JV_PROJECT_ID:-}" =~ ^[a-z0-9][a-z0-9_-]{0,63}$ ]] || _jv_fail "JV_PROJECT_ID must be a stable lowercase project identifier"
  [[ "${JV_PROJECT_ROOT:-}" == /* && -d "$JV_PROJECT_ROOT" ]] || _jv_fail "JV_PROJECT_ROOT must be an absolute existing directory"
  [[ "${JV_STATE_ROOT:-}" == /* ]] || _jv_fail "JV_STATE_ROOT must be absolute"
  JV_PROJECT_ROOT="$(cd -P -- "$JV_PROJECT_ROOT" && pwd -P)"
  JV_STATE_ROOT="$(realpath -m -- "$JV_STATE_ROOT")"
  JV_STORE="$JV_STATE_ROOT/$JV_PROJECT_ID"
}
