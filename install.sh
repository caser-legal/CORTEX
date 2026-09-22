#!/bin/bash
# CORTEX Installation Script
# Installs both DORY and PULSE components

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORTEX_DIR="$SCRIPT_DIR"

echo "🧠 CORTEX Installation"
echo "======================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18+ required. Found: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v)"
echo "✅ Python $(python3 --version)"
echo ""

# Install DORY
echo "📦 Installing DORY..."
cd "$CORTEX_DIR/dory"

if [ ! -f "package.json" ]; then
    echo "❌ DORY package.json not found"
    exit 1
fi

npm install

if [ ! -f ".env.local" ]; then
    cp .env.example .env.local
    echo "⚠️  Created .env.local - Please add your NVIDIA_API_KEY"
fi

echo "✅ DORY installed"
echo ""

# Install PULSE
echo "📦 Installing PULSE..."
CODEX_DIR="$HOME/.codex"

mkdir -p "$CODEX_DIR"

# Copy PULSE files
cp -r "$CORTEX_DIR/pulse/agents" "$CODEX_DIR/"
cp -r "$CORTEX_DIR/pulse/prompts" "$CODEX_DIR/"
cp -r "$CORTEX_DIR/pulse/memory" "$CODEX_DIR/"
cp -r "$CORTEX_DIR/pulse/scripts" "$CODEX_DIR/"
cp -r "$CORTEX_DIR/pulse/tools" "$CODEX_DIR/"
cp -r "$CORTEX_DIR/pulse/skills" "$CODEX_DIR/"
cp -r "$CORTEX_DIR/pulse/rules" "$CODEX_DIR/"
cp "$CORTEX_DIR/pulse/autoogpt.py" "$CODEX_DIR/"
cp "$CORTEX_DIR/pulse/autoqagpt.py" "$CODEX_DIR/"

# Create config if not exists
if [ ! -f "$CODEX_DIR/config.toml" ]; then
    cat > "$CODEX_DIR/config.toml" << EOF
# PULSE Configuration
model = "o4-mini"
model_provider = "openai"

# MCP Server integration (connects to DORY)
[mcp_servers.dory]
command = "npx"
args = ["tsx", "$CORTEX_DIR/dory/mcp-server.ts"]
cwd = "$CORTEX_DIR/dory"
startup_timeout_sec = 120
tool_timeout_sec = 120
env = { NVIDIA_API_KEY = "\${NVIDIA_API_KEY}" }
EOF
    echo "⚠️  Created ~/.codex/config.toml - Please review settings"
fi

# Make scripts executable
chmod +x "$CODEX_DIR/scripts/"*.sh 2>/dev/null || true
chmod +x "$CODEX_DIR/autoogpt.py"
chmod +x "$CODEX_DIR/autoqagpt.py"

echo "✅ PULSE installed to ~/.codex"
echo ""

# Create convenience aliases
echo "📝 Creating convenience commands..."

# Create cortex command
cat > "$CORTEX_DIR/cortex" << 'EOF'
#!/bin/bash
CORTEX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$1" in
    start|web)
        echo "Starting DORY web interface..."
        cd "$CORTEX_DIR/dory" && npm run dev
        ;;
    mcp)
        echo "Starting MCP server..."
        cd "$CORTEX_DIR/dory" && npx tsx mcp-server.ts
        ;;
    build)
        shift
        echo "Running PULSE build agent..."
        ~/.codex/autoogpt.py "$@"
        ;;
    qa)
        shift
        echo "Running PULSE QA agent..."
        ~/.codex/autoqagpt.py "$@"
        ;;
    monitor)
        echo "Starting PULSE monitor..."
        ~/.codex/scripts/monitor.sh
        ;;
    *)
        echo "CORTEX - Unified AI Agent System"
        echo ""
        echo "Usage: cortex <command>"
        echo ""
        echo "Commands:"
        echo "  start, web    Start DORY web interface (localhost:3000)"
        echo "  mcp           Start MCP server only"
        echo "  build -p <path>  Run PULSE build agent on project"
        echo "  qa -p <path>     Run PULSE QA agent on project"
        echo "  monitor       Start PULSE agent monitor"
        ;;
esac
EOF
chmod +x "$CORTEX_DIR/cortex"

echo "✅ Created 'cortex' command"
echo ""

# Summary
echo "======================================"
echo "🧠 CORTEX Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Add your NVIDIA API key:"
echo "   Edit: $CORTEX_DIR/dory/.env.local"
echo "   Set:  NVIDIA_API_KEY=nvapi-xxx"
echo ""
echo "2. Start DORY web interface:"
echo "   cd $CORTEX_DIR/dory && npm run dev"
echo "   Open: http://localhost:3000"
echo ""
echo "3. Use PULSE agents:"
echo "   ~/.codex/autoogpt.py -p /path/to/project"
echo "   ~/.codex/autoqagpt.py -p /path/to/project"
echo ""
echo "4. Or use the cortex command:"
echo "   $CORTEX_DIR/cortex start"
echo "   $CORTEX_DIR/cortex build -p /path/to/project"
echo ""
echo "Documentation: $CORTEX_DIR/README.md"
