#!/usr/bin/env python3
"""
Complete Model Training Pipeline
Trains both GMM clustering and forecasting models
"""

import sys
from pathlib import Path
import logging
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ml_models.gmm_clustering import TrafficPatternClustering
from ml_models.traffic_forecasting import TrafficForecaster
import json


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/model_trainer.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def train_clustering_model(data_path, logger):
    """
    Train GMM clustering model
    
    Args:
        data_path: Path to processed data
        logger: Logger instance
        
    Returns:
        Trained clustering model and metrics
    """
    logger.info("=" * 60)
    logger.info("TRAINING CLUSTERING MODEL")
    logger.info("=" * 60)
    
    # Initialize clustering
    clustering = TrafficPatternClustering()
    
    # Load data
    df = clustering.load_data(data_path)
    
    # Prepare features
    X = clustering.prepare_features(df)
    
    # Train model
    clustering.train(X, df)
    
    # Get predictions
    clusters = clustering.predict(X)
    
    # Evaluate
    metrics = clustering.evaluate(X, df)
    
    # Visualize
    viz_path = Path("data/models/clustering_visualization.png")
    clustering.visualize_clusters(df, clusters, viz_path)
    
    # Save model
    clustering.save_model()
    
    logger.info("Clustering model training complete")
    logger.info(f"Silhouette Score: {metrics['silhouette_score']:.3f}")
    
    return clustering, metrics


def train_forecasting_model(data_path, logger, model_type='xgboost'):
    """
    Train forecasting model
    
    Args:
        data_path: Path to processed data
        logger: Logger instance
        model_type: 'xgboost' or 'lstm'
        
    Returns:
        Trained forecaster and metrics
    """
    logger.info("=" * 60)
    logger.info(f"TRAINING {model_type.upper()} FORECASTING MODEL")
    logger.info("=" * 60)
    
    # Initialize forecaster
    forecaster = TrafficForecaster(model_type=model_type)
    
    # Load data
    df = forecaster.load_data(data_path)
    
    # Create target
    df = forecaster.create_target(df)
    
    # Train-test split (time series aware)
    train_size = int(len(df) * 0.8)
    df_train = df.iloc[:train_size]
    df_test = df.iloc[train_size:]
    
    logger.info(f"Training set: {len(df_train)} samples")
    logger.info(f"Test set: {len(df_test)} samples")
    
    if model_type == 'xgboost':
        # Prepare features
        X_train, y_train, feature_cols = forecaster.prepare_features_xgboost(df_train)
        X_test, y_test, _ = forecaster.prepare_features_xgboost(df_test)
        
        # Split training into train/val
        from sklearn.model_selection import train_test_split
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
    
    logger.info("Forecasting model training complete")
    logger.info(f"RMSE: {metrics['rmse']:.3f}")
    logger.info(f"R²: {metrics['r2']:.3f}")
    logger.info(f"MAPE: {metrics['mape']:.2f}%")
    
    return forecaster, metrics


def main():
    """Main training pipeline"""
    print("\n" + "=" * 60)
    print("PEDESTRIAN TRAFFIC MONITORING - MODEL TRAINING PIPELINE")
    print("=" * 60 + "\n")
    
    # Setup logging
    logger = setup_logging()
    
    # Check for processed data
    data_path = Path("data/processed/processed_traffic_data.csv")
    if not data_path.exists():
        logger.error(f"Processed data not found at {data_path}")
        logger.error("Please run data_processor.py first")
        print("\nERROR: No processed data found. Run data_processor.py first.")
        return 1
    
    try:
        # Train clustering model
        clustering, clustering_metrics = train_clustering_model(data_path, logger)
        
        print("\n" + "-" * 60)
        print("CLUSTERING RESULTS:")
        print(f"  Silhouette Score: {clustering_metrics['silhouette_score']:.3f}")
        print(f"  Quiet Traffic: {clustering_metrics['quiet_count']} samples "
              f"(mean={clustering_metrics['quiet_mean']:.2f})")
        print(f"  Moderate Traffic: {clustering_metrics['moderate_count']} samples "
              f"(mean={clustering_metrics['moderate_mean']:.2f})")
        print(f"  Busy Traffic: {clustering_metrics['busy_count']} samples "
              f"(mean={clustering_metrics['busy_mean']:.2f})")
        print("-" * 60 + "\n")
        
        # Train XGBoost forecasting model
        forecaster_xgb, xgb_metrics = train_forecasting_model(data_path, logger, 'xgboost')
        
        print("\n" + "-" * 60)
        print("XGBOOST FORECASTING RESULTS:")
        print(f"  RMSE: {xgb_metrics['rmse']:.3f}")
        print(f"  MAE: {xgb_metrics['mae']:.3f}")
        print(f"  R² Score: {xgb_metrics['r2']:.3f}")
        print(f"  MAPE: {xgb_metrics['mape']:.2f}%")
        print("-" * 60 + "\n")
        
        # Optionally train LSTM model
        response = input("Train LSTM model as well? (y/n): ").strip().lower()
        if response == 'y':
            forecaster_lstm, lstm_metrics = train_forecasting_model(data_path, logger, 'lstm')
            
            print("\n" + "-" * 60)
            print("LSTM FORECASTING RESULTS:")
            print(f"  RMSE: {lstm_metrics['rmse']:.3f}")
            print(f"  MAE: {lstm_metrics['mae']:.3f}")
            print(f"  R² Score: {lstm_metrics['r2']:.3f}")
            print(f"  MAPE: {lstm_metrics['mape']:.2f}%")
            print("-" * 60 + "\n")
        
        # Final summary
        print("\n" + "=" * 60)
        print("TRAINING PIPELINE COMPLETE")
        print("=" * 60)
        print("\nModels saved to: data/models/")
        print("Visualizations saved to: data/models/")
        print("\nNext steps:")
        print("1. Review model performance metrics")
        print("2. Check visualization plots")
        print("3. Start API server: python api/server.py")
        print("4. Launch dashboard: cd dashboard && npm start")
        print("=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Training pipeline failed: {e}", exc_info=True)
        print(f"\nERROR: Training failed - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
