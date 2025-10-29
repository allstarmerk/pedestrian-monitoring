# USB Storage Setup Guide

## 📦 Automatic USB Data Storage

The system now automatically detects and saves data to USB drives! This makes data collection much easier - just plug in a USB drive and go.

---

## 🔌 How It Works

### Automatic Detection
1. **Plug in USB drive** to Raspberry Pi
2. **System auto-detects** USB mount point
3. **Data saves automatically** to USB drive
4. **Local backup** maintained on SD card

### Storage Priority
```
USB Drive (if available)
     └─ /media/username/USB_NAME/pedestrian-monitoring/data/

⚠️ IMPORTANT: No SD card backup!
   - Keep USB plugged in during collection
   - Use reliable USB drive
   - Monitor USB space regularly
```

---

## 🚀 Quick Setup

### Step 1: Format USB Drive (One-time)

**On Linux/Mac:**
```bash
# Find USB device
lsblk

# Format as FAT32 (for universal compatibility)
sudo mkfs.vfat -n TRAFFIC_DATA /dev/sdb1

# Or format as ext4 (for Linux only, better performance)
sudo mkfs.ext4 -L TRAFFIC_DATA /dev/sdb1
```

**On Windows:**
- Right-click USB drive → Format
- File System: FAT32 or exFAT
- Volume Label: TRAFFIC_DATA
- Quick Format: ✓

### Step 2: Mount USB on Raspberry Pi

**Automatic mounting (recommended):**
```bash
# Edit fstab for auto-mount
sudo nano /etc/fstab

# Add this line (replace UUID with your USB UUID from blkid):
UUID=XXXX-XXXX  /media/usb  vfat  defaults,nofail,uid=pi,gid=pi  0  0

# Create mount point
sudo mkdir -p /media/usb

# Mount it
sudo mount -a
```

**Manual mounting:**
```bash
# Create mount point
sudo mkdir -p /media/usb

# Mount USB
sudo mount /dev/sda1 /media/usb

# Make writable
sudo chmod 777 /media/usb
```

### Step 3: Test USB Detection

```bash
cd pedestrian-monitoring
python3 utils/usb_storage_manager.py
```

**Expected output:**
```
============================================================
USB Storage Manager Test
============================================================

Checking for USB drives...
✓ USB Drive Found!
  Mount point: /media/usb
  Free space: 7450 MB
  Total space: 7628 MB
  Used: 2.3%

Creating README on USB...

Storage paths:
  Raw data: /media/usb/pedestrian-monitoring/data/raw
  Processed: /media/usb/pedestrian-monitoring/data/processed
  Models: /media/usb/pedestrian-monitoring/data/models
============================================================
```

---

## 📁 USB Data Structure

When you plug in the USB, the system creates:

```
USB_DRIVE/
└── pedestrian-monitoring/
    ├── README.txt                    # Explanation of data
    └── data/
        ├── raw/                      # Raw Bluetooth scans
        │   ├── scan_20251029.jsonl
        │   ├── scan_20251030.jsonl
        │   └── ...
        ├── processed/                # Aggregated data
        │   └── processed_traffic_data.csv
        └── models/                   # Trained ML models
            ├── gmm_clustering_model.pkl
            └── xgboost_forecaster.pkl
```

---

## 🔄 Data Collection Workflow

### With USB Drive:

```
1. Plug USB into Raspberry Pi
   ↓
2. Start scanner: python3 data_collection/bluetooth_scanner.py
   ↓
3. System detects USB automatically
   ↓
4. Data saves directly to: /media/usb/pedestrian-monitoring/data/raw/
   ↓
5. Keep USB plugged in while collecting!
   ↓
6. Stop scanner when done (Ctrl+C)
   ↓
7. Wait 5 seconds for writes to complete
   ↓
8. Unplug USB safely
   ↓
9. Plug USB into your computer
   ↓
10. Process data on your development machine
```

### Without USB Drive:

```
1. Start scanner without USB
   ↓
2. ERROR: No USB detected, scanner will warn you
   ↓
3. Plug in USB before starting
   ↓
4. Or use minimal local storage (not recommended for long-term)
```

⚠️ **Important**: Always keep USB plugged in during data collection to avoid data loss!

---

## 💾 Recommended USB Drives

### Size Recommendations:
- **Minimum**: 8 GB (holds ~2-3 months of data)
- **Recommended**: 16-32 GB (6+ months)
- **Optimal**: 64 GB (1+ years)

### Data Size Estimates:
- **Raw scans**: ~1 MB per day
- **Processed data**: ~500 KB per day
- **Models**: ~5-10 MB total
- **Total**: ~30-50 MB per month

### Suggested Brands:
- SanDisk Ultra (reliable, affordable)
- Samsung BAR Plus (durable, fast)
- Kingston DataTraveler (budget-friendly)

---

## 🛠️ Advanced Configuration

### Change USB Mount Point

Edit `utils/usb_storage_manager.py`:

```python
# Look for specific mount point
def get_preferred_usb(self):
    # Add your preferred path
    preferred_paths = [
        '/media/usb',        # Your custom mount
        '/media/pi/USB',     # Default Pi
        '/mnt/usb'          # Alternative
    ]
    
    for path in preferred_paths:
        if os.path.ismount(path):
            return path
```

### Label Your USB Drive

```bash
# FAT32
sudo fatlabel /dev/sda1 TRAFFIC_DATA

# ext4
sudo e2label /dev/sda1 TRAFFIC_DATA
```

### Auto-Mount on Boot

```bash
# Edit /etc/fstab
sudo nano /etc/fstab

# Add line:
LABEL=TRAFFIC_DATA  /media/usb  vfat  defaults,nofail,x-systemd.device-timeout=1  0  0
```

---

## 🔍 Monitoring USB Storage

### Check USB Status During Collection:

```bash
# View logs
tail -f logs/bluetooth_scanner.log

# Look for:
# "USB storage available: 7450 MB free"
# "Saving raw data to USB: /media/usb/..."
```

### Check Space:

```bash
df -h /media/usb
```

### Sync Data from SD to USB:

```python
from utils.usb_storage_manager import USBStorageManager

manager = USBStorageManager()
synced = manager.sync_directory_to_usb('data/raw', 'raw')
print(f"Synced {synced} files")
```

---

## ⚠️ Troubleshooting

### USB Not Detected

**Problem**: "No USB drive found"

**Solutions**:
```bash
# Check if USB is recognized
lsblk

# Check mount points
mount | grep usb

# Check permissions
ls -la /media/

# Manual mount
sudo mount /dev/sda1 /media/usb
```

### Permission Denied

**Problem**: "Error saving file: Permission denied"

**Solution**:
```bash
# Make USB writable
sudo chmod 777 /media/usb

# Or change ownership
sudo chown -R pi:pi /media/usb
```

### USB Fills Up

**Problem**: "No space left on device"

**Solutions**:
1. **Use larger USB drive**
2. **Archive old data**:
   ```bash
   # Compress old data
   cd /media/usb/pedestrian-monitoring/data/raw
   tar -czf archive_2025_Q1.tar.gz scan_202501*.jsonl
   rm scan_202501*.jsonl
   ```
3. **Automatic cleanup** (add to config.yaml):
   ```yaml
   storage:
     raw_retention_days: 30  # Auto-delete after 30 days
   ```

### Data Loss Prevention

**Problem**: What if USB gets disconnected?

**Solution**:
- ⚠️ **Important**: Keep USB connected during collection
- Use reliable USB drive with good connection
- Consider taping USB in place for field deployment
- Check scanner logs regularly to verify USB still detected
- If USB disconnects:
  - Scanner will log error messages
  - Data from that scan may be lost
  - Restart scanner after reconnecting USB

**Best Practice**: Test your USB drive reliability before deployment!

---

## 📤 Retrieving Data

### Method 1: Unplug USB (Easiest)
1. Stop scanner: `Ctrl+C`
2. Wait 5 seconds for writes to finish
3. Unplug USB drive
4. Plug into your computer
5. Open `/pedestrian-monitoring/` folder

### Method 2: Copy via Network
```bash
# On your computer
scp -r pi@raspberrypi.local:/media/usb/pedestrian-monitoring/data ./
```

### Method 3: Access Remotely
```bash
# Mount USB over network (if Pi on network)
# On your computer:
sshfs pi@raspberrypi.local:/media/usb ~/usb_drive
```

---

## 🔄 Processing USB Data

### On Your Computer:

1. **Plug in USB** from Raspberry Pi

2. **Copy data** to your working directory:
   ```bash
   cp -r /path/to/usb/pedestrian-monitoring/data .
   ```

3. **Process data**:
   ```bash
   python3 data_collection/data_processor.py
   ```

4. **Train models**:
   ```bash
   python3 ml_models/model_trainer.py
   ```

5. **View results**:
   ```bash
   python3 api/server.py
   cd dashboard && npm start
   ```

---

## 🎯 Best Practices

### ✅ Do:
- Use USB 3.0 drive for faster writes
- Keep USB plugged in during entire collection period
- Use high-quality, reliable USB drives
- Check USB space before starting long collections
- Label your USB drives clearly
- Test USB reliability before field deployment
- Monitor scanner logs to verify USB still working

### ❌ Don't:
- Unplug USB while scanner is running
- Use cheap/unreliable USB drives
- Let USB fill to 100% capacity
- Forget to check USB space regularly
- Deploy without testing USB first

### 💡 Pro Tips:
- Keep a spare USB for emergencies
- Use USB extension cable for easy access
- Secure USB with tape to prevent accidental disconnection
- Set calendar reminders to check USB space

---

## 📊 Monitoring Dashboard

Add USB status to your monitoring:

```python
# In your monitoring script
from utils.usb_storage_manager import USBStorageManager

manager = USBStorageManager()
info = manager.get_usb_info()

if info['available']:
    print(f"USB: {info['free_space_mb']:.0f} MB free")
    if info['free_space_mb'] < 100:
        print("⚠️  WARNING: USB space low!")
else:
    print("⚠️  USB not available - using local storage")
```

---

## 🎉 Benefits of USB Storage

✅ **Easy Data Retrieval** - Just unplug and go  
✅ **No Network Needed** - Fully offline operation  
✅ **Large Capacity** - Store months of data  
✅ **Portable** - Take data anywhere  
✅ **Backup** - Local SD card backup maintained  
✅ **Simple** - Plug and play, automatic  
✅ **Reliable** - Solid state, no moving parts  

---

## 📞 Quick Reference

```bash
# Check USB
python3 utils/usb_storage_manager.py

# Start scanner with USB
python3 data_collection/bluetooth_scanner.py

# Check USB space
df -h /media/usb

# View saved data
ls -lh /media/usb/pedestrian-monitoring/data/raw/

# Sync SD to USB
python3 -c "from utils.usb_storage_manager import USBStorageManager; \
    m = USBStorageManager(); \
    m.sync_directory_to_usb('data/raw', 'raw')"
```

---

**With USB storage, your pedestrian monitoring system is now even more portable and easier to deploy!** 🎉

Just plug in a USB drive, start the scanner, and collect data anywhere - no network required!
