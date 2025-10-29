#!/bin/bash
# Installation script for Pedestrian Traffic Monitoring System
# Sets up auto-start on Raspberry Pi boot

set -e  # Exit on error

echo "=========================================="
echo "Pedestrian Traffic Monitoring"
echo "Auto-Start Installation Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run with sudo: sudo bash install.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo ~$ACTUAL_USER)
INSTALL_DIR="$USER_HOME/pedestrian-monitoring"

echo "📍 Installation directory: $INSTALL_DIR"
echo "👤 Running as user: $ACTUAL_USER"
echo ""

# Check if directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Error: Directory not found: $INSTALL_DIR"
    echo "Please ensure the project is located at $INSTALL_DIR"
    exit 1
fi

# Step 1: Install system dependencies
echo "📦 Step 1: Installing system dependencies..."
apt-get update -qq
apt-get install -y python3-pip bluetooth bluez libbluetooth-dev python3-dev

# Step 2: Install Python packages
echo "🐍 Step 2: Installing Python packages..."
cd "$INSTALL_DIR"
sudo -u $ACTUAL_USER pip3 install -r requirements.txt

# Step 3: Grant Bluetooth permissions
echo "🔓 Step 3: Granting Bluetooth permissions..."
setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))

# Step 4: Enable Bluetooth service
echo "📡 Step 4: Enabling Bluetooth service..."
systemctl enable bluetooth
systemctl start bluetooth

# Step 5: Install systemd service
echo "⚙️  Step 5: Installing auto-start service..."

# Update WorkingDirectory and ExecStart paths in service file
SERVICE_FILE="$INSTALL_DIR/deployment/traffic-scanner.service"
if [ -f "$SERVICE_FILE" ]; then
    # Copy service file to systemd directory
    cp "$SERVICE_FILE" /etc/systemd/system/traffic-scanner.service
    
    # Update paths in service file
    sed -i "s|/home/pi/pedestrian-monitoring|$INSTALL_DIR|g" /etc/systemd/system/traffic-scanner.service
    sed -i "s|User=pi|User=$ACTUAL_USER|g" /etc/systemd/system/traffic-scanner.service
    sed -i "s|Group=pi|Group=$ACTUAL_USER|g" /etc/systemd/system/traffic-scanner.service
    
    # Reload systemd
    systemctl daemon-reload
    
    echo "✅ Service file installed"
else
    echo "⚠️  Service file not found at $SERVICE_FILE"
    echo "Creating service file..."
    
    cat > /etc/systemd/system/traffic-scanner.service <<EOF
[Unit]
Description=Pedestrian Traffic Monitoring - Bluetooth Scanner
After=network.target bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=$ACTUAL_USER
Group=$ACTUAL_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/python3 $INSTALL_DIR/data_collection/bluetooth_scanner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=traffic-scanner

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    echo "✅ Service file created"
fi

# Step 6: Enable auto-start
echo "🚀 Step 6: Enabling auto-start..."
systemctl enable traffic-scanner.service

echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "The scanner will now start automatically on boot!"
echo ""
echo "📋 Useful commands:"
echo ""
echo "  Start scanner now:"
echo "    sudo systemctl start traffic-scanner"
echo ""
echo "  Stop scanner:"
echo "    sudo systemctl stop traffic-scanner"
echo ""
echo "  Check status:"
echo "    sudo systemctl status traffic-scanner"
echo ""
echo "  View logs:"
echo "    sudo journalctl -u traffic-scanner -f"
echo ""
echo "  Disable auto-start:"
echo "    sudo systemctl disable traffic-scanner"
echo ""
echo "  Re-enable auto-start:"
echo "    sudo systemctl enable traffic-scanner"
echo ""
echo "⚠️  IMPORTANT:"
echo "  - Make sure USB drive is plugged in before booting!"
echo "  - Logs will be in: $INSTALL_DIR/logs/"
echo "  - Data will be saved to: /media/usb/pedestrian-monitoring/"
echo ""
echo "🔄 To start the scanner now without rebooting:"
echo "    sudo systemctl start traffic-scanner"
echo ""
