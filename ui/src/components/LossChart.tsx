'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  TimeScale,
  LogarithmicScale
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import { apiClient } from '@/utils/api';
import Loading from '@/components/Loading';

ChartJS.register(
  CategoryScale,
  LinearScale,
  LogarithmicScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface LossChartProps {
  jobId: string;
  height?: number;
  refreshInterval?: number;
  className?: string;
}

interface MetricData {
  step: number;
  timestamp: string;
  [key: string]: any; // 动态的loss字段
}

interface MetricsResponse {
  success: boolean;
  data: MetricData[];
  totalSteps: number;
  availableMetrics: string[];
  jobId: string;
  metricType: string;
}

const LossChart: React.FC<LossChartProps> = ({ 
  jobId, 
  height = 400,
  refreshInterval = 10000,
  className = ''
}) => {
  const [data, setData] = useState<MetricData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['loss']);
  const [availableMetrics, setAvailableMetrics] = useState<string[]>([]);
  const [yAxisType, setYAxisType] = useState<'linear' | 'logarithmic'>('linear');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isClearing, setIsClearing] = useState(false);
  const [smoothingFactor, setSmoothingFactor] = useState(0.6); // 0为完全平滑，1为不平滑
  const [showRawData, setShowRawData] = useState(false); // 是否显示原始数据
  const isFetchingRef = useRef(false);

  // 预定义的颜色
  const colors = [
    '#ef4444', '#3b82f6', '#10b981', '#f59e0b',
    '#8b5cf6', '#ec4899', '#6b7280', '#14b8a6',
    '#f97316', '#84cc16', '#06b6d4', '#a855f7'
  ];

  // 获取数据
  const fetchData = async () => {
    if (isFetchingRef.current) return;
    
    isFetchingRef.current = true;
    try {
      const response = await apiClient.get(`/api/metrics?jobId=${jobId}&type=loss&limit=2000`);
      const result: MetricsResponse = response.data;
      
      if (result.success) {
        setData(result.data);
        setAvailableMetrics(result.availableMetrics);
        setLastUpdated(new Date());
        setError(null);
        
        // 自动选择第一个metric如果没有选择
        if (selectedMetrics.length === 0 && result.availableMetrics.length > 0) {
          setSelectedMetrics([result.availableMetrics[0]]);
        }
      } else {
        setError('Failed to fetch metrics data');
      }
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError('Failed to fetch metrics data');
    } finally {
      isFetchingRef.current = false;
      setLoading(false);
    }
  };

  // 清除metrics数据
  const clearMetricsData = async () => {
    if (isClearing) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to clear all training metrics data for job "${jobId}"? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setIsClearing(true);
    try {
      const response = await apiClient.delete(`/api/metrics?jobId=${jobId}&clearAll=true`);
      const result = response.data;
      
      if (result.success) {
        // 清除成功，重置所有数据
        setData([]);
        setAvailableMetrics([]);
        setSelectedMetrics(['loss']);
        setLastUpdated(null);
        setError(null);
        console.log('Metrics data cleared successfully');
      } else {
        setError('Failed to clear metrics data');
      }
    } catch (err) {
      console.error('Error clearing metrics:', err);
      setError('Failed to clear metrics data');
    } finally {
      setIsClearing(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // 设置定时刷新
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [jobId, refreshInterval]);

  // 处理metric选择变化
  const handleMetricToggle = (metric: string) => {
    setSelectedMetrics(prev => 
      prev.includes(metric)
        ? prev.filter(m => m !== metric)
        : [...prev, metric]
    );
  };

  // 平滑算法 - 指数移动平均 (EMA)
  const applySmoothingToData = (rawData: Array<{x: number, y: number}>, factor: number) => {
    if (rawData.length === 0 || factor === 1) return rawData;
    
    const smoothed = [...rawData];
    let smoothedValue = smoothed[0].y; // 第一个值不变
    
    for (let i = 1; i < smoothed.length; i++) {
      // EMA公式: smoothed = factor * current + (1 - factor) * previous_smoothed
      smoothedValue = factor * smoothed[i].y + (1 - factor) * smoothedValue;
      smoothed[i] = { ...smoothed[i], y: smoothedValue };
    }
    
    return smoothed;
  };

  // 图表数据处理
  const chartData = useMemo(() => {
    if (!data.length || selectedMetrics.length === 0) return null;

    const datasets: any[] = [];

    selectedMetrics.forEach((metric, index) => {
      const rawMetricData = data
        .filter(point => point[metric] !== undefined && point[metric] !== null)
        .map(point => ({
          x: point.step,
          y: point[metric]
        }))
        .filter(point => !isNaN(point.y) && isFinite(point.y));

      if (rawMetricData.length === 0) return;

      // 应用平滑处理
      const smoothedData = applySmoothingToData(rawMetricData, smoothingFactor);
      
      // 主要显示的数据集（平滑后或原始）
      const mainDataset = {
        label: metric + (smoothingFactor < 1 ? ' (smoothed)' : ''),
        data: smoothedData,
        borderColor: colors[index % colors.length],
        backgroundColor: colors[index % colors.length] + '20',
        borderWidth: 2,
        fill: false,
        tension: 0.1,
        pointRadius: smoothedData.length > 500 ? 0 : 1,
        pointHoverRadius: 4,
        pointBackgroundColor: colors[index % colors.length],
        pointBorderColor: colors[index % colors.length]
      };

      datasets.push(mainDataset);

      // 如果启用了显示原始数据且有平滑，则添加原始数据曲线
      if (showRawData && smoothingFactor < 1) {
        const rawDataset = {
          label: metric + ' (raw)',
          data: rawMetricData,
          borderColor: colors[index % colors.length] + '40', // 更透明
          backgroundColor: 'transparent',
          borderWidth: 1,
          fill: false,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 2,
          borderDash: [5, 5], // 虚线样式
        };
        datasets.push(rawDataset);
      }
    });

    return { datasets };
  }, [data, selectedMetrics, smoothingFactor, showRawData]);

  // 图表配置
  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    },
    scales: {
      x: {
        type: 'linear',
        title: {
          display: true,
          text: 'Training Steps',
          color: '#9ca3af'
        },
        grid: {
          color: '#374151',
          lineWidth: 0.5
        },
        ticks: {
          color: '#9ca3af'
        }
      },
      y: {
        type: yAxisType,
        title: {
          display: true,
          text: 'Loss Value',
          color: '#9ca3af'
        },
        grid: {
          color: '#374151',
          lineWidth: 0.5
        },
        ticks: {
          color: '#9ca3af'
        }
      }
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#e5e7eb',
          usePointStyle: true,
          padding: 15
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        titleColor: '#f3f4f6',
        bodyColor: '#e5e7eb',
        borderColor: '#4b5563',
        borderWidth: 1,
        cornerRadius: 8,
        callbacks: {
          label: function(context) {
            const value = context.parsed.y;
            return `${context.dataset.label}: ${value.toExponential(3)}`;
          }
        }
      }
    },
    elements: {
      line: {
        tension: 0.1
      }
    }
  };

  // 计算统计信息
  const stats = useMemo(() => {
    if (!data.length || selectedMetrics.length === 0) return null;

    const latestData = data[data.length - 1];
    const firstData = data[0];

    return {
      totalSteps: data.length,
      latestStep: latestData?.step || 0,
      firstStep: firstData?.step || 0,
      selectedValues: selectedMetrics.reduce((acc, metric) => {
        const latestValue = latestData?.[metric];
        if (latestValue !== undefined) {
          acc[metric] = latestValue;
        }
        return acc;
      }, {} as Record<string, number>)
    };
  }, [data, selectedMetrics]);

  if (loading && data.length === 0) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-96">
          <Loading />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-96 text-red-400">
          <div className="text-center">
            <p className="mb-2">Error loading training metrics</p>
            <p className="text-sm text-gray-500">{error}</p>
            <button 
              onClick={() => { setError(null); setLoading(true); fetchData(); }}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data.length) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-96 text-gray-400">
          <div className="text-center">
            <p className="mb-2">No training data available yet</p>
            <p className="text-sm text-gray-500">Data will appear when training starts</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
      {/* 标题和控制面板 */}
      <div className="mb-6 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-lg font-semibold text-white">Training Loss</h3>
            {lastUpdated && (
              <p className="text-sm text-gray-400">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="flex space-x-4">
            <select
              value={yAxisType}
              onChange={(e) => setYAxisType(e.target.value as 'linear' | 'logarithmic')}
              className="bg-gray-800 text-white rounded px-3 py-1 text-sm border border-gray-700 focus:border-blue-500 focus:outline-none"
            >
              <option value="linear">Linear Scale</option>
              <option value="logarithmic">Log Scale</option>
            </select>
            <button
              onClick={clearMetricsData}
              disabled={isClearing || loading}
              className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
              title="Clear all training metrics data for this job"
            >
              {isClearing ? 'Clearing...' : 'Clear Data'}
            </button>
            <button
              onClick={fetchData}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        
        {/* Metrics选择器 */}
        {availableMetrics.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-gray-400">Select metrics to display:</p>
            <div className="flex flex-wrap gap-2">
              {availableMetrics.map((metric) => (
                <label key={metric} className="flex items-center space-x-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedMetrics.includes(metric)}
                    onChange={() => handleMetricToggle(metric)}
                    className="rounded text-blue-500 focus:ring-blue-500 focus:ring-2 bg-gray-800 border-gray-600"
                  />
                  <span className="text-gray-300">{metric}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* 平滑控制面板 */}
        <div className="space-y-3 border-t border-gray-700 pt-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">Smoothing (TensorBoard style):</p>
            <span className="text-xs text-gray-500">
              Factor: {(smoothingFactor).toFixed(2)}
            </span>
          </div>
          
          <div className="space-y-2">
            {/* 平滑滑块 */}
            <div className="flex items-center space-x-3">
              <span className="text-xs text-gray-500 w-12">Smooth</span>
              <div className="flex-1 relative">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={smoothingFactor}
                  onChange={(e) => setSmoothingFactor(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                  style={{
                    background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${smoothingFactor * 100}%, #374151 ${smoothingFactor * 100}%, #374151 100%)`
                  }}
                />
              </div>
              <span className="text-xs text-gray-500 w-8">Raw</span>
            </div>

            {/* 快速预设按钮 */}
            <div className="flex items-center space-x-2">
              <span className="text-xs text-gray-500">Quick:</span>
              {[
                { label: 'None', value: 1 },
                { label: 'Light', value: 0.9 },
                { label: 'Medium', value: 0.6 },
                { label: 'Heavy', value: 0.3 },
                { label: 'Max', value: 0.01 }
              ].map(preset => (
                <button
                  key={preset.label}
                  onClick={() => setSmoothingFactor(preset.value)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    Math.abs(smoothingFactor - preset.value) < 0.05
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            {/* 显示原始数据切换 */}
            {smoothingFactor < 1 && (
              <div className="flex items-center space-x-2">
                <label className="flex items-center space-x-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showRawData}
                    onChange={(e) => setShowRawData(e.target.checked)}
                    className="rounded text-blue-500 focus:ring-blue-500 focus:ring-2 bg-gray-800 border-gray-600"
                  />
                  <span className="text-gray-300">Show raw data</span>
                </label>
                <span className="text-xs text-gray-500">(dashed lines)</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 图表 */}
      {chartData && selectedMetrics.length > 0 ? (
        <div style={{ height }} className="mb-4">
          <Line data={chartData} options={chartOptions} />
        </div>
      ) : (
        <div className="flex items-center justify-center h-96 text-gray-400">
          <p>Please select at least one metric to display</p>
        </div>
      )}

      {/* 统计信息 */}
      {stats && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-gray-800 rounded p-3">
            <div className="text-gray-400">Total Steps</div>
            <div className="text-white font-semibold">{stats.totalSteps}</div>
          </div>
          <div className="bg-gray-800 rounded p-3">
            <div className="text-gray-400">Latest Step</div>
            <div className="text-white font-semibold">{stats.latestStep}</div>
          </div>
          {Object.entries(stats.selectedValues).slice(0, 2).map(([metric, value]) => (
            <div key={metric} className="bg-gray-800 rounded p-3">
              <div className="text-gray-400">Latest {metric}</div>
              <div className="text-white font-semibold" title={value.toString()}>
                {value.toExponential(3)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LossChart;