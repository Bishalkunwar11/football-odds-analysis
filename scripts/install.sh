#!/usr/bin/env bash
#
# install.sh — Install agents into your project as GitHub Copilot agents
#              or instructions.
#
# Reads converted files from integrations/<tool>/ and copies them to the
# appropriate config directory. Run scripts/convert.sh first if integrations/
# is missing or stale.
#
# Usage:
#   ./scripts/install.sh [--tool <name>] [--help]
#
# Tools:
#   copilot       — Copy agents to .github/agents/ in current directory
#   instructions  — Copy instructions to .github/instructions/ in current dir
#   all           — Install for all tools (default)
#
# Flags:
#   --tool <name>     Install only the specified tool
#   --help            Show this help

set -euo pipefail

# --- Color helpers ---
if [[ -t 1 ]]; then
  C_GREEN=$'\033[0;32m'
  C_YELLOW=$'\033[1;33m'
  C_RED=$'\033[0;31m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RESET=$'\033[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi

ok()     { printf "${C_GREEN}[OK]${C_RESET}  %s\n" "$*"; }
warn()   { printf "${C_YELLOW}[!!]${C_RESET}  %s\n" "$*"; }
err()    { printf "${C_RED}[ERR]${C_RESET} %s\n" "$*" >&2; }
header() { printf "\n${C_BOLD}%s${C_RESET}\n" "$*"; }
dim()    { printf "${C_DIM}%s${C_RESET}\n" "$*"; }

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INTEGRATIONS="$REPO_ROOT/integrations"

ALL_TOOLS=(copilot instructions)

# --- Usage ---
usage() {
  sed -n '3,19p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# --- Preflight ---
check_integrations() {
  if [[ ! -d "$INTEGRATIONS" ]]; then
    err "integrations/ not found. Run ./scripts/convert.sh first."
    exit 1
  fi
}

# --- Installer ---

install_copilot() {
  local src="$INTEGRATIONS/copilot/agents"
  local dest="${PWD}/.github/agents"
  local count=0

  if [[ ! -d "$src" ]]; then
    err "integrations/copilot/agents missing. Run convert.sh --tool copilot first."
    return 1
  fi

  mkdir -p "$dest"

  local f
  while IFS= read -r -d '' f; do
    cp "$f" "$dest/"
    (( count++ )) || true
  done < <(find "$src" -maxdepth 1 -name "*.agent.md" -type f -print0)

  ok "Copilot: $count agents -> $dest"
  warn "Copilot: project-scoped. Run from your project root to install there."
}

install_instructions() {
  local src="$INTEGRATIONS/instructions"
  local dest="${PWD}/.github/instructions"
  local count=0

  if [[ ! -d "$src" ]]; then
    err "integrations/instructions missing. Run convert.sh --tool instructions first."
    return 1
  fi

  mkdir -p "$dest"

  local f
  while IFS= read -r -d '' f; do
    cp "$f" "$dest/"
    (( count++ )) || true
  done < <(find "$src" -maxdepth 1 -name "*.md" -type f -print0)

  ok "Instructions: $count files -> $dest"
}

install_tool() {
  case "$1" in
    copilot) install_copilot ;;
    instructions) install_instructions ;;
  esac
}

# --- Entry point ---

main() {
  local tool="all"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --tool)   tool="${2:?'--tool requires a value'}"; shift 2 ;;
      --help|-h) usage ;;
      *)         err "Unknown option: $1"; usage ;;
    esac
  done

  check_integrations

  # Validate explicit tool
  if [[ "$tool" != "all" ]]; then
    local valid=false t
    for t in "${ALL_TOOLS[@]}"; do [[ "$t" == "$tool" ]] && valid=true && break; done
    if ! $valid; then
      err "Unknown tool '$tool'. Valid: ${ALL_TOOLS[*]}"
      exit 1
    fi
  fi

  local selected_tools=()
  if [[ "$tool" == "all" ]]; then
    selected_tools=("${ALL_TOOLS[@]}")
  else
    selected_tools=("$tool")
  fi

  header "Installing agents"
  printf "  Repo:       %s\n" "$REPO_ROOT"
  printf "  Installing: %s\n" "${selected_tools[*]}"
  printf "\n"

  local installed=0 t
  for t in "${selected_tools[@]}"; do
    install_tool "$t"
    (( installed++ )) || true
  done

  printf "\n"
  ok "Done! Installed $installed tool(s)."
  printf "\n"
  dim "  Run ./scripts/convert.sh to regenerate after adding or editing agents."
  printf "\n"
}

main "$@"
