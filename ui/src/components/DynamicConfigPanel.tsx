'use client';

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/utils/api';
import { Settings, Save, RefreshCw, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';

interface DynamicConfigPanelProps {
  jobName: string;
  className?: string;
}

interface DynamicConfig {
  sample_every: number;
  save_every: number | null;
  log_every: number | null;
  last_updated: number | null;
}

interface ConfigResponse {
  success: boolean;
  config: DynamicConfig;
  configExists: boolean;
  configPath: string;
  error?: string;
  message?: string;
}

const DynamicConfigPanel: React.FC<DynamicConfigPanelProps> = ({ jobName, className = '' }) => {
  const [config, setConfig] = useState<DynamicConfig>({
    sample_every: 100,
    save_every: null,
    log_every: null,
    last_updated: null
  });
  
  const [formConfig, setFormConfig] = useState<DynamicConfig>({
    sample_every: 100,
    save_every: null,
    log_every: null,
    last_updated: null
  });
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [configExists, setConfigExists] = useState(false);
  const [configPath, setConfigPath] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 加载配置
  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get(`/api/dynamic-config?jobName=${encodeURIComponent(jobName)}`);
      const data: ConfigResponse = response.data;
      
      if (data.success) {
        setConfig(data.config);
        setFormConfig({ ...data.config });
        setConfigExists(data.configExists);
        setConfigPath(data.configPath);
      } else {
        setError(data.error || 'Failed to load configuration');
      }
    } catch (err) {
      console.error('Error loading dynamic config:', err);
      setError('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  // 保存配置
  const saveConfig = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);
      
      const response = await apiClient.post('/api/dynamic-config', {
        jobName: jobName,
        config: formConfig
      });
      
      const data: ConfigResponse = response.data;
      
      if (data.success) {
        setConfig(data.config);
        setFormConfig({ ...data.config });
        setConfigExists(true);
        setSuccessMessage(data.message || 'Configuration updated successfully');
        
        // 清除成功消息
        setTimeout(() => setSuccessMessage(null), 3000);
      } else {
        setError(data.error || 'Failed to save configuration');
      }
    } catch (err: any) {
      console.error('Error saving dynamic config:', err);
      const errorMessage = err.response?.data?.error || 'Failed to save configuration';
      setError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  // 重置表单
  const resetForm = () => {
    setFormConfig({ ...config });
    setError(null);
    setSuccessMessage(null);
  };

  // 检查是否有变化
  const hasChanges = () => {
    return JSON.stringify(config) !== JSON.stringify(formConfig);
  };

  useEffect(() => {
    if (jobName) {
      loadConfig();
    }
  }, [jobName]);

  if (loading) {
    return (
      <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-300">Loading configuration...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900 rounded-lg p-6 ${className}`}>
      {/* 标题 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Settings className="w-5 h-5 text-blue-500 mr-2" />
          <h3 className="text-lg font-semibold text-white">Dynamic Training Settings</h3>
        </div>
        <button
          onClick={loadConfig}
          disabled={loading}
          className="flex items-center px-3 py-1 text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 rounded transition-colors"
        >
          <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* 状态信息 */}
      <div className="mb-4 p-3 bg-gray-800 rounded-lg">
        <div className="flex items-center text-sm text-gray-400">
          <FileText className="w-4 h-4 mr-2" />
          <span>Config file: </span>
          <code className="ml-1 text-xs text-gray-300 break-all">{configPath}</code>
        </div>
        <div className="flex items-center mt-1 text-sm">
          {configExists ? (
            <>
              <CheckCircle2 className="w-4 h-4 mr-2 text-green-500" />
              <span className="text-green-400">File exists</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-4 h-4 mr-2 text-yellow-500" />
              <span className="text-yellow-400">File will be created when saved</span>
            </>
          )}
          {config.last_updated && (
            <span className="ml-4 text-gray-500">
              Last updated: {new Date(config.last_updated * 1000).toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* 错误消息 */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-500/20 rounded-lg">
          <div className="flex items-center text-red-400">
            <AlertCircle className="w-4 h-4 mr-2" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* 成功消息 */}
      {successMessage && (
        <div className="mb-4 p-3 bg-green-900/20 border border-green-500/20 rounded-lg">
          <div className="flex items-center text-green-400">
            <CheckCircle2 className="w-4 h-4 mr-2" />
            <span className="text-sm">{successMessage}</span>
          </div>
        </div>
      )}

      {/* 配置表单 */}
      <div className="space-y-4">
        {/* Sample Every */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Sample Every (steps)
            <span className="text-red-400 ml-1">*</span>
          </label>
          <input
            type="number"
            min="1"
            value={formConfig.sample_every}
            onChange={(e) => setFormConfig({
              ...formConfig,
              sample_every: parseInt(e.target.value) || 1
            })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            placeholder="e.g., 100"
          />
          <p className="text-xs text-gray-500 mt-1">
            How often to generate sample images during training (in training steps)
          </p>
        </div>

        {/* Save Every */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Save Every (steps)
            <span className="text-gray-500 ml-1">- Optional</span>
          </label>
          <input
            type="number"
            min="1"
            value={formConfig.save_every || ''}
            onChange={(e) => setFormConfig({
              ...formConfig,
              save_every: e.target.value ? parseInt(e.target.value) : null
            })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            placeholder="Leave empty to use config default"
          />
          <p className="text-xs text-gray-500 mt-1">
            How often to save model checkpoints. Leave empty to use original config.
          </p>
        </div>

        {/* Log Every */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Log Every (steps)
            <span className="text-gray-500 ml-1">- Optional</span>
          </label>
          <input
            type="number"
            min="1"
            value={formConfig.log_every || ''}
            onChange={(e) => setFormConfig({
              ...formConfig,
              log_every: e.target.value ? parseInt(e.target.value) : null
            })}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            placeholder="Leave empty to use config default"
          />
          <p className="text-xs text-gray-500 mt-1">
            How often to log metrics to tensorboard. Leave empty to use original config.
          </p>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex space-x-3 mt-6">
        <button
          onClick={saveConfig}
          disabled={saving || !hasChanges()}
          className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
        
        <button
          onClick={resetForm}
          disabled={!hasChanges()}
          className="flex items-center px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-gray-300 rounded-lg transition-colors"
        >
          Reset
        </button>
      </div>

      {/* 说明文字 */}
      <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/20 rounded-lg">
        <p className="text-xs text-blue-300">
          <strong>Note:</strong> Changes will take effect within 10 training steps. 
          The training process checks this configuration every 10 steps to avoid frequent file I/O.
        </p>
      </div>
    </div>
  );
};

export default DynamicConfigPanel;