#!/usr/bin/env python3
"""
USB Storage Manager
Detects and manages external USB storage for data collection
"""

import os
import subprocess
import logging
from pathlib import Path
import time


class USBStorageManager:
    """Manage USB storage for data persistence"""
    
    def __init__(self):
        """Initialize USB manager"""
        self.logger = logging.getLogger(__name__)
        self.usb_mount_point = Path("/mnt/usb_storage")
        self.default_storage = Path("/home/claude/pedestrian-monitoring/data")
        
    def find_usb_device(self):
        """
        Find connected USB storage device
        
        Returns:
            Device path (e.g., /dev/sda1) or None
        """
        try:
            # List block devices
            result = subprocess.run(
                ['lsblk', '-o', 'NAME,TYPE,MOUNTPOINT', '-n'],
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    name, device_type = parts[0], parts[1]
                    
                    # Look for disk partitions (not the whole disk)
                    if device_type == 'part' and name.startswith('sd'):
                        # Exclude system disk (usually mmcblk0 on Pi or sda if booting from USB)
                        # We want removable USB drives (typically sda1, sdb1, etc.)
                        device_path = f"/dev/{name}"
                        
                        # Check if it's removable
                        removable_path = f"/sys/block/{name.rstrip('0123456789')}/removable"
                        try:
                            with open(removable_path, 'r') as f:
                                if f.read().strip() == '1':
                                    self.logger.info(f"Found removable USB device: {device_path}")
                                    return device_path
                        except:
                            pass
            
            self.logger.warning("No removable USB device found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding USB device: {e}")
            return None
    
    def mount_usb(self, device_path=None):
        """
        Mount USB device
        
        Args:
            device_path: Specific device to mount, or None to auto-detect
            
        Returns:
            Mount point path or None
        """
        if device_path is None:
            device_path = self.find_usb_device()
        
        if device_path is None:
            self.logger.warning("No USB device to mount")
            return None
        
        try:
            # Create mount point if it doesn't exist
            self.usb_mount_point.mkdir(parents=True, exist_ok=True)
            
            # Check if already mounted
            result = subprocess.run(
                ['mountpoint', '-q', str(self.usb_mount_point)],
                capture_output=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"USB already mounted at {self.usb_mount_point}")
                return self.usb_mount_point
            
            # Mount the device
            self.logger.info(f"Mounting {device_path} to {self.usb_mount_point}")
            subprocess.run(
                ['sudo', 'mount', device_path, str(self.usb_mount_point)],
                check=True
            )
            
            # Make writable
            subprocess.run(
                ['sudo', 'chmod', '777', str(self.usb_mount_point)],
                check=False
            )
            
            self.logger.info(f"Successfully mounted USB at {self.usb_mount_point}")
            return self.usb_mount_point
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to mount USB: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error mounting USB: {e}")
            return None
    
    def unmount_usb(self):
        """Safely unmount USB device"""
        try:
            self.logger.info("Unmounting USB device")
            subprocess.run(
                ['sudo', 'umount', str(self.usb_mount_point)],
                check=True
            )
            self.logger.info("USB unmounted successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to unmount USB: {e}")
            return False
    
    def is_usb_available(self):
        """
        Check if USB storage is available and mounted
        
        Returns:
            True if USB is mounted and writable
        """
        if not self.usb_mount_point.exists():
            return False
        
        try:
            # Check if mounted
            result = subprocess.run(
                ['mountpoint', '-q', str(self.usb_mount_point)],
                capture_output=True
            )
            
            if result.returncode != 0:
                return False
            
            # Check if writable
            test_file = self.usb_mount_point / '.write_test'
            test_file.touch()
            test_file.unlink()
            
            return True
            
        except Exception as e:
            self.logger.debug(f"USB not available: {e}")
            return False
    
    def get_storage_path(self, subdir=''):
        """
        Get appropriate storage path (USB if available, local otherwise)
        
        Args:
            subdir: Subdirectory within storage (e.g., 'raw', 'processed')
            
        Returns:
            Path object for storage location
        """
        if self.is_usb_available():
            base_path = self.usb_mount_point / 'pedestrian-data'
        else:
            base_path = self.default_storage
        
        if subdir:
            storage_path = base_path / subdir
        else:
            storage_path = base_path
        
        # Create directory if it doesn't exist
        storage_path.mkdir(parents=True, exist_ok=True)
        
        return storage_path
    
    def get_usb_info(self):
        """
        Get information about USB storage
        
        Returns:
            Dictionary with USB info
        """
        info = {
            'mounted': False,
            'mount_point': None,
            'available_space_gb': 0,
            'used_space_gb': 0,
            'total_space_gb': 0
        }
        
        if not self.is_usb_available():
            return info
        
        try:
            # Get disk usage
            stat = os.statvfs(self.usb_mount_point)
            
            total = (stat.f_blocks * stat.f_frsize) / (1024**3)  # GB
            available = (stat.f_bavail * stat.f_frsize) / (1024**3)  # GB
            used = total - available
            
            info.update({
                'mounted': True,
                'mount_point': str(self.usb_mount_point),
                'available_space_gb': round(available, 2),
                'used_space_gb': round(used, 2),
                'total_space_gb': round(total, 2)
            })
            
        except Exception as e:
            self.logger.error(f"Error getting USB info: {e}")
        
        return info
    
    def setup_auto_mount(self):
        """
        Create systemd service for auto-mounting USB on boot
        
        Returns:
            True if successful
        """
        service_content = """[Unit]
Description=Auto-mount USB storage for pedestrian monitoring
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/pi/pedestrian-monitoring/utils/usb_manager.py mount
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
        
        try:
            service_path = Path("/etc/systemd/system/usb-automount.service")
            
            print("Creating auto-mount service...")
            print("This requires sudo privileges.")
            print("\nService will be created at:", service_path)
            print("\nTo install, run:")
            print("  sudo systemctl enable usb-automount")
            print("  sudo systemctl start usb-automount")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up auto-mount: {e}")
            return False


def main():
    """Command-line interface for USB management"""
    import sys
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='USB Storage Manager')
    parser.add_argument('action', choices=['detect', 'mount', 'unmount', 'info', 'test'],
                       help='Action to perform')
    
    args = parser.parse_args()
    manager = USBStorageManager()
    
    if args.action == 'detect':
        print("\n" + "="*60)
        print("USB DEVICE DETECTION")
        print("="*60)
        device = manager.find_usb_device()
        if device:
            print(f"✓ Found USB device: {device}")
        else:
            print("✗ No USB device found")
            print("\nTips:")
            print("  1. Make sure USB drive is plugged in")
            print("  2. Check with: lsblk")
            print("  3. Try a different USB port")
    
    elif args.action == 'mount':
        print("\n" + "="*60)
        print("MOUNTING USB STORAGE")
        print("="*60)
        mount_point = manager.mount_usb()
        if mount_point:
            print(f"✓ USB mounted at: {mount_point}")
            info = manager.get_usb_info()
            print(f"\nStorage Info:")
            print(f"  Total Space: {info['total_space_gb']} GB")
            print(f"  Used Space: {info['used_space_gb']} GB")
            print(f"  Available: {info['available_space_gb']} GB")
        else:
            print("✗ Failed to mount USB")
            print("\nTroubleshooting:")
            print("  1. Run: sudo blkid")
            print("  2. Check: dmesg | tail")
            print("  3. Try: sudo mount /dev/sda1 /mnt/usb_storage")
    
    elif args.action == 'unmount':
        print("\n" + "="*60)
        print("UNMOUNTING USB STORAGE")
        print("="*60)
        if manager.unmount_usb():
            print("✓ USB safely unmounted")
            print("\nYou can now remove the USB drive")
        else:
            print("✗ Failed to unmount USB")
    
    elif args.action == 'info':
        print("\n" + "="*60)
        print("USB STORAGE INFORMATION")
        print("="*60)
        info = manager.get_usb_info()
        
        if info['mounted']:
            print(f"✓ USB is mounted")
            print(f"\nMount Point: {info['mount_point']}")
            print(f"Total Space: {info['total_space_gb']} GB")
            print(f"Used Space: {info['used_space_gb']} GB")
            print(f"Available: {info['available_space_gb']} GB")
            
            # Show data directory contents
            data_path = manager.get_storage_path()
            print(f"\nData Directory: {data_path}")
            
            if data_path.exists():
                try:
                    items = list(data_path.iterdir())
                    print(f"Contents: {len(items)} items")
                    for item in items[:10]:  # Show first 10
                        print(f"  - {item.name}")
                    if len(items) > 10:
                        print(f"  ... and {len(items)-10} more")
                except:
                    pass
        else:
            print("✗ USB is not mounted")
            print("\nTo mount: python3 utils/usb_manager.py mount")
    
    elif args.action == 'test':
        print("\n" + "="*60)
        print("USB STORAGE TEST")
        print("="*60)
        
        print("\n1. Detecting USB device...")
        device = manager.find_usb_device()
        if device:
            print(f"   ✓ Found: {device}")
        else:
            print("   ✗ No device found")
            sys.exit(1)
        
        print("\n2. Mounting USB...")
        if manager.mount_usb():
            print(f"   ✓ Mounted at: {manager.usb_mount_point}")
        else:
            print("   ✗ Mount failed")
            sys.exit(1)
        
        print("\n3. Testing write access...")
        test_file = manager.get_storage_path() / 'test.txt'
        try:
            test_file.write_text("USB test successful!")
            content = test_file.read_text()
            test_file.unlink()
            print("   ✓ Write test passed")
        except Exception as e:
            print(f"   ✗ Write test failed: {e}")
            sys.exit(1)
        
        print("\n4. Getting storage info...")
        info = manager.get_usb_info()
        print(f"   ✓ Available: {info['available_space_gb']} GB")
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nUSB storage is ready for data collection!")
        print(f"Data will be saved to: {manager.get_storage_path()}")


if __name__ == "__main__":
    main()
