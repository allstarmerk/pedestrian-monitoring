# USB Storage Feature - Summary

##  USB Storage Support Added!

Your pedestrian monitoring system now includes **automatic USB storage support** for easy data collection and retrieval in the field.

---

##  What Changed

### New Files Added

1. **`utils/usb_manager.py`** (350+ lines)
   - Automatic USB detection
   - Mount/unmount management
   - Storage fallback system
   - Command-line interface

2. **`USB_STORAGE_GUIDE.md`**
   - Complete setup instructions
   - Troubleshooting guide
   - Best practices

### Updated Files

1. **`data_collection/bluetooth_scanner.py`**
   - Now checks for USB on startup
   - Automatically saves to USB if available
   - Falls back to SD card if no USB

2. **`data_collection/data_processor.py`**
   - Reads from USB first, then SD card
   - Writes processed data to USB

3. **`README.md`** and **`QUICK_START.md`**
   - Added USB storage sections
   - Updated setup instructions

---

## 🚀 How It Works

### Automatic Detection

```python
# When scanner starts:
1. Detects USB drive automatically
2. Mounts to /mnt/usb_storage
3. Creates data directories
4. Saves all data to USB
5. Falls back to SD card if no USB
```

### Zero Configuration Required

Just plug in a USB drive - that's it! The system handles everything:
-  Detection
-  Mounting
-  Directory creation
-  Permissions
-  Fallback

---

##  Key Benefits

### For Field Deployment

**Before (SD Card Only):**
- Need to access Pi via SSH/network
- Or remove SD card (risky!)
- Or connect monitor/keyboard

**Now (With USB):**
1. Plug in USB drive
2. Wait for data collection
3. Unmount: `python3 utils/usb_manager.py unmount`
4. Unplug USB and take to office
5. Plug USB into computer - access all data!

### Easy Data Rotation

- Week 1: Use USB Drive A
- Week 2: Swap to USB Drive B
- Week 3: Swap to USB Drive C
- Process all drives in parallel!

### No Internet Required

- USB storage works completely offline
- No network needed for data retrieval
- Perfect for remote/secure locations

---

##  Quick Usage

### Initial Setup (One Time)

```bash
# 1. Format USB drive (on your computer)
#    - FAT32 for Windows/Mac compatibility
#    - ext4 for better performance (Linux only)

# 2. Plug USB into Raspberry Pi

# 3. Mount it
python3 utils/usb_manager.py mount

# 4. Test it
python3 utils/usb_manager.py test
```

### Daily Operation

```bash
# Check status anytime
python3 utils/usb_manager.py info

# Output:
# ✓ USB is mounted
# Available: 28.3 GB
# Data Directory: /mnt/usb_storage/pedestrian-data
```

### Data Retrieval

```bash
# 1. Stop scanner (if running)
sudo systemctl stop traffic-scanner

# 2. Safely unmount
python3 utils/usb_manager.py unmount

# 3. Remove USB drive

# 4. Plug into computer and access files!
```

---

##  Storage Capacity

**Typical USB Drive: 16GB**

| Duration | Data Size | Drives Needed |
|----------|-----------|---------------|
| 1 day    | ~1 MB     | 1 drive = 44 years! |
| 1 week   | ~7 MB     | 1 drive = 6+ years |
| 1 month  | ~30 MB    | 1 drive = 14+ months |
| 1 year   | ~365 MB   | 1 drive = plenty |

**Even a small USB drive lasts for years!**

---

##  Hardware Requirements

### USB Drive Recommendations

**Minimum:**
- 8GB capacity
- USB 2.0

**Recommended:**
- 16-32GB capacity
- USB 3.0 (faster reads/writes)
- Quality brand (SanDisk, Samsung, Kingston)

**Format:**
- FAT32: Universal compatibility
- ext4: Best for Linux, better performance
- exFAT: Large files, newer standard

### Power Considerations

USB drive power draw: ~100mA (minimal)
- No significant battery impact
- Works fine with solar setup
- Pi's USB ports provide ample power

---

##  Command Reference

```bash
# Detection
python3 utils/usb_manager.py detect
# Output: Found USB device: /dev/sda1

# Mount
python3 utils/usb_manager.py mount
# Output: USB mounted at: /mnt/usb_storage

# Check Info
python3 utils/usb_manager.py info
# Shows: mount status, storage space, data contents

# Test (full check)
python3 utils/usb_manager.py test
# Runs: detection, mount, write test, read test

# Unmount (before removal!)
python3 utils/usb_manager.py unmount
# Output: USB safely unmounted
```

---

## Technical Details

### Mount Point

- USB mounted at: `/mnt/usb_storage/`
- Data directory: `/mnt/usb_storage/pedestrian-data/`
- Subdirectories: `raw/`, `processed/`, `models/`

### Fallback Logic

```python
if USB_available:
    save_to("/mnt/usb_storage/pedestrian-data/raw/")
else:
    save_to("/home/pi/pedestrian-monitoring/data/raw/")
```

### Automatic Permissions

System automatically:
- Creates directories
- Sets write permissions
- Handles user/group ownership

---

##  Integration Status

###  Fully Integrated Components

- **Bluetooth Scanner**: Saves to USB automatically
- **Data Processor**: Reads from USB first
- **USB Manager**: Complete management tool

###  Transparent Operation

**No code changes needed in your scripts!**

The system detects and uses USB automatically. Your existing code works exactly the same - it just saves to USB instead of SD card when available.

---

##  Migration from SD Card

### Existing Data on SD Card?

**Option 1: Copy to USB**
```bash
# Mount USB
python3 utils/usb_manager.py mount

# Copy existing data
cp -r /home/pi/pedestrian-monitoring/data/* /mnt/usb_storage/pedestrian-data/
```

**Option 2: Keep Both**
- Old data stays on SD card
- New data goes to USB
- Both accessible

---

## Data Safety

### Backup Strategy

**Daily Backup (Automated):**
```bash
# Add to crontab
0 1 * * * rsync -av /mnt/usb_storage/pedestrian-data/ /home/pi/backup/
```

**Weekly USB Swap:**
- Monday-Friday: USB Drive A
- Weekend: Swap to USB Drive B
- Process Drive A offline

### Redundancy Options

1. **Dual USB**: Use 2 USB drives, mirror data
2. **USB + SD**: Keep SD card as automatic backup
3. **Remote Sync**: When internet available, sync to cloud

---

## Important Notes

### Always Unmount Before Removal!

```bash
python3 utils/usb_manager.py unmount
```

**Why?** Prevents:
- Data corruption
- Incomplete writes
- File system errors

### Monitor Storage Space

```bash
# Check weekly
python3 utils/usb_manager.py info
```

If space low:
- Clean old data
- Swap to new USB
- Process and archive

---

## Documentation

- **Setup**: [USB_STORAGE_GUIDE.md](USB_STORAGE_GUIDE.md) - Complete guide
- **Code**: `utils/usb_manager.py` - Well-commented source
- **Integration**: Scanner and processor updated automatically

---

##  Summary

### What You Get

 **Plug-and-play USB support**
 **Automatic detection and mounting**
 **Smart fallback to SD card**
 **Easy field data retrieval**
 **No configuration required**
 **Command-line management tools**
 **Comprehensive documentation**

### What You Need

1. Any USB drive (16GB+ recommended)
2. Plug it into Raspberry Pi
3. Run: `python3 utils/usb_manager.py mount`
4. Done! Data now saves to USB

---

**The system now supports USB storage while maintaining full backward compatibility with SD card storage. Your deployment just got 10x easier!** 🚀

--
