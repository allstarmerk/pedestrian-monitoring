# Pedestrian Congestion Monitoring System

A privacy-preserving, low-cost system for measuring and predicting pedestrian traffic at metro stations using Bluetooth signal detection and machine learning.

## 🎯 Project Overview

This system uses anonymous Bluetooth signal detection to estimate foot traffic patterns, applies machine learning for pattern recognition and forecasting, and provides real-time visualization through a web dashboard.

### Key Features
- **Privacy-First**: No cameras, no personal data - fully anonymous Bluetooth MAC hashing
- **Machine Learning**: GMM clustering for pattern identification + XGBoost/LSTM for forecasting
- **Real-Time Dashboard**: React-based visualization with automatic updates
- **Off-Grid Ready**: Solar-powered operation for long-term deployment
- **4-Hour Forecasting**: Predictive analytics for congestion management

## 📁 Project Structure

```
pedestrian-monitoring/
├── data_collection/
│   ├── bluetooth_scanner.py       # Raspberry Pi BLE scanning
│   ├── data_processor.py          # Data cleaning and aggregation
│   └── config.yaml                # Configuration settings
├── ml_models/
│   ├── gmm_clustering.py          # Pattern identification
│   ├── traffic_forecasting.py    # XGBoost/LSTM prediction models
│   ├── model_trainer.py           # Training pipeline
│   └── model_evaluator.py         # Performance metrics
├── api/
│   ├── server.py                  # Flask API for dashboard
│   └── endpoints.py               # REST endpoints
├── dashboard/
│   ├── src/
│   │   ├── App.jsx               # Main React component
│   │   ├── components/           # Dashboard components
│   │   └── utils/                # Helper functions
│   └── package.json
├── utils/
│   ├── privacy.py                # Anonymization utilities
│   └── hardware_monitor.py       # System health monitoring
├── data/
│   ├── raw/                      # Raw Bluetooth logs
│   ├── processed/                # Cleaned datasets
│   └── models/                   # Trained ML models
├── notebooks/
│   └── exploratory_analysis.ipynb
├── tests/
│   └── test_*.py                 # Unit tests
├── requirements.txt
└── README.md
```

## 🔧 Hardware Requirements

| Component | Purpose | Notes |
|-----------|---------|-------|
| Raspberry Pi 4 (4GB) | Core processor | Runs Python scripts |
| USB Bluetooth Adapter | Extended BLE range | Optional |
| Weatherproof Box (IP65+) | Protection | 8×6×4 inch |
| 21W Solar Panel | Power source | ALLPOWERS SP001 |
| 24,000 mAh Power Bank | Energy storage | Pass-through charging |
| Desiccant Packs | Moisture control | Optional |
| DS3231 RTC Module | Timekeeping | Optional, for offline operation |

## 📦 Software Installation

### Raspberry Pi Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y python3-pip bluetooth bluez libbluetooth-dev python3-dev

# Install Python packages
pip3 install -r requirements.txt

# Enable Bluetooth service
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

### Development Machine Setup

```bash
# Clone repository
git clone <repository-url>
cd pedestrian-monitoring

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dashboard dependencies
cd dashboard
npm install
```

## 🚀 Quick Start

### 1. Data Collection (Raspberry Pi)

```bash
# Configure settings
nano data_collection/config.yaml

# Start Bluetooth scanner
python3 data_collection/bluetooth_scanner.py
```

### 2. Train Models

```bash
# Process collected data
python3 data_collection/data_processor.py

# Train clustering and forecasting models
python3 ml_models/model_trainer.py

# Evaluate performance
python3 ml_models/model_evaluator.py
```

### 3. Start API Server

```bash
python3 api/server.py
```

### 4. Launch Dashboard

```bash
cd dashboard
npm start
```

Access dashboard at: http://localhost:3000

## 🔒 Privacy & Ethics

- **No Personal Data**: MAC addresses are immediately hashed with SHA-256
- **Stationary Filtering**: Devices present >1 hour are excluded (homes, parked vehicles)
- **Aggregated Analysis**: Individual device tracking is impossible
- **Transparent Operation**: System operation can be clearly signposted
- **GDPR Compliant**: No PII collection or storage

## 💾 Data Storage Options

**USB Storage (Recommended for field deployment):**
- Plug in any USB drive and data automatically saves to it
- Easy data retrieval - just unplug USB and take to your computer
- Automatic fallback to SD card if no USB present
- See **[USB_STORAGE_GUIDE.md](USB_STORAGE_GUIDE.md)** for setup

**SD Card Storage (Default):**
- Works without any external storage
- Data saved to Pi's SD card
- Access via network or direct connection

## 📊 System Workflow

1. **Data Collection**: Raspberry Pi scans for Bluetooth signals every 60 seconds
2. **Anonymization**: MAC addresses are hashed immediately
3. **Filtering**: Stationary devices removed based on duration thresholds
4. **Aggregation**: Data grouped into 4-hour windows
5. **Pattern Recognition**: GMM identifies traffic clusters (quiet/moderate/busy)
6. **Forecasting**: XGBoost/LSTM predicts traffic 4 hours ahead
7. **Visualization**: React dashboard displays real-time predictions

## 📈 Model Performance

Expected metrics after training:
- **GMM Clustering**: Silhouette Score > 0.5
- **Forecasting RMSE**: < 15% of mean traffic volume
- **Prediction Horizon**: 4 hours ahead
- **Update Frequency**: Real-time (1-minute intervals)

## 🛠️ Configuration

Edit `data_collection/config.yaml`:

```yaml
bluetooth:
  scan_interval: 60  # seconds
  stationary_threshold: 3600  # 1 hour in seconds
  
aggregation:
  window_size: 4  # hours
  
models:
  gmm_components: 3  # quiet, moderate, busy
  forecast_horizon: 4  # hours
  
api:
  port: 5000
  update_interval: 60  # seconds
```

## 📝 Maintenance

### Daily Tasks
- Monitor system logs: `tail -f data_collection/logs/scanner.log`
- Check hardware health: `python3 utils/hardware_monitor.py`

### Weekly Tasks
- Backup collected data
- Review prediction accuracy
- Clean temporary files

### Monthly Tasks
- Retrain models with new data
- Update system software
- Check hardware connections

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_data_processor.py

# Generate coverage report
python -m pytest --cov=. tests/
```

## 📚 Documentation

- [Data Collection Guide](docs/data_collection.md)
- [ML Model Documentation](docs/ml_models.md)
- [API Reference](docs/api_reference.md)
- [Dashboard Guide](docs/dashboard.md)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with privacy-first principles
- Inspired by ethical AI and smart city initiatives
- Designed for sustainable, off-grid operation

## 📧 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Status**: Production Ready ✅  
**Version**: 1.0.0  
**Last Updated**: October 2025
