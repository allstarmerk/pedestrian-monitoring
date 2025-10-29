#!/usr/bin/env python3
"""
Bluetooth Scanner for Pedestrian Traffic Monitoring
Scans for nearby Bluetooth devices and logs anonymized data
"""

import bluetooth
import time
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
import yaml
import signal

# Add utils directory to path for USB manager
sys.path.append(str(Path(__file__).parent.parent))

try:
    from utils.usb_storage_manager import USBStorageManager
    USB_MANAGER_AVAILABLE = True
except ImportError:
    USB_MANAGER_AVAILABLE = False
    print("Warning: USB storage manager not available, using local storage only")

try:
    from bluepy.btle import Scanner, DefaultDelegate
    BLUEPY_AVAILABLE = True
except ImportError:
    BLUEPY_AVAILABLE = False
    print("Warning: bluepy not available, using pybluez only")


class BluetoothScanner:
    """Main class for Bluetooth device scanning and logging"""
    
    def __init__(self, config_path="data_collection/config.yaml"):
        """Initialize scanner with configuration"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.running = False
        self.scan_count = 0
        self.device_history = {}  # Track device first/last seen times
        self.salt = self._generate_salt()
        
        # Initialize USB storage manager if available
        if USB_MANAGER_AVAILABLE:
            self.usb_manager = USBStorageManager(config_path)
            usb_info = self.usb_manager.get_usb_info()
            if usb_info['available']:
                self.logger.info(f"USB storage available: {usb_info['free_space_mb']:.0f} MB free")
                self.usb_manager.create_readme_on_usb()
            else:
                self.logger.info("No USB drive found - using local storage")
        else:
            self.usb_manager = None
            self.logger.info("USB manager not available - using local storage")
        
        # Get data directory (USB or local)
        if self.usb_manager:
            self.data_dir = self.usb_manager.get_storage_path('raw')
        else:
            self.data_dir = Path(self.config['storage']['raw_data_dir'])
            self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Data will be saved to: {self.data_dir}")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Bluetooth scanner initialized")
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def setup_logging(self):
        """Configure logging"""
        log_dir = Path(self.config['storage']['logs_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'bluetooth_scanner.log'
        
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format=self.config['logging']['format'],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _generate_salt(self):
        """Generate cryptographic salt for hashing"""
        import secrets
        return secrets.token_hex(32)
    
    def _hash_mac_address(self, mac_address):
        """
        Hash MAC address for privacy
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            Hashed MAC address string
        """
        if self.config['privacy']['store_raw_mac']:
            self.logger.warning("Raw MAC storage is enabled - privacy risk!")
        
        # Combine MAC with salt and hash
        combined = f"{mac_address}{self.salt}"
        hash_obj = hashlib.sha256(combined.encode())
        return hash_obj.hexdigest()
    
    def scan_bluetooth_classic(self):
        """
        Scan for Bluetooth Classic devices
        
        Returns:
            List of detected devices with metadata
        """
        devices = []
        try:
            nearby_devices = bluetooth.discover_devices(
                duration=self.config['bluetooth']['scan_duration'],
                lookup_names=False,
                flush_cache=True
            )
            
            for addr in nearby_devices:
                # Get RSSI (signal strength) if available
                try:
                    rssi = bluetooth.lookup_rssi(addr)
                except:
                    rssi = None
                
                # Only include if RSSI meets threshold
                if rssi is None or rssi >= self.config['bluetooth']['rssi_threshold']:
                    devices.append({
                        'mac_hash': self._hash_mac_address(addr),
                        'rssi': rssi,
                        'protocol': 'classic'
                    })
        
        except Exception as e:
            self.logger.error(f"Error scanning Bluetooth Classic: {e}")
        
        return devices
    
    def scan_bluetooth_le(self):
        """
        Scan for Bluetooth Low Energy (BLE) devices
        
        Returns:
            List of detected BLE devices with metadata
        """
        devices = []
        
        if not BLUEPY_AVAILABLE:
            self.logger.debug("BLE scanning not available (bluepy not installed)")
            return devices
        
        try:
            scanner = Scanner()
            ble_devices = scanner.scan(self.config['bluetooth']['scan_duration'])
            
            for dev in ble_devices:
                # Check RSSI threshold
                if dev.rssi >= self.config['bluetooth']['rssi_threshold']:
                    devices.append({
                        'mac_hash': self._hash_mac_address(dev.addr),
                        'rssi': dev.rssi,
                        'protocol': 'ble'
                    })
        
        except Exception as e:
            self.logger.error(f"Error scanning BLE: {e}")
        
        return devices
    
    def scan_all_devices(self):
        """
        Scan for both Classic and BLE devices
        
        Returns:
            Combined list of all detected devices
        """
        self.logger.info("Starting scan...")
        
        # Scan both protocols
        classic_devices = self.scan_bluetooth_classic()
        ble_devices = self.scan_bluetooth_le()
        
        # Combine and deduplicate
        all_devices = classic_devices + ble_devices
        unique_devices = {}
        
        for device in all_devices:
            mac_hash = device['mac_hash']
            if mac_hash not in unique_devices:
                unique_devices[mac_hash] = device
            elif device['rssi'] is not None:
                # Keep device with stronger signal
                if unique_devices[mac_hash]['rssi'] is None or \
                   device['rssi'] > unique_devices[mac_hash]['rssi']:
                    unique_devices[mac_hash] = device
        
        devices_list = list(unique_devices.values())
        self.logger.info(f"Scan complete: {len(devices_list)} unique devices detected")
        
        return devices_list
    
    def filter_stationary_devices(self, devices, current_time):
        """
        Filter out stationary devices (present for > threshold time)
        
        Args:
            devices: List of detected devices
            current_time: Current timestamp
            
        Returns:
            Filtered list of transient devices only
        """
        threshold = self.config['bluetooth']['stationary_threshold']
        transient_devices = []
        
        for device in devices:
            mac_hash = device['mac_hash']
            
            # Update device history
            if mac_hash not in self.device_history:
                # First time seeing this device
                self.device_history[mac_hash] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'is_stationary': False
                }
                transient_devices.append(device)
            else:
                # Update last seen time
                history = self.device_history[mac_hash]
                history['last_seen'] = current_time
                
                # Check if device has been present too long
                duration = (current_time - history['first_seen']).total_seconds()
                
                if duration > threshold:
                    if not history['is_stationary']:
                        self.logger.info(f"Device {mac_hash[:8]}... marked as stationary")
                        history['is_stationary'] = True
                else:
                    # Still transient
                    transient_devices.append(device)
        
        # Clean up old device history (not seen in last timeout period)
        timeout = self.config['bluetooth']['device_timeout']
        to_remove = []
        
        for mac_hash, history in self.device_history.items():
            if (current_time - history['last_seen']).total_seconds() > timeout:
                to_remove.append(mac_hash)
        
        for mac_hash in to_remove:
            del self.device_history[mac_hash]
        
        self.logger.debug(f"Filtered: {len(transient_devices)}/{len(devices)} transient devices")
        return transient_devices
    
    def save_scan_data(self, devices, timestamp):
        """
        Save scan data to JSON file (only if devices detected or logging enabled)
        
        Args:
            devices: List of detected devices
            timestamp: Scan timestamp
        """
        # Check if we should skip empty scans
        log_empty = self.config['bluetooth'].get('log_empty_scans', True)
        
        if not log_empty and len(devices) == 0:
            self.logger.debug("Skipping empty scan (no devices detected)")
            return
        
        # Create filename based on date
        filename = f"scan_{timestamp.strftime('%Y%m%d')}.jsonl"
        filepath = self.data_dir / filename
        
        # Prepare data record
        record = {
            'timestamp': timestamp.isoformat(),
            'scan_id': self.scan_count,
            'device_count': len(devices),
            'devices': devices
        }
        
        # Append to JSONL file (one JSON object per line)
        with open(filepath, 'a') as f:
            f.write(json.dumps(record) + '\n')
        
        if len(devices) > 0:
            self.logger.debug(f"Data saved to {filepath} - {len(devices)} devices")
        else:
            self.logger.debug(f"Empty scan saved to {filepath}")
    
    def run(self):
        """Main scanning loop"""
        self.running = True
        log_empty = self.config['bluetooth'].get('log_empty_scans', True)
        
        self.logger.info("Starting Bluetooth scanning loop")
        self.logger.info(f"Scan interval: {self.config['bluetooth']['scan_interval']}s")
        self.logger.info(f"Scan duration: {self.config['bluetooth']['scan_duration']}s")
        
        if not log_empty:
            self.logger.info("⚡ RAPID MODE: Only logging scans with detected devices")
            self.logger.info("   This saves space while never missing anyone!")
        
        while self.running:
            try:
                # Perform scan
                scan_time = datetime.now()
                devices = self.scan_all_devices()
                
                # Filter stationary devices
                transient_devices = self.filter_stationary_devices(devices, scan_time)
                
                # Save data (may skip if empty and log_empty_scans=false)
                self.save_scan_data(transient_devices, scan_time)
                
                # Update counter
                self.scan_count += 1
                
                # Log statistics (show all scans for awareness)
                if len(transient_devices) > 0:
                    self.logger.info(
                        f"✓ Scan #{self.scan_count}: {len(transient_devices)} transient devices detected & logged"
                    )
                else:
                    # Only show empty scans in debug mode to reduce log clutter
                    self.logger.debug(
                        f"○ Scan #{self.scan_count}: No devices (not logged)"
                    )
                
                # Wait for next scan
                time.sleep(self.config['bluetooth']['scan_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in scan loop: {e}", exc_info=True)
                time.sleep(10)  # Wait before retrying
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)
    
    def stop(self):
        """Stop the scanner"""
        self.logger.info("Stopping scanner...")
        self.running = False


def main():
    """Main entry point"""
    print("=" * 60)
    print("Pedestrian Traffic Monitoring - Bluetooth Scanner")
    print("=" * 60)
    print()
    
    # Initialize scanner
    scanner = BluetoothScanner()
    
    print("Scanner initialized. Starting data collection...")
    print("Press Ctrl+C to stop")
    print()
    
    # Run scanner
    try:
        scanner.run()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        scanner.stop()
    except Exception as e:
        print(f"\nFatal error: {e}")
        scanner.logger.error("Fatal error", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
