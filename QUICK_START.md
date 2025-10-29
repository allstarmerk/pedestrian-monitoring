# Quick Start Guide
## Get Your Pedestrian Monitoring System Running in 15 Minutes

---

## Prerequisites

- **Raspberry Pi 4** (4GB RAM) with Raspberry Pi OS installed
- **Python 3.9+** installed
- **Node.js 16+** and npm installed (for dashboard)
- **Bluetooth enabled** on your system
- **Internet connection** (for initial setup)

---

## Step 1: Hardware Setup (5 minutes)

### Basic Setup (Testing)
1. Insert SD card with Raspberry Pi OS into Pi
2. Connect Bluetooth adapter if using external one
3. Power on the Raspberry Pi
4. Connect via SSH or use a monitor/keyboard

### Production Setup (Optional)
1. Mount Pi inside weatherproof enclosure
2. Connect solar panel to power bank
3. Connect power bank to Pi via USB-C
4. Position enclosure at metro station location
5. Ensure solar panel faces south (northern hemisphere)

---

## Step 2: Software Installation (5 minutes)

### Clone Repository
```bash
git clone <repository-url>
cd pedestrian-monitoring
```

### Install Python Dependencies
```bash
# Update system
sudo apt-get update

# Install system packages
sudo apt-get install -y python3-pip bluetooth bluez libbluetooth-dev

# Install Python packages
pip3 install -r requirements.txt

# Grant Bluetooth permissions
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
```

### Install Dashboard Dependencies
```bash
cd dashboard
npm install
cd ..
```

---

## Step 3: Data Collection (Start immediately, runs continuously)

### Optional: Setup USB Storage (Recommended)

For easy data retrieval in the field:

```bash
# 1. Plug in USB drive to Raspberry Pi

# 2. Mount the USB
python3 utils/usb_manager.py mount

# 3. Verify it's working
python3 utils/usb_manager.py test
```

**Why USB?** Just unplug the USB drive and take it to your computer - no network needed!

See **[USB_STORAGE_GUIDE.md](USB_STORAGE_GUIDE.md)** for details.

### Start Bluetooth Scanner
```bash
python3 data_collection/bluetooth_scanner.py
```

**What happens:**
- Scans for Bluetooth devices every 60 seconds
- Anonymizes MAC addresses immediately
- Logs detections to `data/raw/scan_YYYYMMDD.jsonl`
- Filters stationary devices automatically

**Let this run for at least 48 hours** to collect meaningful data. The longer it runs, the better your models will be.

**Tips:**
- Run in screen/tmux session to keep it running when disconnected
- Check logs: `tail -f logs/bluetooth_scanner.log`
- Monitor: You should see scan counts incrementing

---

## Step 4: Process Data (After 2-7 days of collection)

Once you have collected at least 2 days of data:

```bash
python3 data_collection/data_processor.py
```

**What happens:**
- Loads raw scan logs
- Expands device detections
- Aggregates into 4-hour windows
- Creates time-based features
- Generates lag and rolling features
- Saves to `data/processed/processed_traffic_data.csv`

**Expected output:**
```
Processing complete - Statistics:
  Total records: 336
  Date range: 2025-10-01 to 2025-10-15
  Days covered: 14
  Average devices: 12.34
```

---

## Step 5: Train Models (5 minutes)

```bash
python3 ml_models/model_trainer.py
```

**What happens:**
- Trains GMM clustering model (Quiet/Moderate/Busy patterns)
- Trains XGBoost forecasting model (4-hour predictions)
- Optionally trains LSTM model
- Saves models to `data/models/`
- Creates visualization plots

**Expected output:**
```
CLUSTERING RESULTS:
  Silhouette Score: 0.623
  Quiet Traffic: 112 samples (mean=5.23)
  Moderate Traffic: 168 samples (mean=12.45)
  Busy Traffic: 56 samples (mean=24.67)

XGBOOST FORECASTING RESULTS:
  RMSE: 2.34
  R² Score: 0.782
  MAPE: 14.2%
```

**What if models perform poorly?**
- Collect more data (minimum 2 weeks recommended)
- Check if there are clear patterns in your data
- Review visualization plots in `data/models/`

---

## Step 6: Start API Server

```bash
python3 api/server.py
```

**What happens:**
- Loads trained models
- Starts Flask API on port 5000
- Generates predictions every 60 seconds
- Serves data to dashboard

**Verify it's working:**
```bash
# In another terminal
curl http://localhost:5000/api/health
curl http://localhost:5000/api/current
```

**Keep this running** - the dashboard needs it!

---

## Step 7: Launch Dashboard

In a new terminal:

```bash
cd dashboard
npm start
```

**Access dashboard:**
Open your browser to: **http://localhost:3000**

**What you'll see:**
- Current traffic level
- 4-hour prediction
- Congestion status (Quiet/Moderate/Busy)
- Historical traffic chart
- Hourly and weekly patterns
- Real-time updates every 60 seconds

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI                             │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Bluetooth   │ -> │     Data     │ -> │   Machine    │ │
│  │   Scanner    │    │  Processor   │    │   Learning   │ │
│  │              │    │              │    │   Models     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         |                    |                    |         │
│         v                    v                    v         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Raw Data -> Processed Data               │  │
│  │              -> Trained Models -> Predictions         │  │
│  └──────────────────────────────────────────────────────┘  │
│                              |                              │
│                              v                              │
│                    ┌──────────────────┐                     │
│                    │   Flask API      │                     │
│                    │   (Port 5000)    │                     │
│                    └──────────────────┘                     │
└──────────────────────────────┬──────────────────────────────┘
                               |
                               | HTTP/JSON
                               v
                    ┌──────────────────┐
                    │  React Dashboard │
                    │  (Port 3000)     │
                    └──────────────────┘
                               |
                               v
                        ┌─────────────┐
                        │   Browser   │
                        └─────────────┘
```

---

## Running in Production

### Auto-Start on Boot

Create systemd service files:

**1. Scanner Service** (`/etc/systemd/system/traffic-scanner.service`):
```ini
[Unit]
Description=Traffic Scanner
After=network.target bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pedestrian-monitoring
ExecStart=/usr/bin/python3 data_collection/bluetooth_scanner.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. API Service** (`/etc/systemd/system/traffic-api.service`):
```ini
[Unit]
Description=Traffic API Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pedestrian-monitoring
ExecStart=/usr/bin/python3 api/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable services:**
```bash
sudo systemctl enable traffic-scanner
sudo systemctl enable traffic-api
sudo systemctl start traffic-scanner
sudo systemctl start traffic-api
```

### Periodic Model Retraining

Add to crontab (`crontab -e`):
```bash
# Process data daily at 2 AM
0 2 * * * cd /home/pi/pedestrian-monitoring && python3 data_collection/data_processor.py

# Retrain models weekly on Sunday at 3 AM
0 3 * * 0 cd /home/pi/pedestrian-monitoring && python3 ml_models/model_trainer.py
```

---

## Troubleshooting

### "No devices detected"
- Check Bluetooth is enabled: `sudo systemctl status bluetooth`
- Verify permissions: `sudo setcap -v 'cap_net_raw,cap_net_admin+eip' $(which python3)`
- Test manually: `sudo hcitool scan`
- Try increasing scan duration in config

### "API returns 503 errors"
- Check if models exist: `ls data/models/`
- Train models if missing: `python3 ml_models/model_trainer.py`
- Check API logs: `tail -f logs/api_server.log`

### "Dashboard not loading data"
- Verify API is running: `curl http://localhost:5000/api/health`
- Check browser console for CORS errors
- Verify CORS origins in config match your dashboard URL

### "Models perform poorly"
- Collect more data (minimum 2 weeks)
- Check for clear traffic patterns in data
- Review visualization plots
- Ensure data collection running continuously

### "Permission denied errors"
- Run with sudo (not recommended for production)
- Or grant capabilities: `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which python3)`

---

## Monitoring

### Check System Health
```bash
# Scanner status
tail -f logs/bluetooth_scanner.log

# API status
tail -f logs/api_server.log

# Data collection stats
ls -lh data/raw/

# Model files
ls -lh data/models/
```

### View Real-Time Stats
```bash
# Current predictions
curl http://localhost:5000/api/current | json_pp

# Historical data
curl http://localhost:5000/api/history?hours=24 | json_pp

# Statistics
curl http://localhost:5000/api/statistics | json_pp
```

---

## What's Next?

1. **Let it run**: Continuous operation improves model accuracy
2. **Review patterns**: Check dashboard regularly for insights
3. **Optimize placement**: Adjust sensor position for better coverage
4. **Expand features**: Add weather data, holiday calendar
5. **Deploy multiple**: Set up at multiple metro stations
6. **Share results**: Use insights for urban planning

---

## Getting Help

- Check logs in `logs/` directory
- Review configuration in `data_collection/config.yaml`
- Read full technical report: `TECHNICAL_REPORT.md`
- Check README for detailed documentation

---

## Summary Checklist

- [ ] Hardware connected and powered
- [ ] Software installed
- [ ] Bluetooth scanner running
- [ ] Data collected (minimum 48 hours)
- [ ] Data processed successfully
- [ ] Models trained with good metrics
- [ ] API server running
- [ ] Dashboard accessible and updating
- [ ] System monitoring configured
- [ ] Auto-start enabled (production)
--
