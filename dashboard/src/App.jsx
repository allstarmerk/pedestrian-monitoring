import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { RefreshCw, Activity, TrendingUp, Clock, AlertCircle } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5000/api';

const TrafficDashboard = () => {
  const [currentData, setCurrentData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [hourlyPattern, setHourlyPattern] = useState([]);
  const [weeklyPattern, setWeeklyPattern] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch current traffic and prediction
  const fetchCurrent = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/current`);
      if (!response.ok) throw new Error('Failed to fetch current data');
      const data = await response.json();
      setCurrentData(data);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch historical data
  const fetchHistory = async (hours = 48) => {
    try {
      const response = await fetch(`${API_BASE_URL}/history?hours=${hours}`);
      if (!response.ok) throw new Error('Failed to fetch history');
      const data = await response.json();
      setHistoryData(data.data);
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch hourly pattern
  const fetchHourlyPattern = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/hourly_pattern`);
      if (!response.ok) throw new Error('Failed to fetch hourly pattern');
      const data = await response.json();
      setHourlyPattern(data.data);
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch weekly pattern
  const fetchWeeklyPattern = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/weekly_pattern`);
      if (!response.ok) throw new Error('Failed to fetch weekly pattern');
      const data = await response.json();
      setWeeklyPattern(data.data);
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch statistics
  const fetchStatistics = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/statistics`);
      if (!response.ok) throw new Error('Failed to fetch statistics');
      const data = await response.json();
      setStatistics(data);
    } catch (err) {
      setError(err.message);
    }
  };

  // Fetch all data
  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchCurrent(),
        fetchHistory(),
        fetchHourlyPattern(),
        fetchWeeklyPattern(),
        fetchStatistics()
      ]);
    } catch (err) {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Initial load and auto-refresh
  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  // Get cluster color
  const getClusterColor = (cluster) => {
    const colors = {
      'Quiet': '#10b981',
      'Moderate': '#f59e0b',
      'Busy': '#ef4444'
    };
    return colors[cluster] || '#6b7280';
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  // Format date
  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md">
          <div className="flex items-center text-red-600 mb-4">
            <AlertCircle className="mr-2" />
            <h2 className="text-xl font-semibold">Error Loading Dashboard</h2>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchAllData}
            className="w-full bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">Pedestrian Traffic Monitor</h1>
              <p className="text-gray-600 mt-1">Real-time congestion prediction using ML</p>
            </div>
            <button
              onClick={fetchAllData}
              className="flex items-center bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
            >
              <RefreshCw className="mr-2" size={18} />
              Refresh
            </button>
          </div>
          {lastUpdate && (
            <p className="text-sm text-gray-500 mt-2">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </p>
          )}
        </div>

        {/* Current Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          {/* Current Traffic */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-600">Current Traffic</h3>
              <Activity size={20} className="text-blue-500" />
            </div>
            <p className="text-3xl font-bold text-gray-800">
              {currentData?.current_traffic?.toFixed(1) || '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">devices detected</p>
          </div>

          {/* Predicted Traffic */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-600">Predicted (4h)</h3>
              <TrendingUp size={20} className="text-green-500" />
            </div>
            <p className="text-3xl font-bold text-gray-800">
              {currentData?.predicted_traffic?.toFixed(1) || '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {currentData?.forecast_time && formatTime(currentData.forecast_time)}
            </p>
          </div>

          {/* Current Status */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-600">Status</h3>
              <Clock size={20} className="text-purple-500" />
            </div>
            <p 
              className="text-2xl font-bold mt-2"
              style={{ color: getClusterColor(currentData?.current_cluster) }}
            >
              {currentData?.current_cluster || '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">congestion level</p>
          </div>

          {/* Today's Average */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-600">Today's Avg</h3>
              <Activity size={20} className="text-orange-500" />
            </div>
            <p className="text-3xl font-bold text-gray-800">
              {statistics?.today?.mean?.toFixed(1) || '—'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Max: {statistics?.today?.max?.toFixed(1) || '—'}
            </p>
          </div>
        </div>

        {/* Cluster Probabilities */}
        {currentData?.cluster_probabilities && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Pattern Probabilities</h3>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(currentData.cluster_probabilities).map(([label, prob]) => (
                prob !== null && (
                  <div key={label} className="text-center">
                    <div className="mb-2">
                      <div className="relative pt-1">
                        <div className="overflow-hidden h-4 text-xs flex rounded bg-gray-200">
                          <div
                            style={{ width: `${prob * 100}%`, backgroundColor: getClusterColor(label) }}
                            className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center transition-all duration-500"
                          ></div>
                        </div>
                      </div>
                    </div>
                    <p className="text-sm font-semibold" style={{ color: getClusterColor(label) }}>
                      {label}
                    </p>
                    <p className="text-xs text-gray-500">{(prob * 100).toFixed(1)}%</p>
                  </div>
                )
              ))}
            </div>
          </div>
        )}

        {/* Traffic History Chart */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Traffic History (48 Hours)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={historyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={(value) => formatTime(value)}
                tick={{ fontSize: 12 }}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleString()}
                formatter={(value) => [value.toFixed(1), 'Devices']}
              />
              <Area 
                type="monotone" 
                dataKey="traffic" 
                stroke="#3b82f6" 
                fill="#3b82f6" 
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Patterns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Hourly Pattern */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Average Traffic by Hour</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={hourlyPattern}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => value.toFixed(1)} />
                <Bar dataKey="mean" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Weekly Pattern */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Average Traffic by Day</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={weeklyPattern}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} angle={-45} textAnchor="end" height={80} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value) => value.toFixed(1)} />
                <Bar dataKey="mean" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Statistics Summary */}
        {statistics && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Statistical Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">All-Time Average</p>
                <p className="text-2xl font-bold text-gray-800">{statistics.all_time.mean.toFixed(1)}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">All-Time Max</p>
                <p className="text-2xl font-bold text-gray-800">{statistics.all_time.max.toFixed(1)}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">All-Time Min</p>
                <p className="text-2xl font-bold text-gray-800">{statistics.all_time.min.toFixed(1)}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">Std Deviation</p>
                <p className="text-2xl font-bold text-gray-800">{statistics.all_time.std.toFixed(1)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Privacy-preserving pedestrian monitoring • No cameras • No personal data</p>
          <p className="mt-1">Powered by Bluetooth detection, GMM clustering, and XGBoost forecasting</p>
        </div>
      </div>
    </div>
  );
};

export default TrafficDashboard;
