#!/usr/bin/env python3
"""
USB Storage Manager
Automatically detects USB drives and saves data to them
"""

import os
import subprocess
import shutil
from pathlib import Path
import logging
import time
import yaml


class USBStorageManager:
    """Manage data storage to USB drives"""
    
    def __init__(self, config_path="data_collection/config.yaml"):
        """Initialize USB storage manager"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(__name__)
        self.usb_mount_point = None
    
    def find_usb_drives(self):
        """
        Find all mounted USB drives
        
        Returns:
            List of USB mount points
        """
        usb_drives = []
        
        try:
            # Check common USB mount points
            media_dirs = ['/media', '/mnt']
            
            for media_dir in media_dirs:
                if os.path.exists(media_dir):
                    # List all subdirectories
                    for root, dirs, files in os.walk(media_dir):
                        for dir_name in dirs:
                            mount_point = os.path.join(root, dir_name)
                            # Check if it's actually mounted
                            if os.path.ismount(mount_point):
                                usb_drives.append(mount_point)
                        break  # Don't recurse deeper
            
            # Alternative: Parse /proc/mounts
            if not usb_drives:
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            device, mount_point = parts[0], parts[1]
                            # Look for USB devices
                            if '/dev/sd' in device and mount_point.startswith('/media'):
                                usb_drives.append(mount_point)
        
        except Exception as e:
            self.logger.error(f"Error finding USB drives: {e}")
        
        return usb_drives
    
    def get_preferred_usb(self):
        """
        Get the preferred USB drive (first available with enough space)
        
        Returns:
            USB mount point or None
        """
        usb_drives = self.find_usb_drives()
        
        if not usb_drives:
            self.logger.debug("No USB drives found")
            return None
        
        # Check each drive for sufficient space (at least 100MB)
        for usb in usb_drives:
            try:
                stat = os.statvfs(usb)
                free_space = stat.f_bavail * stat.f_frsize
                free_mb = free_space / (1024 * 1024)
                
                if free_mb > 100:  # At least 100MB free
                    self.logger.info(f"Using USB drive: {usb} ({free_mb:.0f} MB free)")
                    return usb
            except Exception as e:
                self.logger.warning(f"Error checking USB {usb}: {e}")
        
        self.logger.warning("No USB drives with sufficient space found")
        return None
    
    def get_storage_path(self, data_type='raw'):
        """
        Get storage path for data
        
        Args:
            data_type: 'raw', 'processed', or 'models'
            
        Returns:
            Path object for storage location
        """
        # Try USB first
        usb = self.get_preferred_usb()
        
        if usb:
            # Create project directory on USB
            usb_project_dir = Path(usb) / 'pedestrian-monitoring'
            usb_data_dir = usb_project_dir / 'data' / data_type
            
            try:
                usb_data_dir.mkdir(parents=True, exist_ok=True)
                self.usb_mount_point = usb
                self.logger.info(f"Saving {data_type} data to USB: {usb_data_dir}")
                return usb_data_dir
            except Exception as e:
                self.logger.error(f"Error creating USB directory: {e}")
        
        # Fallback to local storage
        local_dir = Path(self.config['storage'][f'{data_type}_data_dir'])
        local_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Saving {data_type} data to local storage: {local_dir}")
        return local_dir
    
    def save_to_usb_with_fallback(self, source_file, data_type='raw'):
        """
        Save file to USB (no local backup to preserve SD card space)
        
        Args:
            source_file: Path to file to save
            data_type: Type of data (raw, processed, models)
            
        Returns:
            True if saved successfully
        """
        source_file = Path(source_file)
        
        if not source_file.exists():
            self.logger.error(f"Source file not found: {source_file}")
            return False
        
        # Get USB storage path
        usb_dir = self.get_storage_path(data_type)
        usb_file = usb_dir / source_file.name
        
        try:
            # Copy to USB/storage
            shutil.copy2(source_file, usb_file)
            self.logger.debug(f"Saved to: {usb_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving file: {e}")
            self.logger.warning("USB save failed - file not backed up (SD card space preservation)")
            return False
    
    def sync_directory_to_usb(self, source_dir, data_type='raw'):
        """
        Sync entire directory to USB
        
        Args:
            source_dir: Directory to sync
            data_type: Type of data
            
        Returns:
            Number of files synced
        """
        source_dir = Path(source_dir)
        
        if not source_dir.exists():
            self.logger.error(f"Source directory not found: {source_dir}")
            return 0
        
        usb_dir = self.get_storage_path(data_type)
        synced_count = 0
        
        for source_file in source_dir.glob('*'):
            if source_file.is_file():
                usb_file = usb_dir / source_file.name
                
                # Only copy if file doesn't exist or is newer
                if not usb_file.exists() or source_file.stat().st_mtime > usb_file.stat().st_mtime:
                    try:
                        shutil.copy2(source_file, usb_file)
                        synced_count += 1
                        self.logger.debug(f"Synced: {source_file.name}")
                    except Exception as e:
                        self.logger.error(f"Error syncing {source_file.name}: {e}")
        
        self.logger.info(f"Synced {synced_count} files to USB")
        return synced_count
    
    def get_usb_info(self):
        """
        Get information about USB storage
        
        Returns:
            Dictionary with USB info
        """
        usb = self.get_preferred_usb()
        
        if not usb:
            return {
                'available': False,
                'mount_point': None,
                'free_space_mb': 0,
                'total_space_mb': 0
            }
        
        try:
            stat = os.statvfs(usb)
            total_space = stat.f_blocks * stat.f_frsize
            free_space = stat.f_bavail * stat.f_frsize
            
            return {
                'available': True,
                'mount_point': usb,
                'free_space_mb': free_space / (1024 * 1024),
                'total_space_mb': total_space / (1024 * 1024),
                'used_percent': ((total_space - free_space) / total_space) * 100
            }
        except Exception as e:
            self.logger.error(f"Error getting USB info: {e}")
            return {'available': False}
    
    def create_readme_on_usb(self):
        """Create a README file on USB explaining the data"""
        usb = self.get_preferred_usb()
        
        if not usb:
            return
        
        readme_path = Path(usb) / 'pedestrian-monitoring' / 'README.txt'
        
        try:
            with open(readme_path, 'w') as f:
                f.write("=" * 70 + "\n")
                f.write("PEDESTRIAN TRAFFIC MONITORING DATA\n")
                f.write("=" * 70 + "\n\n")
                f.write("This USB drive contains anonymized pedestrian traffic data.\n\n")
                f.write("DATA STRUCTURE:\n")
                f.write("  data/raw/      - Raw Bluetooth scan logs (JSONL format)\n")
                f.write("  data/processed/ - Processed and aggregated data (CSV)\n")
                f.write("  data/models/   - Trained machine learning models\n\n")
                f.write("PRIVACY NOTICE:\n")
                f.write("  - All MAC addresses are hashed (SHA-256)\n")
                f.write("  - No personal identifiable information stored\n")
                f.write("  - Stationary devices filtered out\n")
                f.write("  - Data aggregated into time windows\n\n")
                f.write("TO PROCESS THIS DATA:\n")
                f.write("  1. Copy this folder to your computer\n")
                f.write("  2. Run: python3 data_collection/data_processor.py\n")
                f.write("  3. Run: python3 ml_models/model_trainer.py\n")
                f.write("  4. Start API and dashboard to view results\n\n")
                f.write(f"Data collected on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n")
            
            self.logger.info(f"Created README on USB: {readme_path}")
        except Exception as e:
            self.logger.error(f"Error creating README: {e}")


def test_usb_storage():
    """Test USB storage functionality"""
    print("=" * 60)
    print("USB Storage Manager Test")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    manager = USBStorageManager()
    
    # Get USB info
    print("\nChecking for USB drives...")
    usb_info = manager.get_usb_info()
    
    if usb_info['available']:
        print(f"✓ USB Drive Found!")
        print(f"  Mount point: {usb_info['mount_point']}")
        print(f"  Free space: {usb_info['free_space_mb']:.0f} MB")
        print(f"  Total space: {usb_info['total_space_mb']:.0f} MB")
        print(f"  Used: {usb_info['used_percent']:.1f}%")
        
        # Create README
        print("\nCreating README on USB...")
        manager.create_readme_on_usb()
        
        # Show storage paths
        print("\nStorage paths:")
        print(f"  Raw data: {manager.get_storage_path('raw')}")
        print(f"  Processed: {manager.get_storage_path('processed')}")
        print(f"  Models: {manager.get_storage_path('models')}")
    else:
        print("✗ No USB drive found")
        print("  Data will be saved to local storage as fallback")
        print(f"  Local backup: {manager.local_backup}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_usb_storage()
