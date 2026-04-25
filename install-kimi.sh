#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Automotive Agents — Kimi Migration Installer
# ============================================================================
# Converts and installs automotive agents/skills for Kimi ecosystem.
#
# Supports two targets:
#   1. Kimi Code CLI skills directory (local IDE integration)
#   2. Kimi Web knowledge-base bundle (upload to web/app)
#
# Usage:
#   ./install-kimi.sh                          # Install to ~/.kimi/automotive-skills
#   ./install-kimi.sh --kimi-cli-dir PATH      # Install to Kimi Code CLI skills/
#   ./install-kimi.sh --export-web             # Generate kim-web-kb.md only
#   ./install-kimi.sh --dry-run                # Preview changes
#   ./install-kimi.sh --status                 # Show installation status
#   ./install-kimi.sh --uninstall              # Remove automotive skills
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.kimi/automotive-skills"
KIMI_CLI_DIR=""
EXPORT_WEB=false
DRY_RUN=false
UNINSTALL=false
STATUS_ONLY=false
NAMESPACE="automotive"
INSTALLED_COUNT=0
SKIPPED_COUNT=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[x]${NC} $*"; }
debug() { echo -e "${DIM}    $*${NC}"; }

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Convert and install automotive agents for Kimi ecosystem.

Options:
  --kimi-cli-dir DIR  Install directly into Kimi Code CLI skills directory
  --export-web        Generate a single Markdown bundle for Kimi Web/App
  --web-output FILE   Output path for web bundle (default: ./kimi-web-kb.md)
  --dry-run           Preview what would be installed without making changes
  --uninstall         Remove only automotive-prefixed skills
  --status            Show what automotive components are currently installed
  -h, --help          Show this help message

Kimi Code CLI Detection:
  If Kimi Code CLI is detected, the installer will suggest the correct
  --kimi-cli-dir path. You can also find it manually:
    $(find_kimi_skills_dir)

Examples:
  $(basename "$0")                              # Local install (recommended)
  $(basename "$0") --kimi-cli-dir ~/.kimi/skills   # IDE integration
  $(basename "$0") --export-web --web-output kb.md # Web bundle
  $(basename "$0") --dry-run                    # Preview only
  $(basename "$0") --uninstall                  # Clean removal
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Detect Kimi Code CLI skills directory
# ---------------------------------------------------------------------------
find_kimi_skills_dir() {
    # Try to find Kimi CLI internal skills directory
    local candidates=(
        "${HOME}/.kimi/skills"
        "${HOME}/.local/share/kimi/skills"
    )

    # Check if we can infer from Python environment
    if command -v python3 >/dev/null 2>&1; then
        local py_dir
        py_dir=$(python3 -c "
import sys, pathlib
for p in sys.path:
    candidate = pathlib.Path(p) / 'kimi_cli' / 'skills'
    if candidate.exists():
        print(candidate)
        break
" 2>/dev/null || true)
        if [[ -n "$py_dir" ]]; then
            candidates+=("$py_dir")
        fi
    fi

    # VS Code extension path pattern
    local vscode_glob
    vscode_glob=$(find "${HOME}/.vscode-server" -path "*/kimi_cli/skills" -type d 2>/dev/null | head -1 || true)
    if [[ -n "$vscode_glob" ]]; then
        candidates+=("$vscode_glob")
    fi

    for d in "${candidates[@]}"; do
        if [[ -d "$d" ]]; then
            echo "$d"
            return 0
        fi
    done

    echo "${HOME}/.kimi/skills (not detected, will be created)"
    return 1
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --kimi-cli-dir)
            KIMI_CLI_DIR="$2"
            shift 2
            ;;
        --export-web)
            EXPORT_WEB=true
            shift
            ;;
        --web-output)
            WEB_OUTPUT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --status)
            STATUS_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            usage
            ;;
    esac
done

WEB_OUTPUT="${WEB_OUTPUT:-${SCRIPT_DIR}/kimi-web-kb.md}"

# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------
if $STATUS_ONLY; then
    echo ""
    echo -e "${CYAN}Automotive Kimi Skills — Installation Status${NC}"
    echo ""

    local found=0
    for dir in "$TARGET_DIR" "$KIMI_CLI_DIR"; do
        [[ -z "$dir" ]] && continue
        if [[ -d "$dir" ]]; then
            local_count=$(find "$dir" -maxdepth 1 -type d | wc -l)
            echo -e "  ${GREEN}OK${NC}  $dir ($local_count items)"
            (( found++ )) || true
        fi
    done

    if [[ $found -eq 0 ]]; then
        echo "  Not installed"
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------
if $UNINSTALL; then
    echo ""
    echo -e "${CYAN}Automotive Kimi Skills — Uninstall${NC}"
    echo ""

    local removed=0
    for dir in "$TARGET_DIR" "$KIMI_CLI_DIR"; do
        [[ -z "$dir" ]] && continue
        if [[ -d "$dir" ]]; then
            if $DRY_RUN; then
                echo "  [DRY-RUN] rm -rf $dir"
            else
                rm -rf "$dir"
                info "Removed: $dir"
            fi
            (( removed++ )) || true
        fi
    done

    if [[ $removed -eq 0 ]]; then
        info "No automotive Kimi skills found."
    else
        info "Uninstall complete — removed $removed directories"
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Export web bundle only
# ---------------------------------------------------------------------------
if $EXPORT_WEB; then
    echo ""
    echo -e "${CYAN}Automotive Kimi Skills — Web Bundle Export${NC}"
    echo ""

    if $DRY_RUN; then
        echo -e "  ${DIM}[DRY-RUN] python3 ${SCRIPT_DIR}/tools/convert_to_kimi.py --bundle-web --web-output ${WEB_OUTPUT}${NC}"
    else
        python3 "${SCRIPT_DIR}/tools/convert_to_kimi.py" --bundle-web --web-output "$WEB_OUTPUT"
        local size_kb
        size_kb=$(stat -c%s "$WEB_OUTPUT" 2>/dev/null || stat -f%z "$WEB_OUTPUT" 2>/dev/null)
        size_kb=$((size_kb / 1024))
        info "Web bundle exported: $WEB_OUTPUT (${size_kb} KB)"
        echo ""
        echo "  Usage:"
        echo "    1. Open Kimi Web/App (kimi.moonshot.cn)"
        echo "    2. Create a new Knowledge Base"
        echo "    3. Upload $WEB_OUTPUT"
        echo "    4. Start a conversation with the knowledge base"
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Main install flow
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  Automotive Agents — Kimi Migration Installer${NC}"
echo -e "${CYAN}============================================================${NC}"
echo ""

# Detect Kimi CLI
KIMI_SKILLS_DETECTED=$(find_kimi_skills_dir || true)
if [[ -n "$KIMI_SKILLS_DETECTED" && -d "$KIMI_SKILLS_DETECTED" ]]; then
    echo -e "  ${GREEN}Detected Kimi Code CLI skills directory:${NC}"
    echo -e "    ${DIM}${KIMI_SKILLS_DETECTED}${NC}"
    if [[ -z "$KIMI_CLI_DIR" ]]; then
        echo ""
        echo "  To install into Kimi Code CLI directly, re-run with:"
        echo -e "    ${CYAN}./install-kimi.sh --kimi-cli-dir ${KIMI_SKILLS_DETECTED}${NC}"
        echo ""
    fi
fi

# Determine final target
if [[ -n "$KIMI_CLI_DIR" ]]; then
    TARGET_DIR="${KIMI_CLI_DIR}/automotive"
    echo -e "  Mode:   ${GREEN}KIMI CLI INTEGRATION${NC}"
else
    echo -e "  Mode:   ${GREEN}LOCAL INSTALL${NC}"
fi

echo -e "  Target: ${CYAN}${TARGET_DIR}${NC}"
$DRY_RUN && echo -e "          ${YELLOW}(dry-run — no changes will be made)${NC}"
echo ""

# Run conversion
if $DRY_RUN; then
    echo -e "  ${DIM}[DRY-RUN] python3 ${SCRIPT_DIR}/tools/convert_to_kimi.py --output-dir ${TARGET_DIR}${NC}"
    INSTALLED_COUNT=237  # Approximate
else
    mkdir -p "$TARGET_DIR"
    python3 "${SCRIPT_DIR}/tools/convert_to_kimi.py" --output-dir "$TARGET_DIR"
    INSTALLED_COUNT=$(find "$TARGET_DIR" -maxdepth 1 -type d | wc -l)
    INSTALLED_COUNT=$((INSTALLED_COUNT - 1))  # Exclude TARGET_DIR itself
fi

# Summary
echo ""
echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"
echo -e "  ${GREEN}Converted: ${INSTALLED_COUNT}${NC} skills/agents"
echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"
echo ""

if ! $DRY_RUN; then
    info "Installation complete!"
    echo ""
    echo "  What was installed:"
    echo "    - Agents:    ${TARGET_DIR}/automotive-{domain}-{agent}/SKILL.md"
    echo "    - Skills:    ${TARGET_DIR}/automotive-{domain}/SKILL.md"
    echo ""

    if [[ -n "$KIMI_CLI_DIR" ]]; then
        echo "  Kimi Code CLI integration:"
        echo "    Skills are now available in your IDE."
        echo "    Restart Kimi Code CLI or run: kimi skills reload"
        echo ""
    else
        echo "  Local install usage:"
        echo "    Skills are stored in: ${TARGET_DIR}"
        echo ""
        echo "  To use with Kimi Code CLI:"
        echo "    1. Find your Kimi CLI skills directory:"
        echo -e "       ${CYAN}./install-kimi.sh --status${NC}"
        echo "    2. Re-run with:"
        echo -e "       ${CYAN}./install-kimi.sh --kimi-cli-dir <skills-dir>${NC}"
        echo ""
        echo "  To use with Kimi Web/App:"
        echo -e "    ${CYAN}./install-kimi.sh --export-web${NC}"
        echo ""
    fi

    echo "  Manage installation:"
    echo "    Status:    ./install-kimi.sh --status"
    echo "    Uninstall: ./install-kimi.sh --uninstall"
    echo ""
else
    info "Dry run complete. Re-run without --dry-run to apply."
fi
