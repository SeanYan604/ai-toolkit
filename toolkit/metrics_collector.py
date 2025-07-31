import os
import sqlite3
import json
import threading
from datetime import datetime
from typing import Dict, Optional, List, Any
from collections import OrderedDict

import torch

class LossCollector:
    """
    训练指标收集器，用于收集和存储训练过程中的loss、学习率等指标
    """
    
    def __init__(self, job_id: str, db_path: str = None):
        """
        初始化指标收集器
        
        Args:
            job_id: 训练任务ID
            db_path: 数据库路径，如果为None则使用默认路径
        """
        self.job_id = job_id
        self.db_path = db_path or self._get_default_db_path()
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_size = 10  # 批量写入优化
        self.lock = threading.Lock()  # 线程安全
        
        # 确保数据库表存在
        self._ensure_table_exists()
    
    def _get_default_db_path(self) -> str:
        """获取默认数据库路径"""
        # 尝试找到项目根目录下的数据库
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # 上一级目录
        db_path = os.path.join(project_root, "aitk_db.db")
        
        if not os.path.exists(db_path):
            # 如果根目录没有，尝试ui目录下的数据库
            ui_db_path = os.path.join(project_root, "ui", "aitk_db.db")
            if os.path.exists(ui_db_path):
                return ui_db_path
        
        return db_path
    
    def _ensure_table_exists(self):
        """确保TrainingMetrics表存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='TrainingMetrics'
            """)
            
            if not cursor.fetchone():
                # 如果表不存在，创建它
                cursor.execute("""
                    CREATE TABLE TrainingMetrics (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        step INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        value REAL NOT NULL
                    )
                """)
                
                # 创建索引
                cursor.execute("""
                    CREATE INDEX idx_metrics_job_step 
                    ON TrainingMetrics(job_id, step)
                """)
                cursor.execute("""
                    CREATE INDEX idx_metrics_job_type_name 
                    ON TrainingMetrics(job_id, metric_type, metric_name)
                """)
                
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            print(f"Warning: Could not ensure TrainingMetrics table exists: {e}")
    
    def log_step_metrics(self, step: int, loss_dict: OrderedDict, 
                        learning_rate: float, **kwargs):
        """
        记录单步训练指标
        
        Args:
            step: 训练步数
            loss_dict: loss字典，包含各种loss值
            learning_rate: 学习率
            **kwargs: 其他指标 (如gpu_memory, speed等)
        """
        timestamp = datetime.now().isoformat()
        
        with self.lock:
            # 处理loss数据
            for key, value in loss_dict.items():
                if isinstance(value, (int, float)) and not (isinstance(value, float) and (value != value)):  # 排除NaN
                    # 清理key中的特殊字符以生成安全的ID
                    safe_key = key.replace('/', '_').replace(' ', '_').replace('-', '_')
                    self.buffer.append({
                        'id': f"{self.job_id}_{step}_loss_{safe_key}",
                        'job_id': self.job_id,
                        'step': step,
                        'timestamp': timestamp,
                        'metric_type': 'loss',
                        'metric_name': key,
                        'value': float(value)
                    })
            
            # 记录学习率
            if isinstance(learning_rate, (int, float)) and not (isinstance(learning_rate, float) and (learning_rate != learning_rate)):
                self.buffer.append({
                    'id': f"{self.job_id}_{step}_lr",
                    'job_id': self.job_id,
                    'step': step,
                    'timestamp': timestamp,
                    'metric_type': 'learning_rate',
                    'metric_name': 'lr',
                    'value': float(learning_rate)
                })
            
            # 处理额外指标
            for key, value in kwargs.items():
                if value is not None:
                    try:
                        if isinstance(value, (int, float)) and not (isinstance(value, float) and (value != value)):
                            self.buffer.append({
                                'id': f"{self.job_id}_{step}_system_{key}",
                                'job_id': self.job_id,
                                'step': step,
                                'timestamp': timestamp,
                                'metric_type': 'system',
                                'metric_name': key,
                                'value': float(value)
                            })
                        elif isinstance(value, str) and len(value) < 100:  # 限制字符串长度
                            # 对于字符串值，我们可以存储为特殊的metric
                            self.buffer.append({
                                'id': f"{self.job_id}_{step}_info_{key}",
                                'job_id': self.job_id,
                                'step': step,
                                'timestamp': timestamp,
                                'metric_type': 'info',
                                'metric_name': key,
                                'value': hash(value) % 1000000  # 简单hash作为数值
                            })
                    except (ValueError, TypeError):
                        # 忽略无法转换的值
                        continue
            
            # 批量写入优化
            if len(self.buffer) >= self.buffer_size:
                self.flush()
    
    def flush(self):
        """批量写入数据库"""
        if not self.buffer:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 批量插入或替换
            cursor.executemany("""
                INSERT OR REPLACE INTO TrainingMetrics 
                (id, job_id, step, timestamp, metric_type, metric_name, value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [(
                item['id'], item['job_id'], item['step'], item['timestamp'],
                item['metric_type'], item['metric_name'], item['value']
            ) for item in self.buffer])
            
            conn.commit()
            conn.close()
            self.buffer.clear()
            
        except Exception as e:
            print(f"Error writing metrics to database: {e}")
    
    def get_gpu_memory_usage(self) -> Optional[float]:
        """获取GPU内存使用情况 (GB)"""
        try:
            if torch.cuda.is_available():
                return torch.cuda.memory_allocated() / (1024**3)
        except Exception:
            pass
        return None
    
    def log_step_with_auto_metrics(self, step: int, loss_dict: OrderedDict, 
                                  learning_rate: float, speed_string: str = None):
        """
        记录单步指标，自动收集GPU内存等系统指标
        
        Args:
            step: 训练步数
            loss_dict: loss字典
            learning_rate: 学习率
            speed_string: 训练速度字符串
        """
        extra_metrics = {}
        
        # 自动收集GPU内存
        gpu_memory = self.get_gpu_memory_usage()
        if gpu_memory is not None:
            extra_metrics['gpu_memory_gb'] = gpu_memory
        
        # 处理速度字符串
        if speed_string:
            extra_metrics['speed_info'] = speed_string
        
        self.log_step_metrics(step, loss_dict, learning_rate, **extra_metrics)
    
    def cleanup(self):
        """清理资源，确保所有数据都被写入"""
        with self.lock:
            self.flush()
    
    def __del__(self):
        """确保缓冲区数据被写入"""
        try:
            self.cleanup()
        except Exception:
            pass  # 避免析构函数抛出异常


class MetricsManager:
    """
    指标管理器，管理多个LossCollector实例
    """
    
    _instance = None
    _collectors: Dict[str, LossCollector] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_collector(cls, job_id: str, db_path: str = None) -> LossCollector:
        """获取或创建指标收集器"""
        if job_id not in cls._collectors:
            cls._collectors[job_id] = LossCollector(job_id, db_path)
        return cls._collectors[job_id]
    
    @classmethod
    def cleanup_collector(cls, job_id: str):
        """清理指定的收集器"""
        if job_id in cls._collectors:
            cls._collectors[job_id].cleanup()
            del cls._collectors[job_id]
    
    @classmethod
    def cleanup_all(cls):
        """清理所有收集器"""
        for collector in cls._collectors.values():
            collector.cleanup()
        cls._collectors.clear()