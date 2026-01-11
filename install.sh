#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check OS
OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM=linux;;
    Darwin*) PLATFORM=macos;;
    *)       error "Unsupported OS: $OS";;
esac

info "Installing kd (키즈노트 앨범 다운로더)..."

# Install uv if not present
if ! command -v uv &> /dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        error "Failed to install uv. Please install manually: https://docs.astral.sh/uv/"
    fi
fi

info "uv version: $(uv --version)"

# Install kd using uv tool
info "Installing kd..."
uv tool install --force git+https://github.com/bestend/kidsnote.git

# Install Playwright browser
info "Installing Chromium browser for login..."
uv tool run --from git+https://github.com/bestend/kidsnote.git playwright install chromium

# Verify installation
if command -v kd &> /dev/null; then
    echo ""
    info "✅ Installation complete!"
    echo ""
    echo "Usage:"
    echo "  kd login      # 브라우저로 키즈노트 로그인"
    echo "  kd config     # 다운로드 경로 설정"
    echo "  kd list       # 아이 목록 확인"
    echo "  kd fetch      # 앨범 목록 가져오기"
    echo "  kd download   # 다운로드"
    echo ""
    echo "  kd update     # 최신 버전으로 업데이트"
    echo "  kd version    # 현재 버전 확인"
    echo ""
else
    warn "kd command not found in PATH."
    warn "Add ~/.local/bin to your PATH:"
    echo ""
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
    echo "Then restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
fi
