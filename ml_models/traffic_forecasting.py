#!/usr/bin/env python3
"""
Traffic Forecasting Models
Predicts pedestrian traffic 4 hours ahead using XGBoost or LSTM
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import joblib
import yaml
import logging
import sys
import matplotlib.pyplot as plt
from pathlib import Path
import json


class TrafficForecaster:
    """Time series forecasting for pedestrian traffic"""
    
    def __init__(self, config_path="data_collection/config.yaml", model_type='xgboost'):
        """
        Initialize forecasting model
        
        Args:
            config_path: Path to configuration file
            model_type: 'xgboost' or 'lstm'
        """
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        self.model_type = model_type
        self.model = None
        self.feature_cols = None
        self.scaler = None
        
        self.models_dir = Path(self.config['storage']['models_dir'])
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Traffic forecaster initialized with {model_type} model")
    
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
                logging.FileHandler(log_dir / 'traffic_forecasting.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_data(self, filepath):
        """
        Load processed traffic data
        
        Args:
            filepath: Path to processed CSV file
            
        Returns:
            DataFrame with traffic data
        """
        self.logger.info(f"Loading data from {filepath}")
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        self.logger.info(f"Loaded {len(df)} records")
        return df
    
    def create_target(self, df, target_col='avg_devices', horizon=None):
        """
        Create forecast target (future values)
        
        Args:
            df: DataFrame with traffic data
            target_col: Column to forecast
            horizon: Hours ahead to forecast (default from config)
            
        Returns:
            DataFrame with target column
        """
        if horizon is None:
            horizon = self.config['models']['forecasting']['forecast_horizon']
        
        df = df.copy()
        df[f'{target_col}_future'] = df[target_col].shift(-horizon)
        
        # Drop rows without target
        df = df.dropna(subset=[f'{target_col}_future'])
        
        self.logger.info(f"Created target for {horizon}-hour forecast")
        return df
    
    def prepare_features_xgboost(self, df):
        """
        Prepare features for XGBoost model
        
        Args:
            df: DataFrame with traffic data
            
        Returns:
            X (features), y (target), feature names
        """
        # Select feature columns (exclude timestamp and target)
        exclude_cols = ['timestamp', 'avg_devices_future']
        self.feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[self.feature_cols].values
        y = df['avg_devices_future'].values
        
        self.logger.info(f"Prepared {len(self.feature_cols)} features for XGBoost")
        return X, y, self.feature_cols
    
    def prepare_sequences_lstm(self, df, lookback=None):
        """
        Prepare sequences for LSTM model
        
        Args:
            df: DataFrame with traffic data
            lookback: Number of time steps to look back
            
        Returns:
            X (sequences), y (targets)
        """
        if lookback is None:
            lookback = self.config['models']['forecasting']['lookback_window']
        
        # Use only avg_devices and time features
        feature_cols = ['avg_devices', 'hour', 'day_of_week', 'is_weekend']
        available_cols = [col for col in feature_cols if col in df.columns]
        
        data = df[available_cols].values
        target = df['avg_devices_future'].values
        
        # Normalize data
        from sklearn.preprocessing import MinMaxScaler
        self.scaler = MinMaxScaler()
        data_scaled = self.scaler.fit_transform(data)
        
        # Create sequences
        X, y = [], []
        for i in range(lookback, len(data_scaled)):
            X.append(data_scaled[i-lookback:i])
            y.append(target[i])
        
        X = np.array(X)
        y = np.array(y)
        
        self.logger.info(f"Prepared {len(X)} sequences with lookback={lookback}")
        return X, y
    
    def train_xgboost(self, X_train, y_train, X_val, y_val):
        """
        Train XGBoost model
        
        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            
        Returns:
            Trained XGBoost model
        """
        self.logger.info("Training XGBoost model...")
        
        # Get parameters from config
        params = self.config['models']['xgboost']
        
        self.model = xgb.XGBRegressor(
            n_estimators=params['n_estimators'],
            max_depth=params['max_depth'],
            learning_rate=params['learning_rate'],
            subsample=params['subsample'],
            colsample_bytree=params['colsample_bytree'],
            random_state=params['random_state'],
            objective='reg:squarederror',
            early_stopping_rounds=20,
            eval_metric='rmse'
        )
        
        # Train with validation
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=True
        )
        
        self.logger.info("XGBoost training complete")
        return self.model
    
    def build_lstm_model(self, input_shape):
        """
        Build LSTM neural network
        
        Args:
            input_shape: Shape of input sequences (timesteps, features)
            
        Returns:
            Compiled Keras model
        """
        params = self.config['models']['lstm']
        
        model = keras.Sequential([
            layers.LSTM(params['units'], return_sequences=True, input_shape=input_shape),
            layers.Dropout(params['dropout']),
            layers.LSTM(params['units'] // 2),
            layers.Dropout(params['dropout']),
            layers.Dense(32, activation='relu'),
            layers.Dense(1)
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train_lstm(self, X_train, y_train, X_val, y_val):
        """
        Train LSTM model
        
        Args:
            X_train, y_train: Training data
            X_val, y_val: Validation data
            
        Returns:
            Trained LSTM model
        """
        self.logger.info("Training LSTM model...")
        
        params = self.config['models']['lstm']
        
        # Build model
        self.model = self.build_lstm_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        # Callbacks
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        # Train
        history = self.model.fit(
            X_train, y_train,
            epochs=params['epochs'],
            batch_size=params['batch_size'],
            validation_data=(X_val, y_val),
            callbacks=[early_stop],
            verbose=1
        )
        
        self.logger.info("LSTM training complete")
        return self.model, history
    
    def evaluate(self, X_test, y_test):
        """
        Evaluate model performance
        
        Args:
            X_test, y_test: Test data
            
        Returns:
            Dictionary of evaluation metrics
        """
        self.logger.info("Evaluating model...")
        
        # Get predictions
        if self.model_type == 'xgboost':
            y_pred = self.model.predict(X_test)
        else:  # lstm
            y_pred = self.model.predict(X_test).flatten()
        
        # Calculate metrics
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Calculate percentage errors
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
        
        metrics = {
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'mape': float(mape)
        }
        
        # Log results
        self.logger.info("Model Evaluation:")
        self.logger.info(f"  RMSE: {rmse:.3f}")
        self.logger.info(f"  MAE: {mae:.3f}")
        self.logger.info(f"  R²: {r2:.3f}")
        self.logger.info(f"  MAPE: {mape:.2f}%")
        
        return metrics, y_pred
    
    def visualize_predictions(self, y_true, y_pred, timestamps=None, save_path=None):
        """
        Visualize prediction results
        
        Args:
            y_true: True values
            y_pred: Predicted values
            timestamps: Optional timestamps for x-axis
            save_path: Path to save figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Predictions vs Actual
        ax = axes[0, 0]
        if timestamps is not None:
            ax.plot(timestamps, y_true, label='Actual', alpha=0.7)
            ax.plot(timestamps, y_pred, label='Predicted', alpha=0.7)
            ax.set_xlabel('Time')
        else:
            ax.plot(y_true, label='Actual', alpha=0.7)
            ax.plot(y_pred, label='Predicted', alpha=0.7)
            ax.set_xlabel('Sample')
        ax.set_ylabel('Traffic Volume')
        ax.set_title('Predictions vs Actual Values')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Scatter plot
        ax = axes[0, 1]
        ax.scatter(y_true, y_pred, alpha=0.5)
        min_val = min(y_true.min(), y_pred.min())
        max_val = max(y_true.max(), y_pred.max())
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
        ax.set_xlabel('Actual')
        ax.set_ylabel('Predicted')
        ax.set_title('Prediction Scatter Plot')
        ax.grid(True, alpha=0.3)
        
        # 3. Residuals
        ax = axes[1, 0]
        residuals = y_true - y_pred
        ax.hist(residuals, bins=50, edgecolor='black')
        ax.set_xlabel('Residual')
        ax.set_ylabel('Frequency')
        ax.set_title('Residual Distribution')
        ax.axvline(x=0, color='r', linestyle='--')
        ax.grid(True, alpha=0.3)
        
        # 4. Residuals over time
        ax = axes[1, 1]
        if timestamps is not None:
            ax.plot(timestamps, residuals, alpha=0.7)
            ax.set_xlabel('Time')
        else:
            ax.plot(residuals, alpha=0.7)
            ax.set_xlabel('Sample')
        ax.set_ylabel('Residual')
        ax.set_title('Residuals Over Time')
        ax.axhline(y=0, color='r', linestyle='--')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Visualization saved to {save_path}")
        
        return fig
    
    def save_model(self, filename=None):
        """
        Save trained model
        
        Args:
            filename: Model filename
        """
        if filename is None:
            filename = f'{self.model_type}_forecaster.pkl'
        
        model_path = self.models_dir / filename
        
        if self.model_type == 'xgboost':
            # Save XGBoost model and metadata
            model_data = {
                'model': self.model,
                'feature_cols': self.feature_cols,
                'model_type': self.model_type,
                'config': self.config
            }
            joblib.dump(model_data, model_path)
        else:  # lstm
            # Save Keras model
            self.model.save(model_path.with_suffix('.h5'))
            # Save scaler and metadata separately
            metadata = {
                'scaler': self.scaler,
                'model_type': self.model_type,
                'config': self.config
            }
            joblib.dump(metadata, model_path.with_suffix('.pkl'))
        
        self.logger.info(f"Model saved to {model_path}")
    
    def load_model(self, filename=None):
        """
        Load trained model
        
        Args:
            filename: Model filename
        """
        if filename is None:
            filename = f'{self.model_type}_forecaster.pkl'
        
        model_path = self.models_dir / filename
        
        if self.model_type == 'xgboost':
            model_data = joblib.load(model_path)
            self.model = model_data['model']
            self.feature_cols = model_data['feature_cols']
        else:  # lstm
            self.model = keras.models.load_model(model_path.with_suffix('.h5'))
            metadata = joblib.load(model_path.with_suffix('.pkl'))
            self.scaler = metadata['scaler']
        
        self.logger.info(f"Model loaded from {model_path}")
    
    def predict(self, X):
        """
        Make predictions on new data
        
        Args:
            X: Input features or sequences
            
        Returns:
            Predictions array
        """
        if self.model_type == 'xgboost':
            return self.model.predict(X)
        else:  # lstm
            return self.model.predict(X).flatten()


def main():
    """Main entry point for training forecasting model"""
    print("=" * 60)
    print("Traffic Forecasting - Model Training")
    print("=" * 60)
    print()
    
    # Choose model type
    model_type = 'xgboost'  # or 'lstm'
    print(f"Training {model_type.upper()} model\n")
    
    # Initialize forecaster
    forecaster = TrafficForecaster(model_type=model_type)
    
    # Load data
    data_path = Path("data/processed/processed_traffic_data.csv")
    if not data_path.exists():
        print(f"Error: Processed data not found at {data_path}")
        print("Please run data_processor.py first")
        return
    
    df = forecaster.load_data(data_path)
    
    # Create target
    df = forecaster.create_target(df)
    
    # Train-test split (time series aware)
    train_size = int(len(df) * 0.8)
    df_train = df.iloc[:train_size]
    df_test = df.iloc[train_size:]
    
    if model_type == 'xgboost':
        # Prepare features
        X_train, y_train, feature_cols = forecaster.prepare_features_xgboost(df_train)
        X_test, y_test, _ = forecaster.prepare_features_xgboost(df_test)
        
        # Split training into train/val
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42
        )
        
        # Train
        forecaster.train_xgboost(X_train, y_train, X_val, y_val)
        
    else:  # lstm
        # Prepare sequences
        X_train, y_train = forecaster.prepare_sequences_lstm(df_train)
        X_test, y_test = forecaster.prepare_sequences_lstm(df_test)
        
        # Split training into train/val
        val_split = int(len(X_train) * 0.8)
        X_val = X_train[val_split:]
        y_val = y_train[val_split:]
        X_train = X_train[:val_split]
        y_train = y_train[:val_split]
        
        # Train
        forecaster.train_lstm(X_train, y_train, X_val, y_val)
    
    # Evaluate
    metrics, y_pred = forecaster.evaluate(X_test, y_test)
    
    # Visualize
    viz_path = Path(f"data/models/{model_type}_predictions.png")
    forecaster.visualize_predictions(y_test, y_pred, save_path=viz_path)
    
    # Save model
    forecaster.save_model()
    
    # Save metrics
    metrics_path = Path(f"data/models/{model_type}_metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print("\nTraining complete!")
    print(f"RMSE: {metrics['rmse']:.3f}")
    print(f"R²: {metrics['r2']:.3f}")
    print(f"Model saved to: {forecaster.models_dir}")


if __name__ == "__main__":
    main()
