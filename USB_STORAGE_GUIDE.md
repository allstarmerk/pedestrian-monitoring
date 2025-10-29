# USB Storage Setup Guide

## Why Use USB Storage? 🔌

Using an external USB drive for data storage provides:
- **Easy data retrieval** - Just unplug and take to your computer
- **More storage** - Not limited by SD card size
- **Data safety** - Separate from system drive
- **Quick backup** - Copy USB contents for backup
- **Field deployment** - Swap USB drives without touching the Pi

---

## Quick Setup (3 Steps)

### 1. Prepare USB Drive

**Format the USB drive (on your computer):**

**On Linux/Mac:**
```bash
# Find your USB device (e.g., /dev/sdb1)
lsblk

# Format as ext4 (recommended) or FAT32
sudo mkfs.ext4 /dev/sdb1  # Replace with your device

# Or for Windows compatibility:
sudo mkfs.vfat -F 32 /dev/sdb1
```

**On Windows:**
- Right-click USB drive → Format
- Choose FAT32 or exFAT
- Quick format

**Recommended:**
- Size: 16GB or larger (32GB ideal)
- Format: ext4 (Linux) or FAT32 (cross-platform)
- Label: "TRAFFIC-DATA" (optional, helps identify)

### 2. Connect to Raspberry Pi

1. Plug USB drive into any USB port on Pi
2. Wait 5 seconds for detection
3. Test detection:
   ```bash
   python3 utils/usb_manager.py detect
   ```

### 3. Mount and Test

```bash
# Mount the USB drive
python3 utils/usb_manager.py mount

# Test write access
python3 utils/usb_manager.py test

# Check storage info
python3 utils/usb_manager.py info
```

**That's it!** Your system will now automatically use USB storage.

---

## How It Works

### Automatic USB Detection

The system includes `usb_manager.py` that:
1. **Detects USB drives** automatically on startup
2. **Mounts** them to `/mnt/usb_storage`
3. **Falls back** to SD card if no USB present
4. **Creates directories** for raw/processed data

### Storage Priority

```
1. USB drive (if available) → /mnt/usb_storage/pedestrian-data/
2. SD card (fallback)      → /home/pi/pedestrian-monitoring/data/
```

### Data Organization on USB

```
/mnt/usb_storage/
└── pedestrian-data/
    ├── raw/                    # Bluetooth scan logs
    │   ├── scan_20251029.jsonl
    │   ├── scan_20251030.jsonl
    │   └── scan_20251031.jsonl
    ├── processed/              # Cleaned datasets
    │   ├── processed_traffic_data.csv
    │   └── processed_traffic_data_metadata.json
    └── models/                 # Trained ML models (optional)
        ├── gmm_clustering_model.pkl
        └── xgboost_forecaster.pkl
```

---

## Usage Examples

### Check USB Status

```bash
python3 utils/usb_manager.py info
```

**Output:**
```
USB STORAGE INFORMATION
============================================================
✓ USB is mounted

Mount Point: /mnt/usb_storage
Total Space: 29.5 GB
Used Space: 1.2 GB
Available: 28.3 GB

Data Directory: /mnt/usb_storage/pedestrian-data
Contents: 45 items
  - raw/
  - processed/
  - scan_20251029.jsonl
  ...
```

### Safely Remove USB

**Before unplugging:**
```bash
# Stop the scanner first
sudo systemctl stop traffic-scanner

# Unmount USB
python3 utils/usb_manager.py unmount

# Now safe to remove USB drive
```

### Read Data on Your Computer

1. Unplug USB from Pi
2. Plug into your computer
3. Navigate to `pedestrian-data/` folder
4. Copy files or analyze directly

---

## Auto-Mount on Boot

For production deployment, set up automatic USB mounting:

### 1. Create Systemd Service

```bash
sudo nano /etc/systemd/system/usb-automount.service
```

**Add this content:**
```ini
[Unit]
Description=Auto-mount USB storage for pedestrian monitoring
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/pi/pedestrian-monitoring/utils/usb_manager.py mount
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

### 2. Enable Auto-Mount

```bash
sudo systemctl enable usb-automount
sudo systemctl start usb-automount
```

### 3. Test Reboot

```bash
sudo reboot

# After reboot, check:
python3 utils/usb_manager.py info
```

---

## Troubleshooting

### USB Not Detected

**Check if USB is visible:**
```bash
lsblk
```

**Look for device like sda1, sdb1:**
```
NAME        MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
sda           8:0    1 29.5G  0 disk
└─sda1        8:1    1 29.5G  0 part
```

**Manually check:**
```bash
sudo blkid  # Shows all block devices
dmesg | tail  # Shows recent kernel messages
```

### Permission Errors

**Grant permissions:**
```bash
sudo chmod 777 /mnt/usb_storage
```

**Or mount with permissions:**
```bash
sudo mount -o uid=pi,gid=pi /dev/sda1 /mnt/usb_storage
```

### USB Not Mounting

**Try manual mount:**
```bash
sudo mkdir -p /mnt/usb_storage
sudo mount /dev/sda1 /mnt/usb_storage
```

**If ext4 format:**
```bash
sudo mount -t ext4 /dev/sda1 /mnt/usb_storage
```

**If FAT32 format:**
```bash
sudo mount -t vfat /dev/sda1 /mnt/usb_storage
```

### "Read-only file system"

**Remount as read-write:**
```bash
sudo mount -o remount,rw /mnt/usb_storage
```

### USB Full

**Check space:**
```bash
df -h /mnt/usb_storage
```

**Clean old data:**
```bash
# Delete files older than 30 days
find /mnt/usb_storage/pedestrian-data/raw -name "*.jsonl" -mtime +30 -delete
```

---

## Storage Requirements

### Expected Data Sizes

| Duration | Raw Data | Processed | Total |
|----------|----------|-----------|-------|
| 1 day    | ~1 MB    | ~100 KB   | ~1 MB |
| 1 week   | ~7 MB    | ~700 KB   | ~8 MB |
| 1 month  | ~30 MB   | ~3 MB     | ~33 MB |
| 1 year   | ~365 MB  | ~36 MB    | ~400 MB |

**Recommendation:** 16GB USB drive = ~40 years of data!

### Data Retention

**Automatic cleanup (optional):**

Add to crontab:
```bash
crontab -e
```

Add line:
```bash
# Delete raw data older than 90 days, keep processed
0 2 * * 0 find /mnt/usb_storage/pedestrian-data/raw -name "*.jsonl" -mtime +90 -delete
```

---

## Advanced: Multiple USB Drives

### Swap Drives for Backup

**Day 1-15:** USB Drive A collects data
**Day 15:** 
1. Stop scanner
2. Unmount USB A
3. Remove USB A (take to office)
4. Insert USB B
5. Mount USB B
6. Restart scanner

**Both drives maintain independent datasets!**

### RAID Setup (Optional)

For critical deployments, use 2 USB drives in mirror:
```bash
# This is advanced - see RAID documentation
mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sda1 /dev/sdb1
```

---

## Best Practices

### ✅ Do's

- ✅ Use quality USB drive (SanDisk, Samsung, Kingston)
- ✅ Format before first use
- ✅ Label the USB drive clearly
- ✅ Always unmount before removing
- ✅ Keep a backup USB drive
- ✅ Test USB regularly with: `python3 utils/usb_manager.py test`
- ✅ Monitor storage space weekly

### ❌ Don'ts

- ❌ Don't remove USB while system is writing
- ❌ Don't use old/cheap USB drives (may fail)
- ❌ Don't format USB while mounted
- ❌ Don't ignore "disk full" warnings
- ❌ Don't rely on single USB without backups

---

## Integration with Existing System

The USB storage is **already integrated** in:

### Bluetooth Scanner
```python
# Automatically uses USB if available
scanner = BluetoothScanner()
# Data saved to USB or SD card (automatic)
```

### Data Processor
```python
# Automatically reads from USB if available
processor = DataProcessor()
# Looks for data on USB first, then SD card
```

### No Code Changes Needed!

The system automatically:
1. Detects USB on startup
2. Mounts to `/mnt/usb_storage`
3. Uses USB for all data operations
4. Falls back to SD card if no USB

---

## Quick Reference Commands

```bash
# Detect USB
python3 utils/usb_manager.py detect

# Mount USB
python3 utils/usb_manager.py mount

# Check status
python3 utils/usb_manager.py info

# Test USB
python3 utils/usb_manager.py test

# Safely unmount
python3 utils/usb_manager.py unmount

# Check what's on USB
ls -lh /mnt/usb_storage/pedestrian-data/

# See storage usage
du -sh /mnt/usb_storage/pedestrian-data/*
```

---

## FAQ

**Q: Does the Pi need to be powered off to insert USB?**
A: No! You can hot-plug USB drives. Just run `python3 utils/usb_manager.py mount` after inserting.

**Q: What happens if USB fills up?**
A: System will log warnings and fall back to SD card. Monitor with `python3 utils/usb_manager.py info`.

**Q: Can I use multiple USB drives?**
A: Yes! Swap them as needed. Each maintains independent data.

**Q: What format is best?**
A: ext4 for Linux-only, FAT32 for cross-platform compatibility.

**Q: Will data be lost if USB is removed?**
A: Recent scans might be in buffer. Always unmount first: `python3 utils/usb_manager.py unmount`

**Q: Can I access USB data while Pi is running?**
A: Yes! The data files are just regular files in `/mnt/usb_storage/pedestrian-data/`

**Q: Does USB drain more battery?**
A: Minimal impact. USB draw is ~100mA, negligible with solar power.

---

## Summary

USB storage provides:
- ✅ **Easy data retrieval** (unplug and go)
- ✅ **Automatic detection** (plug and play)
- ✅ **Safe fallback** (SD card if no USB)
- ✅ **No code changes** (works out of box)
- ✅ **Field swappable** (multiple drives)

**Just plug in a USB drive and the system handles the rest!** 🎉

---

**Updated**: October 2025  
**Version**: 1.1 (USB Support Added)
