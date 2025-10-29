#!/usr/bin/env python3
"""
Flask API Server for Pedestrian Traffic Monitoring Dashboard
Serves real-time predictions and historical data
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import logging
import sys
import joblib
import threading
import time


class TrafficMonitoringAPI:
    """API server for traffic monitoring dashboard"""
    
    def __init__(self, config_path="data_collection/config.yaml"):
        """Initialize API server"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app, origins=self.config['api']['cors_origins'])
        
        # Load models
        self.models_dir = Path(self.config['storage']['models_dir'])
        self.processed_data_dir = Path(self.config['storage']['processed_data_dir'])
        
        self.clustering_model = None
        self.forecasting_model = None
        self.latest_predictions = None
        self.latest_data = None
        
        # Setup routes
        self.setup_routes()
        
        # Start background update thread
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        
        self.logger.info("API server initialized")
    
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
                logging.FileHandler(log_dir / 'api_server.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_models(self):
        """Load trained ML models"""
        try:
            # Load clustering model
            clustering_path = self.models_dir / 'gmm_clustering_model.pkl'
            if clustering_path.exists():
                self.clustering_model = joblib.load(clustering_path)
                self.logger.info("Clustering model loaded")
            else:
                self.logger.warning("Clustering model not found")
            
            # Load forecasting model
            forecasting_path = self.models_dir / 'xgboost_forecaster.pkl'
            if forecasting_path.exists():
                self.forecasting_model = joblib.load(forecasting_path)
                self.logger.info("Forecasting model loaded")
            else:
                self.logger.warning("Forecasting model not found")
        
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
    
    def load_latest_data(self):
        """Load latest processed data"""
        try:
            data_path = self.processed_data_dir / 'processed_traffic_data.csv'
            if data_path.exists():
                df = pd.read_csv(data_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                self.latest_data = df.sort_values('timestamp')
                self.logger.info(f"Loaded {len(df)} records")
            else:
                self.logger.warning("Processed data not found")
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
    
    def generate_predictions(self):
        """Generate predictions for next 4 hours"""
        try:
            if self.forecasting_model is None or self.latest_data is None:
                self.logger.warning("Models or data not available for predictions")
                return None
            
            # Get latest features
            latest_features = self.latest_data.iloc[-1:][self.forecasting_model['feature_cols']]
            
            # Generate prediction
            model = self.forecasting_model['model']
            prediction = model.predict(latest_features.values)[0]
            
            # Get current cluster if clustering model available
            current_cluster = None
            cluster_label = None
            cluster_proba = None
            
            if self.clustering_model is not None:
                clustering = self.clustering_model
                X = self.latest_data.iloc[-1:][['avg_devices']].values
                current_cluster = int(clustering['gmm'].predict(
                    clustering['scaler'].transform(X)
                )[0])
                cluster_label = clustering['cluster_labels'][current_cluster]
                cluster_proba = clustering['gmm'].predict_proba(
                    clustering['scaler'].transform(X)
                )[0].tolist()
            
            # Create prediction object
            current_time = datetime.now()
            forecast_time = current_time + timedelta(hours=4)
            
            self.latest_predictions = {
                'timestamp': current_time.isoformat(),
                'current_traffic': float(self.latest_data.iloc[-1]['avg_devices']),
                'predicted_traffic': float(prediction),
                'forecast_time': forecast_time.isoformat(),
                'current_cluster': cluster_label,
                'cluster_probabilities': {
                    'Quiet': cluster_proba[0] if cluster_proba else None,
                    'Moderate': cluster_proba[1] if cluster_proba else None,
                    'Busy': cluster_proba[2] if cluster_proba else None
                }
            }
            
            self.logger.info(f"Generated prediction: {prediction:.2f} devices")
            return self.latest_predictions
        
        except Exception as e:
            self.logger.error(f"Error generating predictions: {e}")
            return None
    
    def _update_loop(self):
        """Background thread for updating predictions"""
        update_interval = self.config['api']['update_interval']
        
        while self.running:
            try:
                self.load_latest_data()
                self.generate_predictions()
                time.sleep(update_interval)
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
                time.sleep(10)
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'models_loaded': {
                    'clustering': self.clustering_model is not None,
                    'forecasting': self.forecasting_model is not None
                }
            })
        
        @self.app.route('/api/current', methods=['GET'])
        def get_current():
            """Get current traffic conditions"""
            if self.latest_predictions is None:
                return jsonify({'error': 'No predictions available'}), 503
            
            return jsonify(self.latest_predictions)
        
        @self.app.route('/api/history', methods=['GET'])
        def get_history():
            """Get historical traffic data"""
            if self.latest_data is None:
                return jsonify({'error': 'No data available'}), 503
            
            # Get query parameters
            hours = request.args.get('hours', 48, type=int)
            
            # Filter last N hours
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_data = self.latest_data[
                self.latest_data['timestamp'] >= cutoff_time
            ].copy()
            
            # Convert to JSON-friendly format
            history = []
            for _, row in recent_data.iterrows():
                history.append({
                    'timestamp': row['timestamp'].isoformat(),
                    'traffic': float(row['avg_devices']),
                    'hour': int(row['hour']) if 'hour' in row else None,
                    'day_of_week': int(row['day_of_week']) if 'day_of_week' in row else None
                })
            
            return jsonify({
                'data': history,
                'count': len(history)
            })
        
        @self.app.route('/api/statistics', methods=['GET'])
        def get_statistics():
            """Get traffic statistics"""
            if self.latest_data is None:
                return jsonify({'error': 'No data available'}), 503
            
            # Calculate statistics
            stats = {
                'current': {
                    'traffic': float(self.latest_data.iloc[-1]['avg_devices']),
                    'timestamp': self.latest_data.iloc[-1]['timestamp'].isoformat()
                },
                'today': {
                    'mean': float(self.latest_data.tail(24)['avg_devices'].mean()),
                    'max': float(self.latest_data.tail(24)['avg_devices'].max()),
                    'min': float(self.latest_data.tail(24)['avg_devices'].min())
                },
                'all_time': {
                    'mean': float(self.latest_data['avg_devices'].mean()),
                    'max': float(self.latest_data['avg_devices'].max()),
                    'min': float(self.latest_data['avg_devices'].min()),
                    'std': float(self.latest_data['avg_devices'].std())
                }
            }
            
            return jsonify(stats)
        
        @self.app.route('/api/hourly_pattern', methods=['GET'])
        def get_hourly_pattern():
            """Get average traffic by hour of day"""
            if self.latest_data is None or 'hour' not in self.latest_data.columns:
                return jsonify({'error': 'No data available'}), 503
            
            hourly = self.latest_data.groupby('hour')['avg_devices'].agg(['mean', 'std']).reset_index()
            
            pattern = []
            for _, row in hourly.iterrows():
                pattern.append({
                    'hour': int(row['hour']),
                    'mean': float(row['mean']),
                    'std': float(row['std'])
                })
            
            return jsonify({'data': pattern})
        
        @self.app.route('/api/weekly_pattern', methods=['GET'])
        def get_weekly_pattern():
            """Get average traffic by day of week"""
            if self.latest_data is None or 'day_of_week' not in self.latest_data.columns:
                return jsonify({'error': 'No data available'}), 503
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekly = self.latest_data.groupby('day_of_week')['avg_devices'].agg(['mean', 'std']).reset_index()
            
            pattern = []
            for _, row in weekly.iterrows():
                pattern.append({
                    'day': day_names[int(row['day_of_week'])],
                    'day_of_week': int(row['day_of_week']),
                    'mean': float(row['mean']),
                    'std': float(row['std'])
                })
            
            return jsonify({'data': pattern})
        
        @self.app.route('/api/predict', methods=['POST'])
        def predict():
            """Generate on-demand prediction"""
            self.generate_predictions()
            
            if self.latest_predictions is None:
                return jsonify({'error': 'Prediction failed'}), 500
            
            return jsonify(self.latest_predictions)
    
    def run(self):
        """Start the API server"""
        # Load models
        self.load_models()
        
        # Start update thread
        self.update_thread.start()
        
        # Run Flask app
        host = self.config['api']['host']
        port = self.config['api']['port']
        debug = self.config['api']['debug']
        
        self.logger.info(f"Starting API server on {host}:{port}")
        print(f"\n{'='*60}")
        print(f"Traffic Monitoring API Server")
        print(f"{'='*60}")
        print(f"Server running at: http://{host}:{port}")
        print(f"API endpoints:")
        print(f"  - GET  /api/health          : Health check")
        print(f"  - GET  /api/current         : Current traffic & prediction")
        print(f"  - GET  /api/history         : Historical data")
        print(f"  - GET  /api/statistics      : Traffic statistics")
        print(f"  - GET  /api/hourly_pattern  : Hourly traffic pattern")
        print(f"  - GET  /api/weekly_pattern  : Weekly traffic pattern")
        print(f"  - POST /api/predict         : Generate new prediction")
        print(f"{'='*60}\n")
        
        self.app.run(host=host, port=port, debug=debug)
    
    def stop(self):
        """Stop the server"""
        self.running = False
        self.logger.info("API server stopped")


def main():
    """Main entry point"""
    api = TrafficMonitoringAPI()
    
    try:
        api.run()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        api.stop()
    except Exception as e:
        print(f"\nFatal error: {e}")
        api.logger.error("Fatal error", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
