import os
import json
import yaml
from typing import Dict, Any, Optional
import time

class DynamicConfig:
    """
    动态配置管理器，支持训练过程中热重载配置
    """
    
    def __init__(self, job_name: str, save_root: str):
        self.job_name = job_name
        self.save_root = save_root
        self.config_file = os.path.join(save_root, 'dynamic_config.yaml')
        self.last_modified = 0
        self.config_cache = {}
        
        # 创建默认配置文件
        self.ensure_config_file()
    
    def ensure_config_file(self):
        """确保配置文件存在，如果不存在则创建默认配置"""
        if not os.path.exists(self.config_file):
            default_config = {
                'sample_every': 100,
                'save_every': None,  # None表示不修改原有设置
                'log_every': None,
                'last_updated': time.time()
            }
            self.save_config(default_config)
    
    def save_config(self, config: Dict[str, Any]):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            print(f"Dynamic config saved to: {self.config_file}")
        except Exception as e:
            print(f"Warning: Failed to save dynamic config: {e}")
    
    def load_config(self) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            if not os.path.exists(self.config_file):
                self.ensure_config_file()
                
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                return config
        except Exception as e:
            print(f"Warning: Failed to load dynamic config: {e}")
            return {}
    
    def check_and_update(self) -> Dict[str, Any]:
        """检查配置文件是否有更新，如果有则返回新配置"""
        try:
            if not os.path.exists(self.config_file):
                return {}
                
            current_modified = os.path.getmtime(self.config_file)
            
            # 如果文件没有被修改，返回缓存的配置
            if current_modified <= self.last_modified:
                return self.config_cache
            
            # 文件有更新，重新加载
            new_config = self.load_config()
            self.last_modified = current_modified
            self.config_cache = new_config
            
            print(f"Dynamic config updated at step: {new_config}")
            return new_config
            
        except Exception as e:
            print(f"Warning: Failed to check dynamic config: {e}")
            return self.config_cache
    
    def get_sample_every(self, default: int) -> int:
        """获取当前的采样间隔设置"""
        config = self.check_and_update()
        sample_every = config.get('sample_every', default)
        
        # 确保是有效的正整数
        if isinstance(sample_every, int) and sample_every > 0:
            return sample_every
        return default
    
    def get_save_every(self, default: Optional[int]) -> Optional[int]:
        """获取当前的保存间隔设置"""
        config = self.check_and_update()
        save_every = config.get('save_every', default)
        
        if save_every is None:
            return default
        if isinstance(save_every, int) and save_every > 0:
            return save_every
        return default
    
    def get_log_every(self, default: Optional[int]) -> Optional[int]:
        """获取当前的日志间隔设置"""
        config = self.check_and_update()
        log_every = config.get('log_every', default)
        
        if log_every is None:
            return default
        if isinstance(log_every, int) and log_every > 0:
            return log_every
        return default
    
    def update_sample_every(self, new_value: int):
        """更新采样间隔设置"""
        if not isinstance(new_value, int) or new_value <= 0:
            raise ValueError(f"sample_every must be a positive integer, got {new_value}")
        
        config = self.load_config()
        config['sample_every'] = new_value
        config['last_updated'] = time.time()
        self.save_config(config)
        
    def get_config_file_path(self) -> str:
        """获取配置文件路径"""
        return self.config_file