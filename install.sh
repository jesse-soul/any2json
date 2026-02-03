#!/bin/bash
# any2json installer
# Usage: curl -sSL https://any2json.ai/install | bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "   __ _ _ __  _   _|__ \\(_)___  ___  _ __  "
echo "  / _\` | '_ \\| | | | / /| / __|/ _ \\| '_ \\ "
echo " | (_| | | | | |_| |/ /_| \\__ \\ (_) | | | |"
echo "  \\__,_|_| |_|\\__, /____| |___/\\___/|_| |_|"
echo "              |___/    |__/                 "
echo -e "${NC}"
echo "Installing any2json CLI..."
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Create directory
INSTALL_DIR="$HOME/.any2json"
mkdir -p "$INSTALL_DIR"

# Download CLI
echo -e "${BLUE}Downloading CLI...${NC}"
curl -sSL https://any2json.ai/cli/any2json.py -o "$INSTALL_DIR/any2json.py"
chmod +x "$INSTALL_DIR/any2json.py"

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip3 install --quiet --user rich httpx pyotp qrcode 2>/dev/null || pip3 install --quiet rich httpx pyotp qrcode

# Create wrapper
cat > "$INSTALL_DIR/any2json" << 'EOF'
#!/bin/bash
python3 "$HOME/.any2json/any2json.py" "$@"
EOF
chmod +x "$INSTALL_DIR/any2json"

# Add to PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "" >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.any2json:$PATH"' >> "$HOME/.bashrc"
    echo "" >> "$HOME/.zshrc" 2>/dev/null || true
    echo 'export PATH="$HOME/.any2json:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
fi

echo
echo -e "${GREEN}✓ Installation complete!${NC}"
echo
echo "Run 'any2json' to start (may need to restart terminal)"
echo "Or run now: $INSTALL_DIR/any2json"
echo

# Auto-launch
export PATH="$INSTALL_DIR:$PATH"
exec "$INSTALL_DIR/any2json"
