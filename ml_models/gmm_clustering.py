#!/usr/bin/env python3
"""
GMM Clustering for Pedestrian Traffic Pattern Identification
Identifies quiet, moderate, and busy traffic patterns
"""

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import joblib
import yaml
import logging
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


class TrafficPatternClustering:
    """GMM-based clustering for identifying traffic patterns"""
    
    def __init__(self, config_path="data_collection/config.yaml"):
        """Initialize clustering model"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        self.models_dir = Path(self.config['storage']['models_dir'])
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.scaler = StandardScaler()
        self.gmm = None
        self.cluster_labels = ['Quiet', 'Moderate', 'Busy']
        
        self.logger.info("Traffic pattern clustering initialized")
    
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
                logging.FileHandler(log_dir / 'gmm_clustering.log'),
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
        self.logger.info(f"Loaded {len(df)} records")
        return df
    
    def prepare_features(self, df):
        """
        Prepare features for clustering
        
        Args:
            df: DataFrame with traffic data
            
        Returns:
            Feature array for clustering
        """
        # Primary feature: average devices
        features = df[['avg_devices']].copy()
        
        # Optional: add time context features
        if 'hour' in df.columns:
            features['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            features['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        if 'day_of_week' in df.columns:
            features['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            features['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        self.logger.info(f"Prepared {features.shape[1]} features for clustering")
        return features.values
    
    def train(self, X, df):
        """
        Train GMM clustering model
        
        Args:
            X: Feature array
            df: Original DataFrame for reference
            
        Returns:
            Trained GMM model
        """
        self.logger.info("Training GMM clustering model...")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Get GMM parameters from config
        n_components = self.config['models']['gmm']['n_components']
        covariance_type = self.config['models']['gmm']['covariance_type']
        max_iter = self.config['models']['gmm']['max_iter']
        random_state = self.config['models']['gmm']['random_state']
        
        # Train GMM
        self.gmm = GaussianMixture(
            n_components=n_components,
            covariance_type=covariance_type,
            max_iter=max_iter,
            random_state=random_state,
            verbose=1
        )
        
        self.gmm.fit(X_scaled)
        
        # Get cluster assignments
        clusters = self.gmm.predict(X_scaled)
        
        # Order clusters by traffic volume (low to high)
        cluster_means = []
        for i in range(n_components):
            mask = clusters == i
            cluster_means.append(df.loc[mask, 'avg_devices'].mean())
        
        # Create mapping from cluster index to ordered label
        sorted_indices = np.argsort(cluster_means)
        self.cluster_mapping = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_indices)}
        
        self.logger.info("GMM training complete")
        self.logger.info(f"Cluster means: {[f'{m:.2f}' for m in sorted(cluster_means)]}")
        
        return self.gmm
    
    def predict(self, X):
        """
        Predict cluster labels for new data
        
        Args:
            X: Feature array
            
        Returns:
            Cluster labels (0=Quiet, 1=Moderate, 2=Busy)
        """
        X_scaled = self.scaler.transform(X)
        raw_clusters = self.gmm.predict(X_scaled)
        
        # Map to ordered clusters
        ordered_clusters = np.array([self.cluster_mapping[c] for c in raw_clusters])
        
        return ordered_clusters
    
    def predict_proba(self, X):
        """
        Predict cluster probabilities
        
        Args:
            X: Feature array
            
        Returns:
            Array of probabilities for each cluster
        """
        X_scaled = self.scaler.transform(X)
        proba = self.gmm.predict_proba(X_scaled)
        
        # Reorder probabilities according to cluster mapping
        ordered_proba = np.zeros_like(proba)
        for old_idx, new_idx in self.cluster_mapping.items():
            ordered_proba[:, new_idx] = proba[:, old_idx]
        
        return ordered_proba
    
    def evaluate(self, X, df):
        """
        Evaluate clustering quality
        
        Args:
            X: Feature array
            df: Original DataFrame
            
        Returns:
            Dictionary of evaluation metrics
        """
        from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
        
        self.logger.info("Evaluating clustering quality...")
        
        X_scaled = self.scaler.transform(X)
        clusters = self.predict(X)
        
        # Calculate metrics
        metrics = {
            'silhouette_score': silhouette_score(X_scaled, clusters),
            'davies_bouldin_score': davies_bouldin_score(X_scaled, clusters),
            'calinski_harabasz_score': calinski_harabasz_score(X_scaled, clusters)
        }
        
        # Cluster statistics
        for i, label in enumerate(self.cluster_labels):
            mask = clusters == i
            count = mask.sum()
            mean_devices = df.loc[mask, 'avg_devices'].mean()
            std_devices = df.loc[mask, 'avg_devices'].std()
            
            metrics[f'{label.lower()}_count'] = int(count)
            metrics[f'{label.lower()}_mean'] = float(mean_devices)
            metrics[f'{label.lower()}_std'] = float(std_devices)
        
        # Log results
        self.logger.info("Clustering Evaluation:")
        self.logger.info(f"  Silhouette Score: {metrics['silhouette_score']:.3f}")
        self.logger.info(f"  Davies-Bouldin Score: {metrics['davies_bouldin_score']:.3f}")
        self.logger.info(f"  Calinski-Harabasz Score: {metrics['calinski_harabasz_score']:.3f}")
        
        for label in self.cluster_labels:
            label_lower = label.lower()
            self.logger.info(
                f"  {label}: {metrics[f'{label_lower}_count']} samples, "
                f"mean={metrics[f'{label_lower}_mean']:.2f}, "
                f"std={metrics[f'{label_lower}_std']:.2f}"
            )
        
        return metrics
    
    def visualize_clusters(self, df, clusters, save_path=None):
        """
        Create visualization of clustering results
        
        Args:
            df: DataFrame with traffic data
            clusters: Cluster assignments
            save_path: Optional path to save figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Add cluster labels to dataframe
        df_plot = df.copy()
        df_plot['cluster'] = clusters
        df_plot['cluster_label'] = df_plot['cluster'].map(
            {i: label for i, label in enumerate(self.cluster_labels)}
        )
        
        # 1. Traffic over time colored by cluster
        ax = axes[0, 0]
        for i, label in enumerate(self.cluster_labels):
            mask = df_plot['cluster'] == i
            ax.scatter(
                df_plot.loc[mask, 'timestamp'],
                df_plot.loc[mask, 'avg_devices'],
                label=label,
                alpha=0.6,
                s=30
            )
        ax.set_xlabel('Time')
        ax.set_ylabel('Average Devices')
        ax.set_title('Traffic Patterns Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Distribution of traffic by cluster
        ax = axes[0, 1]
        for i, label in enumerate(self.cluster_labels):
            mask = df_plot['cluster'] == i
            ax.hist(
                df_plot.loc[mask, 'avg_devices'],
                bins=30,
                alpha=0.6,
                label=label
            )
        ax.set_xlabel('Average Devices')
        ax.set_ylabel('Frequency')
        ax.set_title('Traffic Distribution by Cluster')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. Hourly patterns by cluster
        ax = axes[1, 0]
        if 'hour' in df_plot.columns:
            hourly_patterns = df_plot.groupby(['hour', 'cluster_label'])['avg_devices'].mean().unstack()
            hourly_patterns.plot(ax=ax, marker='o')
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Average Devices')
            ax.set_title('Hourly Traffic Patterns by Cluster')
            ax.legend(title='Cluster')
            ax.grid(True, alpha=0.3)
        
        # 4. Weekly patterns by cluster
        ax = axes[1, 1]
        if 'day_of_week' in df_plot.columns:
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            weekly_patterns = df_plot.groupby(['day_of_week', 'cluster_label'])['avg_devices'].mean().unstack()
            weekly_patterns.plot(kind='bar', ax=ax)
            ax.set_xlabel('Day of Week')
            ax.set_ylabel('Average Devices')
            ax.set_title('Weekly Traffic Patterns by Cluster')
            ax.set_xticklabels(day_names, rotation=45)
            ax.legend(title='Cluster')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"Visualization saved to {save_path}")
        
        return fig
    
    def save_model(self, filename='gmm_clustering_model.pkl'):
        """
        Save trained model and scaler
        
        Args:
            filename: Model filename
        """
        model_path = self.models_dir / filename
        
        model_data = {
            'gmm': self.gmm,
            'scaler': self.scaler,
            'cluster_mapping': self.cluster_mapping,
            'cluster_labels': self.cluster_labels,
            'config': self.config
        }
        
        joblib.dump(model_data, model_path)
        self.logger.info(f"Model saved to {model_path}")
    
    def load_model(self, filename='gmm_clustering_model.pkl'):
        """
        Load trained model
        
        Args:
            filename: Model filename
        """
        model_path = self.models_dir / filename
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        model_data = joblib.load(model_path)
        
        self.gmm = model_data['gmm']
        self.scaler = model_data['scaler']
        self.cluster_mapping = model_data['cluster_mapping']
        self.cluster_labels = model_data['cluster_labels']
        
        self.logger.info(f"Model loaded from {model_path}")


def main():
    """Main entry point for training GMM clustering"""
    print("=" * 60)
    print("Traffic Pattern Clustering - GMM Training")
    print("=" * 60)
    print()
    
    # Initialize clustering
    clustering = TrafficPatternClustering()
    
    # Load processed data
    data_path = Path("data/processed/processed_traffic_data.csv")
    if not data_path.exists():
        print(f"Error: Processed data not found at {data_path}")
        print("Please run data_processor.py first")
        return
    
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
    
    print("\nTraining complete!")
    print(f"Silhouette Score: {metrics['silhouette_score']:.3f}")
    print(f"Model saved to: {clustering.models_dir}")


if __name__ == "__main__":
    main()
