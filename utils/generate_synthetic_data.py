#!/usr/bin/env python3
"""
Synthetic Data Generator for Testing
Generates realistic pedestrian traffic patterns without real Bluetooth hardware
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import hashlib
from pathlib import Path
import yaml


class SyntheticDataGenerator:
    """Generate synthetic traffic data for testing"""
    
    def __init__(self, config_path="data_collection/config.yaml"):
        """Initialize generator"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.data_dir = Path(self.config['storage']['raw_data_dir'])
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_pattern(self, hour):
        """
        Generate realistic hourly traffic pattern
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Base traffic level for that hour
        """
        # Typical metro station pattern
        if 0 <= hour < 5:
            return 2  # Very quiet, late night
        elif 5 <= hour < 7:
            return 5  # Early morning, building up
        elif 7 <= hour < 9:
            return 25  # Morning rush hour
        elif 9 <= hour < 11:
            return 12  # Mid-morning
        elif 11 <= hour < 13:
            return 15  # Lunch time
        elif 13 <= hour < 16:
            return 10  # Afternoon
        elif 16 <= hour < 19:
            return 28  # Evening rush hour
        elif 19 <= hour < 22:
            return 12  # Evening
        else:
            return 5  # Late evening
    
    def generate_weekly_pattern(self, day_of_week):
        """
        Generate weekly multiplier
        
        Args:
            day_of_week: 0=Monday, 6=Sunday
            
        Returns:
            Multiplier for that day
        """
        if day_of_week < 5:  # Weekday
            return 1.0
        elif day_of_week == 5:  # Saturday
            return 0.7
        else:  # Sunday
            return 0.5
    
    def generate_device_count(self, timestamp):
        """
        Generate realistic device count for given time
        
        Args:
            timestamp: DateTime object
            
        Returns:
            Number of devices to simulate
        """
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Base pattern
        base = self.generate_daily_pattern(hour)
        weekly_mult = self.generate_weekly_pattern(day_of_week)
        
        # Add some randomness
        noise = np.random.normal(0, 0.2)
        
        # Final count
        count = int(base * weekly_mult * (1 + noise))
        count = max(0, count)  # No negative devices
        
        return count
    
    def generate_mac_hash(self, device_id):
        """
        Generate fake anonymized MAC hash
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            SHA-256 hash string
        """
        mac = f"fake_device_{device_id}"
        return hashlib.sha256(mac.encode()).hexdigest()
    
    def generate_scan(self, timestamp, scan_id):
        """
        Generate a single scan record
        
        Args:
            timestamp: DateTime for this scan
            scan_id: Scan identifier
            
        Returns:
            Dictionary with scan data
        """
        device_count = self.generate_device_count(timestamp)
        
        devices = []
        for i in range(device_count):
            # Generate unique device ID based on time and index
            device_id = f"{timestamp.timestamp()}_{i}"
            
            devices.append({
                'mac_hash': self.generate_mac_hash(device_id),
                'rssi': np.random.randint(-80, -40),  # Signal strength
                'protocol': np.random.choice(['classic', 'ble'])
            })
        
        return {
            'timestamp': timestamp.isoformat(),
            'scan_id': scan_id,
            'device_count': len(devices),
            'devices': devices
        }
    
    def generate_dataset(self, start_date, days=14):
        """
        Generate complete synthetic dataset
        
        Args:
            start_date: Starting date (string or datetime)
            days: Number of days to generate
        """
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        
        print(f"Generating {days} days of synthetic data...")
        print(f"Start date: {start_date.date()}")
        
        scan_interval = self.config['bluetooth']['scan_interval']
        current_time = start_date
        end_time = start_date + timedelta(days=days)
        scan_id = 0
        
        # Group scans by date for file organization
        scans_by_date = {}
        
        while current_time < end_time:
            # Generate scan
            scan = self.generate_scan(current_time, scan_id)
            
            # Group by date
            date_key = current_time.date()
            if date_key not in scans_by_date:
                scans_by_date[date_key] = []
            scans_by_date[date_key].append(scan)
            
            # Move to next scan time
            current_time += timedelta(seconds=scan_interval)
            scan_id += 1
            
            # Progress indicator
            if scan_id % 100 == 0:
                progress = (current_time - start_date).total_seconds() / (end_time - start_date).total_seconds()
                print(f"Progress: {progress*100:.1f}% ({scan_id} scans)")
        
        # Save to files
        print("\nSaving data files...")
        for date, scans in scans_by_date.items():
            filename = f"scan_{date.strftime('%Y%m%d')}.jsonl"
            filepath = self.data_dir / filename
            
            with open(filepath, 'w') as f:
                for scan in scans:
                    f.write(json.dumps(scan) + '\n')
            
            print(f"  Saved {len(scans)} scans to {filename}")
        
        print(f"\n✓ Generated {scan_id} total scans")
        print(f"✓ Saved to {self.data_dir}")
        
        # Generate summary statistics
        total_devices = sum(scan['device_count'] for scans in scans_by_date.values() for scan in scans)
        avg_devices = total_devices / scan_id if scan_id > 0 else 0
        
        print(f"\nDataset Statistics:")
        print(f"  Total scans: {scan_id}")
        print(f"  Total device detections: {total_devices}")
        print(f"  Average devices per scan: {avg_devices:.2f}")
        print(f"  Date range: {min(scans_by_date.keys())} to {max(scans_by_date.keys())}")


def main():
    """Main entry point"""
    print("=" * 60)
    print("Synthetic Data Generator for Pedestrian Traffic Monitoring")
    print("=" * 60)
    print()
    print("This tool generates realistic synthetic data for testing")
    print("the system without real Bluetooth hardware.")
    print()
    
    # Get parameters
    start_date = input("Start date (YYYY-MM-DD) [default: today]: ").strip()
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            start_date = datetime.fromisoformat(start_date)
        except ValueError:
            print("Invalid date format. Using today.")
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    days_input = input("Number of days to generate [default: 14]: ").strip()
    days = int(days_input) if days_input else 14
    
    print()
    
    # Generate data
    generator = SyntheticDataGenerator()
    generator.generate_dataset(start_date, days)
    
    print("\n" + "=" * 60)
    print("Data generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Process the data: python3 data_collection/data_processor.py")
    print("2. Train models: python3 ml_models/model_trainer.py")
    print("3. Start API: python3 api/server.py")
    print("4. Launch dashboard: cd dashboard && npm start")
    print()


if __name__ == "__main__":
    main()
