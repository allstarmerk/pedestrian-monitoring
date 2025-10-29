#!/usr/bin/env python3
"""
Data Processor for Pedestrian Traffic Monitoring
Cleans, aggregates, and prepares Bluetooth scan data for ML models
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import logging
import sys

# Add utils directory to path for USB manager
sys.path.append(str(Path(__file__).parent.parent))
from utils.usb_manager import USBStorageManager


class DataProcessor:
    """Process and aggregate Bluetooth scan data"""
    
    def __init__(self, config_path="data_collection/config.yaml"):
        """Initialize processor with configuration"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize USB storage manager
        self.usb_manager = USBStorageManager()
        
        # Try to mount USB if available
        if self.usb_manager.find_usb_device():
            self.usb_manager.mount_usb()
            usb_info = self.usb_manager.get_usb_info()
            if usb_info['mounted']:
                self.logger.info(f"USB storage found: {usb_info['available_space_gb']} GB available")
        
        # Get storage paths (USB or local fallback)
        self.raw_data_dir = self.usb_manager.get_storage_path('raw')
        self.processed_data_dir = self.usb_manager.get_storage_path('processed')
        
        self.logger.info(f"Reading raw data from: {self.raw_data_dir}")
        self.logger.info(f"Writing processed data to: {self.processed_data_dir}")
        
        self.logger.info("Data processor initialized")
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def setup_logging(self):
        """Configure logging"""
        log_dir = Path(self.config['storage']['logs_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format=self.config['logging']['format'],
            handlers=[
                logging.FileHandler(log_dir / 'data_processor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_raw_data(self, start_date=None, end_date=None):
        """
        Load raw scan data from JSONL files
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            DataFrame with scan records
        """
        self.logger.info("Loading raw scan data...")
        
        # Find all scan files
        scan_files = sorted(self.raw_data_dir.glob("scan_*.jsonl"))
        
        if not scan_files:
            self.logger.warning("No scan files found")
            return pd.DataFrame()
        
        self.logger.info(f"Found {len(scan_files)} scan files")
        
        # Load all records
        all_records = []
        
        for filepath in scan_files:
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        record = json.loads(line)
                        all_records.append(record)
            except Exception as e:
                self.logger.error(f"Error loading {filepath}: {e}")
        
        if not all_records:
            self.logger.warning("No records found in scan files")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter by date if specified
        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]
        
        self.logger.info(f"Loaded {len(df)} scan records")
        return df
    
    def expand_devices(self, df):
        """
        Expand device list into individual rows
        
        Args:
            df: DataFrame with scan records
            
        Returns:
            DataFrame with one row per device detection
        """
        expanded_rows = []
        
        for _, row in df.iterrows():
            timestamp = row['timestamp']
            scan_id = row['scan_id']
            
            for device in row['devices']:
                expanded_rows.append({
                    'timestamp': timestamp,
                    'scan_id': scan_id,
                    'mac_hash': device['mac_hash'],
                    'rssi': device.get('rssi'),
                    'protocol': device.get('protocol', 'unknown')
                })
        
        expanded_df = pd.DataFrame(expanded_rows)
        self.logger.info(f"Expanded to {len(expanded_df)} device detections")
        
        return expanded_df
    
    def create_time_features(self, df):
        """
        Create time-based features for ML
        
        Args:
            df: DataFrame with timestamp column
            
        Returns:
            DataFrame with additional time features
        """
        df = df.copy()
        
        if self.config['features']['include_hour']:
            df['hour'] = df['timestamp'].dt.hour
        
        if self.config['features']['include_day_of_week']:
            df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        if self.config['features']['include_month']:
            df['month'] = df['timestamp'].dt.month
        
        if self.config['features']['include_is_weekend']:
            df['is_weekend'] = df['timestamp'].dt.dayofweek >= 5
        
        return df
    
    def aggregate_by_window(self, df, window_hours=None):
        """
        Aggregate device counts into time windows
        
        Args:
            df: DataFrame with device detections
            window_hours: Window size in hours (default from config)
            
        Returns:
            DataFrame with aggregated traffic counts
        """
        if window_hours is None:
            window_hours = self.config['aggregation']['window_size']
        
        self.logger.info(f"Aggregating data into {window_hours}-hour windows")
        
        # Group by unique devices per scan
        scans = df.groupby('scan_id').agg({
            'timestamp': 'first',
            'mac_hash': 'nunique'
        }).rename(columns={'mac_hash': 'device_count'})
        
        scans = scans.reset_index()
        
        # Resample into time windows
        scans = scans.set_index('timestamp')
        window_str = f'{window_hours}H'
        
        aggregated = scans.resample(window_str).agg({
            'device_count': ['mean', 'std', 'min', 'max', 'sum', 'count']
        })
        
        # Flatten column names
        aggregated.columns = ['_'.join(col).strip() for col in aggregated.columns.values]
        aggregated = aggregated.reset_index()
        
        # Rename for clarity
        aggregated = aggregated.rename(columns={
            'device_count_mean': 'avg_devices',
            'device_count_std': 'std_devices',
            'device_count_min': 'min_devices',
            'device_count_max': 'max_devices',
            'device_count_sum': 'total_devices',
            'device_count_count': 'num_scans'
        })
        
        # Filter windows with minimum scans
        min_scans = self.config['aggregation']['min_devices_per_window']
        aggregated = aggregated[aggregated['num_scans'] >= min_scans]
        
        # Add time features
        aggregated = self.create_time_features(aggregated)
        
        self.logger.info(f"Created {len(aggregated)} aggregated windows")
        return aggregated
    
    def create_lag_features(self, df, value_col='avg_devices'):
        """
        Create lagged features for time series prediction
        
        Args:
            df: DataFrame with time series data
            value_col: Column to create lags for
            
        Returns:
            DataFrame with lag features
        """
        df = df.copy()
        df = df.sort_values('timestamp')
        
        lag_periods = self.config['features']['lag_periods']
        
        for lag in lag_periods:
            df[f'{value_col}_lag_{lag}h'] = df[value_col].shift(lag)
        
        return df
    
    def create_rolling_features(self, df, value_col='avg_devices'):
        """
        Create rolling window statistics
        
        Args:
            df: DataFrame with time series data
            value_col: Column to calculate rolling stats for
            
        Returns:
            DataFrame with rolling features
        """
        df = df.copy()
        df = df.sort_values('timestamp')
        
        windows = self.config['features']['rolling_windows']
        stats = self.config['features']['rolling_stats']
        
        for window in windows:
            for stat in stats:
                col_name = f'{value_col}_rolling_{window}h_{stat}'
                if stat == 'mean':
                    df[col_name] = df[value_col].rolling(window=window, min_periods=1).mean()
                elif stat == 'std':
                    df[col_name] = df[value_col].rolling(window=window, min_periods=1).std()
                elif stat == 'min':
                    df[col_name] = df[value_col].rolling(window=window, min_periods=1).min()
                elif stat == 'max':
                    df[col_name] = df[value_col].rolling(window=window, min_periods=1).max()
        
        return df
    
    def prepare_ml_dataset(self, df):
        """
        Prepare complete dataset for ML training
        
        Args:
            df: Aggregated DataFrame
            
        Returns:
            DataFrame ready for ML with all features
        """
        self.logger.info("Preparing ML dataset with features...")
        
        # Sort by time
        df = df.sort_values('timestamp')
        
        # Create lag features
        df = self.create_lag_features(df)
        
        # Create rolling features
        df = self.create_rolling_features(df)
        
        # Drop rows with NaN values from lag/rolling features
        initial_len = len(df)
        df = df.dropna()
        self.logger.info(f"Dropped {initial_len - len(df)} rows with missing features")
        
        return df
    
    def save_processed_data(self, df, filename='processed_traffic_data.csv'):
        """
        Save processed dataset
        
        Args:
            df: Processed DataFrame
            filename: Output filename
        """
        filepath = self.processed_data_dir / filename
        df.to_csv(filepath, index=False)
        self.logger.info(f"Saved processed data to {filepath}")
        
        # Also save metadata
        metadata = {
            'num_records': len(df),
            'date_range': {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat()
            },
            'columns': list(df.columns),
            'processing_date': datetime.now().isoformat()
        }
        
        metadata_path = self.processed_data_dir / filename.replace('.csv', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_statistics(self, df):
        """
        Calculate and display dataset statistics
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary of statistics
        """
        stats = {
            'total_records': len(df),
            'date_range': {
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max(),
                'days': (df['timestamp'].max() - df['timestamp'].min()).days
            },
            'traffic_stats': {
                'mean_devices': df['avg_devices'].mean(),
                'std_devices': df['avg_devices'].std(),
                'min_devices': df['avg_devices'].min(),
                'max_devices': df['avg_devices'].max()
            }
        }
        
        return stats
    
    def process_all(self, start_date=None, end_date=None):
        """
        Run complete processing pipeline
        
        Args:
            start_date: Optional start date
            end_date: Optional end date
        """
        self.logger.info("Starting data processing pipeline")
        
        # Load raw data
        df = self.load_raw_data(start_date, end_date)
        
        if df.empty:
            self.logger.error("No data to process")
            return None
        
        # Expand devices
        expanded = self.expand_devices(df)
        
        # Aggregate
        aggregated = self.aggregate_by_window(expanded)
        
        # Prepare ML dataset
        ml_dataset = self.prepare_ml_dataset(aggregated)
        
        # Save
        self.save_processed_data(ml_dataset)
        
        # Display statistics
        stats = self.get_statistics(ml_dataset)
        
        self.logger.info("=" * 60)
        self.logger.info("Processing Complete - Statistics:")
        self.logger.info(f"  Total records: {stats['total_records']}")
        self.logger.info(f"  Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
        self.logger.info(f"  Days covered: {stats['date_range']['days']}")
        self.logger.info(f"  Average devices: {stats['traffic_stats']['mean_devices']:.2f}")
        self.logger.info(f"  Std deviation: {stats['traffic_stats']['std_devices']:.2f}")
        self.logger.info(f"  Min devices: {stats['traffic_stats']['min_devices']:.2f}")
        self.logger.info(f"  Max devices: {stats['traffic_stats']['max_devices']:.2f}")
        self.logger.info("=" * 60)
        
        return ml_dataset


def main():
    """Main entry point"""
    print("=" * 60)
    print("Pedestrian Traffic Monitoring - Data Processor")
    print("=" * 60)
    print()
    
    processor = DataProcessor()
    
    # Process all available data
    dataset = processor.process_all()
    
    if dataset is not None:
        print("\nProcessing successful!")
        print(f"Dataset shape: {dataset.shape}")
        print(f"Saved to: {processor.processed_data_dir}")
    else:
        print("\nProcessing failed - check logs for details")


if __name__ == "__main__":
    main()
