#!/usr/bin/env python3
"""
Dynamic Config CLI Tool

用于管理训练过程中的动态配置的命令行工具

使用示例:
    python scripts/dynamic_config_cli.py list output/
    python scripts/dynamic_config_cli.py get my_training_job
    python scripts/dynamic_config_cli.py set my_training_job sample_every 50
    python scripts/dynamic_config_cli.py set my_training_job save_every 1000
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class DynamicConfigCLI:
    def __init__(self, training_folder: str = "output"):
        self.training_folder = Path(training_folder)
        
    def list_jobs(self) -> None:
        """列出所有可用的训练任务"""
        if not self.training_folder.exists():
            print(f"Training folder not found: {self.training_folder}")
            return
            
        jobs = []
        for job_dir in self.training_folder.iterdir():
            if job_dir.is_dir():
                config_file = job_dir / "dynamic_config.yaml"
                has_config = config_file.exists()
                jobs.append({
                    'name': job_dir.name,
                    'path': str(job_dir),
                    'has_config': has_config,
                    'config_path': str(config_file)
                })
        
        if not jobs:
            print("No training jobs found.")
            return
            
        print(f"Found {len(jobs)} training job(s):")
        print("-" * 80)
        for job in jobs:
            status = "✓ Has config" if job['has_config'] else "✗ No config"
            print(f"  {job['name']:<30} {status}")
            print(f"    Path: {job['path']}")
            if job['has_config']:
                print(f"    Config: {job['config_path']}")
            print()
    
    def get_config(self, job_name: str) -> Optional[Dict[str, Any]]:
        """获取指定任务的配置"""
        config_file = self.training_folder / job_name / "dynamic_config.yaml"
        
        if not config_file.exists():
            return None
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error reading config file: {e}")
            return None
    
    def save_config(self, job_name: str, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        job_dir = self.training_folder / job_name
        if not job_dir.exists():
            print(f"Job directory not found: {job_dir}")
            return False
            
        config_file = job_dir / "dynamic_config.yaml"
        
        try:
            # 添加时间戳
            import time
            config['last_updated'] = time.time()
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            print(f"Configuration saved to: {config_file}")
            return True
        except Exception as e:
            print(f"Error saving config file: {e}")
            return False
    
    def show_config(self, job_name: str) -> None:
        """显示指定任务的配置"""
        config = self.get_config(job_name)
        
        if config is None:
            print(f"No dynamic config found for job: {job_name}")
            config_file = self.training_folder / job_name / "dynamic_config.yaml"
            print(f"Expected location: {config_file}")
            return
        
        print(f"Dynamic configuration for job: {job_name}")
        print("-" * 50)
        
        # 格式化显示配置
        for key, value in config.items():
            if key == 'last_updated' and value:
                import time
                formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))
                print(f"  {key:<15}: {formatted_time}")
            elif value is None:
                print(f"  {key:<15}: (use default)")
            else:
                print(f"  {key:<15}: {value}")
        
        config_file = self.training_folder / job_name / "dynamic_config.yaml"
        print(f"\nConfig file: {config_file}")
    
    def set_config(self, job_name: str, key: str, value: Any) -> None:
        """设置配置项"""
        # 验证配置键
        valid_keys = ['sample_every', 'save_every', 'log_every']
        if key not in valid_keys:
            print(f"Invalid config key: {key}")
            print(f"Valid keys: {', '.join(valid_keys)}")
            return
        
        # 加载现有配置
        config = self.get_config(job_name) or {}
        
        # 处理值
        if value.lower() in ['none', 'null', '']:
            processed_value = None
        else:
            try:
                processed_value = int(value)
                if processed_value <= 0:
                    print(f"Value must be a positive integer or 'none', got: {value}")
                    return
            except ValueError:
                print(f"Invalid value: {value}. Must be a positive integer or 'none'.")
                return
        
        # 更新配置
        old_value = config.get(key, 'not set')
        config[key] = processed_value
        
        # 保存配置
        if self.save_config(job_name, config):
            print(f"Updated {key}: {old_value} → {processed_value}")
            
            if key == 'sample_every':
                print("\n💡 Note: Changes will take effect within 10 training steps.")
    
    def create_default_config(self, job_name: str) -> None:
        """为指定任务创建默认配置"""
        job_dir = self.training_folder / job_name
        if not job_dir.exists():
            print(f"Job directory not found: {job_dir}")
            return
        
        default_config = {
            'sample_every': 100,
            'save_every': None,
            'log_every': None,
        }
        
        if self.save_config(job_name, default_config):
            print(f"Created default configuration for job: {job_name}")

def main():
    parser = argparse.ArgumentParser(
        description="Dynamic Config CLI Tool - Manage training configurations during runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                                    # List all training jobs
  %(prog)s get my_training_job                     # Show config for a job
  %(prog)s set my_training_job sample_every 50     # Change sample interval to 50 steps
  %(prog)s set my_training_job save_every 1000     # Change save interval to 1000 steps  
  %(prog)s set my_training_job sample_every none   # Disable auto sampling
  %(prog)s create my_training_job                  # Create default config file
        """
    )
    
    parser.add_argument(
        '--training-folder', '-t',
        default='output',
        help='Training folder path (default: output)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List all training jobs')
    
    # get command
    get_parser = subparsers.add_parser('get', help='Show configuration for a job')
    get_parser.add_argument('job_name', help='Training job name')
    
    # set command
    set_parser = subparsers.add_parser('set', help='Set a configuration value')
    set_parser.add_argument('job_name', help='Training job name')
    set_parser.add_argument('key', help='Configuration key (sample_every, save_every, log_every)')
    set_parser.add_argument('value', help='Configuration value (positive integer or "none")')
    
    # create command
    create_parser = subparsers.add_parser('create', help='Create default configuration file')
    create_parser.add_argument('job_name', help='Training job name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = DynamicConfigCLI(args.training_folder)
    
    if args.command == 'list':
        cli.list_jobs()
    elif args.command == 'get':
        cli.show_config(args.job_name)
    elif args.command == 'set':
        cli.set_config(args.job_name, args.key, args.value)
    elif args.command == 'create':
        cli.create_default_config(args.job_name)

if __name__ == '__main__':
    main()