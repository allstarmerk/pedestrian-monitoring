# ⚠️ USB Storage - Important Requirements

## Critical Information

### 🔴 Keep USB Connected!

**The system does NOT backup to SD card** to preserve space for the operating system.

This means:
- ✅ USB must stay plugged in during data collection
- ❌ Don't unplug USB while scanner is running
- ❌ Data will be lost if USB disconnects during collection

---

## 📋 Pre-Deployment Checklist

Before deploying your Raspberry Pi for data collection:

### 1. USB Drive Selection
- [ ] Use reliable brand (SanDisk, Samsung, Kingston)
- [ ] Minimum 8GB capacity
- [ ] USB 3.0 for better performance
- [ ] Test the USB drive first!

### 2. USB Testing (CRITICAL!)
```bash
# Test your USB drive before field deployment!

# 1. Plug USB into Pi
# 2. Test detection
python3 utils/usb_storage_manager.py

# 3. Run scanner for 1 hour test
python3 data_collection/bluetooth_scanner.py
# Let run for 1 hour, then check data was saved

# 4. Verify data files created
ls -lh /media/usb/pedestrian-monitoring/data/raw/

# 5. Check no errors in logs
tail -50 logs/bluetooth_scanner.log
```

### 3. Physical Security
- [ ] Secure USB drive so it won't get accidentally unplugged
- [ ] Consider using USB extension cable for strain relief
- [ ] Tape USB in place if needed
- [ ] Mark USB drive with "DO NOT REMOVE" label

### 4. Capacity Planning
- [ ] Calculate storage needed: ~1 MB/day × collection days
- [ ] Add 50% safety margin
- [ ] Set calendar reminder to check space weekly

---

## 🛡️ Reliability Recommendations

### USB Drive Quality Tiers

**Recommended (Best):**
- Samsung BAR Plus (metal construction, very durable)
- SanDisk Ultra Fit (small, stays secure)
- Kingston DataTraveler Elite G2

**Acceptable (Good):**
- SanDisk Cruzer
- Kingston DataTraveler
- PNY Attaché

**Avoid:**
- Generic/no-name brands
- Very old USB drives (>5 years)
- USB drives that get hot
- USB drives with loose connections

### Physical Deployment Tips

```
Good Setup:
┌─────────────────┐
│  Raspberry Pi   │
│                 │
│  [USB Port]─────┼──[Extension Cable]──[USB Drive secured with tape]
│                 │
└─────────────────┘

Why:
- Extension cable provides strain relief
- USB drive can't be accidentally pulled
- Easy to label and secure
```

---

## 🚨 What Happens If USB Fails?

### Scenario 1: USB Disconnects During Collection
- **Result**: Data loss from that scan onward
- **Recovery**: 
  1. Check scanner logs to see when disconnect happened
  2. Reconnect USB
  3. Restart scanner
  4. Lost data cannot be recovered

### Scenario 2: USB Fills Up
- **Result**: Scanner will log errors, data stops saving
- **Recovery**:
  1. Stop scanner
  2. Replace with larger USB
  3. Restart scanner

### Scenario 3: USB Drive Fails Completely
- **Result**: All data on that USB is lost
- **Recovery**: 
  - No recovery possible without backup
  - This is why testing beforehand is critical!

---

## 💡 Best Practices for Reliable Operation

### Before Deployment
1. **Format USB properly**: FAT32 or exFAT
2. **Test for 24 hours**: Run scanner and verify data saves correctly
3. **Check USB health**: No errors in logs
4. **Secure physically**: Tape, extension cable, labels

### During Deployment
1. **Check logs weekly**: SSH in or view locally
2. **Monitor space**: Ensure USB isn't filling up
3. **Verify still writing**: Check file timestamps

### After Collection
1. **Stop scanner properly**: Ctrl+C and wait 5 seconds
2. **Safely eject**: Better safe than sorry
3. **Backup immediately**: Copy USB contents to computer
4. **Archive data**: Keep original USB as backup

---

## 🔧 Monitoring Commands

### Check if USB is still detected:
```bash
df -h | grep usb
# Should show your USB mount point
```

### Check recent scans saved:
```bash
ls -lt /media/usb/pedestrian-monitoring/data/raw/ | head -5
# Shows most recent files with timestamps
```

### Check scanner is still writing:
```bash
tail -f logs/bluetooth_scanner.log
# Should see new scan entries every 60 seconds
```

### Check USB space:
```bash
df -h /media/usb
# Watch the "Use%" column
```

---

## 📊 Space Calculation

**Data Size Per Day**: ~1 MB
- 60 scans/hour × 24 hours = 1,440 scans/day
- Average ~700 bytes per scan = ~1 MB/day

**Example Calculations:**

| Collection Period | Data Size | Recommended USB |
|-------------------|-----------|-----------------|
| 1 week | ~7 MB | 8 GB |
| 1 month | ~30 MB | 8 GB |
| 3 months | ~90 MB | 8 GB |
| 6 months | ~180 MB | 8 GB |
| 1 year | ~365 MB | 8 GB or larger |

**Rule of Thumb**: 8GB USB = ~8,000 MB = ~8,000 days of data (20+ years!)

Space is rarely the issue - reliability is what matters!

---

## ⚠️ Emergency Procedures

### USB Disconnected Accidentally

1. **Don't panic** - OS on SD card is fine
2. **Check what was lost**:
   ```bash
   # Check last saved file
   ls -lt /media/usb/pedestrian-monitoring/data/raw/
   
   # Check logs for disconnect time
   grep -i "error\|usb\|fail" logs/bluetooth_scanner.log | tail -20
   ```
3. **Reconnect USB**
4. **Restart scanner**
5. **Document the gap** in your records

### SD Card Nearly Full

If you see "No space left on device":

```bash
# Check what's using space
df -h
du -sh /*

# Clean up system logs if needed
sudo journalctl --vacuum-time=7d

# The scanner itself uses minimal SD space
# Check for other applications
```

### USB Not Being Detected

```bash
# 1. Check if USB is physically recognized
lsblk

# 2. Check dmesg for USB events
dmesg | grep -i usb | tail -20

# 3. Try manual mount
sudo mount /dev/sda1 /media/usb

# 4. Check file system
sudo fsck /dev/sda1
```

---

## ✅ Final Checklist Before Deployment

- [ ] USB drive tested for 24+ hours
- [ ] No errors in scanner logs
- [ ] USB physically secured
- [ ] Capacity verified (space available)
- [ ] Extension cable used (optional but recommended)
- [ ] Label added: "DO NOT REMOVE"
- [ ] Backup plan documented
- [ ] Calendar reminders set for monitoring
- [ ] Emergency contact information on device
- [ ] Documentation printed and included with device

---

## 📞 Quick Troubleshooting

| Problem | Quick Fix |
|---------|-----------|
| USB not detected | Check `lsblk` and `df -h` |
| Scanner stops saving | Check USB space and connection |
| Files not appearing | Wait 60 seconds for next scan |
| USB slow | Use USB 3.0 port (blue) |
| Concerned about reliability | Run 24-hour test first |

---

## 🎯 Remember

**The USB drive is your data lifeline!**

- No SD card backup means USB reliability is critical
- Test before deploying
- Secure it properly
- Monitor regularly
- Keep spare USB drives handy

**But don't worry!** With a quality USB drive and proper setup, your system will run reliably for months without issues. 🎉

---

**Pro Tip**: Buy 2-3 USB drives. Use one for collection, keep others as spares. Swap them if you need to retrieve data without stopping collection.
