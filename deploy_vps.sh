#!/bin/bash
# =============================================================================
# VPS Worker Deployment Script for Traffic Engine
# Installs Chrome, Python, dependencies, and sets up systemd worker service.
#
# Usage:
#   ssh user@vps "bash -s" < deploy_vps.sh --master-url http://MASTER_IP:5000
#   ssh user@vps "bash -s" < deploy_vps.sh --master-url http://MASTER_IP:5000 --max-chrome 5
#
# Prerequisites: Ubuntu 20.04+ / Debian 11+ with sudo access
# Network: Worker needs OUTBOUND only (no inbound ports required)
# =============================================================================

set -euo pipefail

# --- Parse arguments ---
MASTER_URL="http://localhost:5000"
WORKER_ID="vps-$(hostname)-$(date +%s)"
MAX_CHROME=3
REPO_URL=""
REPO_BRANCH="main"
INSTALL_DIR="/opt/traffic-engine"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_NAME="traffic-worker"
SERVICE_USER="traffic"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --master-url)  MASTER_URL="$2"; shift 2 ;;
        --worker-id)   WORKER_ID="$2"; shift 2 ;;
        --max-chrome)  MAX_CHROME="$2"; shift 2 ;;
        --repo)        REPO_URL="$2"; shift 2 ;;
        --branch)      REPO_BRANCH="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; VENV_DIR="$INSTALL_DIR/venv"; shift 2 ;;
        *)             echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "============================================="
echo "  Traffic Engine - VPS Worker Deployment"
echo "============================================="
echo "  Master URL : $MASTER_URL"
echo "  Worker ID  : $WORKER_ID"
echo "  Max Chrome : $MAX_CHROME"
echo "  Install Dir: $INSTALL_DIR"
echo "============================================="
echo ""

# --- Step 1: System packages ---
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-venv python3-pip \
    wget curl unzip gnupg2 \
    fonts-nanum fonts-nanum-coding \
    xvfb \
    > /dev/null 2>&1
echo "  -> System packages installed"

# --- Step 2: Install Google Chrome ---
echo "[2/6] Installing Google Chrome..."
if ! command -v google-chrome-stable &> /dev/null; then
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt-get install -y -qq /tmp/chrome.deb > /dev/null 2>&1 || {
        # Fix broken dependencies if needed
        sudo apt-get -f install -y -qq > /dev/null 2>&1
        sudo apt-get install -y -qq /tmp/chrome.deb > /dev/null 2>&1
    }
    rm -f /tmp/chrome.deb
    echo "  -> Chrome installed: $(google-chrome-stable --version)"
else
    echo "  -> Chrome already installed: $(google-chrome-stable --version)"
fi

# --- Step 3: Create service user ---
echo "[3/6] Setting up service user..."
if ! id "$SERVICE_USER" &> /dev/null; then
    sudo useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false "$SERVICE_USER"
    echo "  -> User '$SERVICE_USER' created"
else
    echo "  -> User '$SERVICE_USER' already exists"
fi

# --- Step 4: Deploy code ---
echo "[4/6] Deploying engine code..."
sudo mkdir -p "$INSTALL_DIR"

if [ -n "$REPO_URL" ]; then
    # Clone or pull from git
    if [ -d "$INSTALL_DIR/.git" ]; then
        sudo -u "$SERVICE_USER" git -C "$INSTALL_DIR" pull origin "$REPO_BRANCH" --ff-only
        echo "  -> Code updated from git"
    else
        sudo rm -rf "$INSTALL_DIR"
        sudo git clone --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
        echo "  -> Code cloned from git"
    fi
else
    # Copy from current directory (when running via scp/rsync)
    if [ -f "worker.py" ]; then
        sudo cp -f worker.py engine_selenium.py engine_place.py engine_blog.py \
            requirements.txt database.py "$INSTALL_DIR/" 2>/dev/null || true
        echo "  -> Code copied from local directory"
    else
        echo "  WARNING: No repo URL and no local files found."
        echo "  Copy your engine files to $INSTALL_DIR manually, or re-run with --repo <git-url>"
    fi
fi

sudo mkdir -p "$INSTALL_DIR/data"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# --- Step 5: Python venv + dependencies ---
echo "[5/6] Setting up Python environment..."
if [ ! -d "$VENV_DIR" ]; then
    sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
fi
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --quiet --upgrade pip
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
echo "  -> Python venv ready: $VENV_DIR"

# --- Step 6: Create systemd service ---
echo "[6/6] Creating systemd service..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<UNIT
[Unit]
Description=Traffic Engine Worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python worker.py \\
    --master-url $MASTER_URL \\
    --worker-id $WORKER_ID \\
    --max-chrome $MAX_CHROME \\
    --headless
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Environment
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:99

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=$INSTALL_DIR/data /tmp
PrivateTmp=yes

# Resource limits
LimitNOFILE=65536
MemoryMax=2G

[Install]
WantedBy=multi-user.target
UNIT

# Xvfb service for virtual display (Chrome needs it even in headless)
sudo tee "/etc/systemd/system/xvfb.service" > /dev/null <<XVFB
[Unit]
Description=X Virtual Framebuffer
Before=${SERVICE_NAME}.service

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
XVFB

sudo systemctl daemon-reload
sudo systemctl enable xvfb.service
sudo systemctl start xvfb.service
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl start "${SERVICE_NAME}.service"

echo ""
echo "============================================="
echo "  Deployment Complete!"
echo "============================================="
echo ""
echo "  Service: $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
echo "  Worker connects to: $MASTER_URL"
echo "  Worker ID: $WORKER_ID"
echo ""
echo "  NOTE: The worker only needs OUTBOUND network access."
echo "  No inbound firewall ports need to be opened."
echo "============================================="
