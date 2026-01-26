#!/bin/bash

# ============================================
# Enhanced Beautification Library for Remote Tools
# ASCII Art & Rich Color Rendering
# ============================================

# Extended Color Definitions
export BLACK='\033[0;30m'
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[0;33m'
export BLUE='\033[0;34m'
export MAGENTA='\033[0;35m'
export CYAN='\033[0;36m'
export WHITE='\033[0;37m'
export GRAY='\033[0;90m'
export LIGHT_RED='\033[0;91m'
export LIGHT_GREEN='\033[0;92m'
export LIGHT_YELLOW='\033[0;93m'
export LIGHT_BLUE='\033[0;94m'
export LIGHT_MAGENTA='\033[0;95m'
export LIGHT_CYAN='\033[0;96m'
export BRIGHT_WHITE='\033[0;97m'

# Text Styles
export BOLD='\033[1m'
export DIM='\033[2m'
export ITALIC='\033[3m'
export UNDERLINE='\033[4m'
export BLINK='\033[5m'
export REVERSE='\033[7m'
export HIDDEN='\033[8m'
export STRIKE='\033[9m'
export NC='\033[0m' # No Color

# Background Colors
export BG_RED='\033[41m'
export BG_GREEN='\033[42m'
export BG_YELLOW='\033[43m'
export BG_BLUE='\033[44m'
export BG_MAGENTA='\033[45m'
export BG_CYAN='\033[46m'
export BG_WHITE='\033[47m'

# 256 Color Support
color256() { echo -e "\033[38;5;${1}m"; }
bg256() { echo -e "\033[48;5;${1}m"; }

# Gradient Text Function
gradient_text() {
    local text="$1"
    local start_color="${2:-196}"  # Default red start
    local end_color="${3:-226}"    # Default yellow end
    local len=${#text}
    
    if [ $len -eq 0 ]; then
        return
    fi
    
    for (( i=0; i<len; i++ )); do
        local progress=$(( i * 100 / len ))
        local color=$(( start_color + (end_color - start_color) * progress / 100 ))
        echo -en "$(color256 $color)${text:$i:1}"
    done
    echo -en "${NC}"
}

# ASCII Art Banner
print_ascii_banner() {
    local title="$1"
    local style="${2:-1}"
    
    case $style in
        1) # 3D Style for REMOTE
            echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
            echo -e "${CYAN}║${NC}  $(gradient_text '██████╗ ███████╗███╗   ███╗ ██████╗ ████████╗███████╗' 196 226)  ${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}  $(gradient_text '██╔══██╗██╔════╝████╗ ████║██╔═══██╗╚══██╔══╝██╔════╝' 196 226)  ${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}  $(gradient_text '██████╔╝█████╗  ██╔████╔██║██║   ██║   ██║   █████╗  ' 196 226)  ${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}  $(gradient_text '██╔══██╗██╔══╝  ██║╚██╔╝██║██║   ██║   ██║   ██╔══╝  ' 196 226)  ${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}  $(gradient_text '██║  ██║███████╗██║ ╚═╝ ██║╚██████╔╝   ██║   ███████╗' 196 226)  ${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}  $(gradient_text '╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝    ╚═╝   ╚══════╝' 196 226)  ${CYAN}║${NC}"
            echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
            ;;
        2) # Double Line Box
            local len=${#title}
            local total_width=60
            local padding=$(( (total_width - len - 2) / 2 ))
            echo -e "${LIGHT_BLUE}╔$(printf '═%.0s' $(seq 1 $((total_width-2))))╗${NC}"
            echo -e "${LIGHT_BLUE}║${NC}$(printf ' %.0s' $(seq 1 $padding))${BOLD}$(gradient_text "$title" 51 87)${NC}$(printf ' %.0s' $(seq 1 $((total_width-len-padding-2))))${LIGHT_BLUE}║${NC}"
            echo -e "${LIGHT_BLUE}╚$(printf '═%.0s' $(seq 1 $((total_width-2))))╝${NC}"
            ;;
        3) # Minimalist Style
            echo -e "${LIGHT_CYAN}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
            echo -e "${LIGHT_CYAN}┃${NC} $(center_text "$title" 52 "${BOLD}${LIGHT_GREEN}") ${LIGHT_CYAN}┃${NC}"
            echo -e "${LIGHT_CYAN}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"
            ;;
    esac
}

# Rainbow Separator
print_rainbow_separator() {
    local width="${1:-60}"
    local char="${2:-═}"
    local colors=(196 202 208 214 220 226 190 154 118 82 46 47 48 49 50 51 87 123 159 195)
    
    for (( i=0; i<width; i++ )); do
        local color_index=$(( i % ${#colors[@]} ))
        echo -en "$(color256 ${colors[$color_index]})$char"
    done
    echo -e "${NC}"
}

# Simple Separator
print_separator() {
    local char="${1:-─}"
    local width="${2:-60}"
    local color="${3:-$CYAN}"
    echo -e "${color}$(printf '%*s' "$width" | tr ' ' "$char")${NC}"
}

# Spinner Animation Frames
SPINNER_FRAMES=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
SPINNER_PID=""

# Start Spinner
start_spinner() {
    local msg="${1:-Loading}"
    (
        local i=0
        local colors=(51 50 49 48 47 46 82 118 154 190 226 220 214 208 202 196)
        while true; do
            local color_index=$(( i % ${#colors[@]} ))
            printf "\r$(color256 ${colors[$color_index]})${SPINNER_FRAMES[$i]}${NC} ${CYAN}%s${NC}" "$msg"
            i=$(( (i + 1) % ${#SPINNER_FRAMES[@]} ))
            sleep 0.1
        done
    ) &
    SPINNER_PID=$!
}

# Stop Spinner
stop_spinner() {
    if [ -n "$SPINNER_PID" ]; then
        kill "$SPINNER_PID" 2>/dev/null
        wait "$SPINNER_PID" 2>/dev/null
        SPINNER_PID=""
        printf "\r%*s\r" 80 ""  # Clear line
    fi
}

# Status Messages with Icons
print_status() {
    local status="$1"
    local message="$2"
    local icon="${3:-}"
    
    case "$status" in
        "success")
            echo -e "${GREEN}${icon:-✓}${NC} ${message}"
            ;;
        "error")
            echo -e "${RED}${icon:-✗}${NC} ${message}"
            ;;
        "warning")
            echo -e "${YELLOW}${icon:-⚠}${NC} ${message}"
            ;;
        "info")
            echo -e "${BLUE}${icon:-ℹ}${NC} ${message}"
            ;;
        "processing")
            echo -e "${CYAN}${icon:-⏳}${NC} ${message}"
            ;;
        *)
            echo -e "${message}"
            ;;
    esac
}

# Animated Status Display
print_status_animated() {
    local status="$1"
    local message="$2"
    
    case "$status" in
        "success")
            echo -e "${GREEN}┌─────────────┐${NC}"
            echo -e "${GREEN}│${NC} ${LIGHT_GREEN}✓ SUCCESS${NC} ${GREEN}│${NC}"
            echo -e "${GREEN}└─────────────┘${NC}"
            echo -e "  ${BOLD}${message}${NC}"
            ;;
        "error")
            echo -e "${RED}╔═════════════╗${NC}"
            echo -e "${RED}║${NC} ${LIGHT_RED}✗ ERROR${NC}   ${RED}║${NC}"
            echo -e "${RED}╚═════════════╝${NC}"
            echo -e "  ${BOLD}${message}${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}┏━━━━━━━━━━━━━┓${NC}"
            echo -e "${YELLOW}┃${NC} ${LIGHT_YELLOW}⚠ WARNING${NC} ${YELLOW}┃${NC}"
            echo -e "${YELLOW}┗━━━━━━━━━━━━━┛${NC}"
            echo -e "  ${message}"
            ;;
    esac
}

# Advanced Progress Bar
show_advanced_progress() {
    local current="$1"
    local total="$2"
    local width="${3:-50}"
    local label="${4:-}"
    
    if [ "$total" -eq 0 ]; then
        return
    fi
    
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    
    # Choose color based on percentage
    local bar_color=""
    if [ $percent -lt 30 ]; then
        bar_color="${RED}"
    elif [ $percent -lt 60 ]; then
        bar_color="${YELLOW}"
    elif [ $percent -lt 90 ]; then
        bar_color="${LIGHT_BLUE}"
    else
        bar_color="${GREEN}"
    fi
    
    printf "\r${CYAN}[${NC}"
    
    # Gradient fill
    for (( i=0; i<filled; i++ )); do
        local color=$(( 46 + (i * 4) % 40 ))
        echo -en "$(color256 $color)█"
    done
    
    echo -en "${GRAY}"
    printf '%*s' $empty | tr ' ' '░'
    echo -en "${NC}${CYAN}]${NC}"
    
    printf " ${BOLD}${bar_color}%3d%%${NC}" "$percent"
    
    if [ -n "$label" ]; then
        printf " ${GRAY}%s${NC}" "$label"
    fi
    
    if [ "$current" -eq "$total" ]; then
        echo
    fi
}

# Format Duration
format_duration() {
    local seconds="$1"
    
    if [ "$seconds" -lt 60 ]; then
        echo "${seconds}s"
    elif [ "$seconds" -lt 3600 ]; then
        local minutes=$((seconds / 60))
        local secs=$((seconds % 60))
        echo "${minutes}m ${secs}s"
    else
        local hours=$((seconds / 3600))
        local minutes=$(((seconds % 3600) / 60))
        local secs=$((seconds % 60))
        echo "${hours}h ${minutes}m ${secs}s"
    fi
}

# Colored Table Functions
print_colored_table_header() {
    local -a headers=("$@")
    local width=20
    local header_color="${LIGHT_CYAN}"
    local border_color="${CYAN}"
    
    # Table top
    echo -en "${border_color}┌"
    for ((i=0; i<${#headers[@]}; i++)); do
        printf '─%.0s' $(seq 1 $width)
        if [ $i -lt $((${#headers[@]}-1)) ]; then
            echo -en "┬"
        fi
    done
    echo -e "┐${NC}"
    
    # Headers
    echo -en "${border_color}│${NC}"
    for header in "${headers[@]}"; do
        printf " ${header_color}${BOLD}%-*s${NC} ${border_color}│${NC}" $((width-2)) "$header"
    done
    echo
    
    # Middle separator
    echo -en "${border_color}├"
    for ((i=0; i<${#headers[@]}; i++)); do
        printf '─%.0s' $(seq 1 $width)
        if [ $i -lt $((${#headers[@]}-1)) ]; then
            echo -en "┼"
        fi
    done
    echo -e "┤${NC}"
}

print_colored_table_row() {
    local -a values=("$@")
    local width=20
    local border_color="${CYAN}"
    
    echo -en "${border_color}│${NC}"
    for value in "${values[@]}"; do
        # Remove color codes for length calculation
        local clean_value=$(echo -e "$value" | sed 's/\x1b\[[0-9;]*m//g')
        local padding=$((width - 2 - ${#clean_value}))
        echo -en " ${value}$(printf ' %.0s' $(seq 1 $padding)) ${border_color}│${NC}"
    done
    echo
}

print_colored_table_footer() {
    local cols="$1"
    local width=20
    local border_color="${CYAN}"
    
    echo -en "${border_color}└"
    for ((i=0; i<cols; i++)); do
        printf '─%.0s' $(seq 1 $width)
        if [ $i -lt $((cols-1)) ]; then
            echo -en "┴"
        fi
    done
    echo -e "┘${NC}"
}

# Output Frame Functions - Auto-width support
print_output_frame_start() {
    local title="${1:-Output}"
    local width="${2:-100}"  # Increased default width
    
    # Top border with gradient
    echo -en "$(color256 51)╔"
    for (( i=0; i<$((width-2)); i++ )); do
        local color=$(( 51 + (i * 36 / (width-2)) ))
        echo -en "$(color256 $color)═"
    done
    echo -e "$(color256 87)╗${NC}"
    
    # Title line
    echo -e "$(color256 51)║${NC} $(color256 226)▶${NC} ${BOLD}${LIGHT_GREEN}${title}${NC}"
    
    # Separator
    echo -en "$(color256 51)╟"
    for (( i=0; i<$((width-2)); i++ )); do
        echo -en "─"
    done
    echo -e "$(color256 87)╢${NC}"
}

print_output_frame_line() {
    local line="$1"
    # Don't wrap lines, show them as-is
    echo -e "$(color256 51)║${NC} ${line}"
}

print_output_frame_end() {
    local width="${1:-100}"  # Increased default width
    
    # Bottom border with gradient
    echo -en "$(color256 51)╚"
    for (( i=0; i<$((width-2)); i++ )); do
        local color=$(( 51 + (i * 36 / (width-2)) ))
        echo -en "$(color256 $color)═"
    done
    echo -e "$(color256 87)╝${NC}"
}

# Colored Icons
get_colored_icon() {
    local type="$1"
    
    case "$type" in
        "success") echo -e "${LIGHT_GREEN}✓${NC}" ;;
        "error") echo -e "${LIGHT_RED}✗${NC}" ;;
        "warning") echo -e "${LIGHT_YELLOW}⚠${NC}" ;;
        "info") echo -e "${LIGHT_BLUE}ℹ${NC}" ;;
        "server") echo -e "${LIGHT_CYAN}🖥${NC}" ;;
        "network") echo -e "${LIGHT_MAGENTA}🌐${NC}" ;;
        "file") echo -e "${LIGHT_BLUE}📄${NC}" ;;
        "time") echo -e "${LIGHT_YELLOW}⏱${NC}" ;;
        "lock") echo -e "${RED}🔒${NC}" ;;
        "key") echo -e "${GREEN}🔑${NC}" ;;
        "user") echo -e "${LIGHT_CYAN}👤${NC}" ;;
        "gear") echo -e "${GRAY}⚙${NC}" ;;
        "package") echo -e "${YELLOW}📦${NC}" ;;
        *) echo -e "•" ;;
    esac
}

# Center Text
center_text() {
    local text="$1"
    local width="$2"
    local color="${3:-}"
    
    local text_len=${#text}
    local padding=$(( (width - text_len) / 2 ))
    local padding_right=$(( width - text_len - padding ))
    
    echo -en "$(printf ' %.0s' $(seq 1 $padding))${color}${text}${NC}$(printf ' %.0s' $(seq 1 $padding_right))"
}

# Typewriter Effect
typewriter_effect() {
    local text="$1"
    local delay="${2:-0.03}"
    local color="${3:-$LIGHT_GREEN}"
    
    echo -en "${color}"
    for (( i=0; i<${#text}; i++ )); do
        echo -n "${text:i:1}"
        sleep $delay
    done
    echo -e "${NC}"
}

# Success/Failure ASCII Art
show_result_ascii() {
    local result="$1"
    
    if [ "$result" = "success" ]; then
        echo -e "${LIGHT_GREEN}"
        echo "    ╔═══════════════════════════════════════╗"
        echo "    ║       🎉 ALL TASKS PASSED! 🎉        ║"
        echo "    ║                                       ║"
        echo "    ║     ███████╗██╗   ██╗ ██████╗ ██╗    ║"
        echo "    ║     ██╔════╝██║   ██║██╔════╝ ██║    ║"
        echo "    ║     ███████╗██║   ██║██║      ██║    ║"
        echo "    ║     ╚════██║██║   ██║██║      ╚═╝    ║"
        echo "    ║     ███████║╚██████╔╝╚██████╗ ██╗    ║"
        echo "    ║     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝    ║"
        echo "    ╚═══════════════════════════════════════╝"
        echo -e "${NC}"
    else
        echo -e "${LIGHT_RED}"
        echo "    ╔═══════════════════════════════════════╗"
        echo "    ║      ⚠️  SOME TASKS FAILED  ⚠️        ║"
        echo "    ║                                       ║"
        echo "    ║     ███████╗ █████╗ ██╗██╗           ║"
        echo "    ║     ██╔════╝██╔══██╗██║██║           ║"
        echo "    ║     █████╗  ███████║██║██║           ║"
        echo "    ║     ██╔══╝  ██╔══██║██║██║           ║"
        echo "    ║     ██║     ██║  ██║██║███████╗      ║"
        echo "    ║     ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝      ║"
        echo "    ╚═══════════════════════════════════════╝"
        echo -e "${NC}"
    fi
}

# Percentage Bar
show_percentage_bar() {
    local current=$1
    local total=$2
    
    if [ "$total" -eq 0 ]; then
        echo "N/A"
        return
    fi
    
    local percent=$((current * 100 / total))
    local bar_width=20
    local filled=$((bar_width * percent / 100))
    
    # Choose color based on percentage
    local color=""
    if [ $percent -ge 90 ]; then
        color="${LIGHT_GREEN}"
    elif [ $percent -ge 70 ]; then
        color="${LIGHT_YELLOW}"
    else
        color="${LIGHT_RED}"
    fi
    
    echo -en "${color}"
    printf '%*s' $filled | tr ' ' '█'
    echo -en "${GRAY}"
    printf '%*s' $((bar_width - filled)) | tr ' ' '░'
    echo -en "${NC} ${BOLD}${color}${percent}%${NC}"
}

# Beauty Level Check
get_beauty_level() {
    echo "${REMOTE_BEAUTY_LEVEL:-2}"
}

# Apply beauty based on level
apply_beauty() {
    local level=$(get_beauty_level)
    if [ "$level" -eq 0 ]; then
        return 1  # No beauty
    fi
    return 0  # Apply beauty
}
