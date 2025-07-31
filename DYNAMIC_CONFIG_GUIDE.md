# 🔧 动态配置功能使用指南

## 📖 概述

这个功能允许您在训练过程中**实时修改**采样间隔、保存间隔等参数，无需重启训练！

### ✨ 主要特性
- 🔄 **实时生效**: 更改在10个训练步骤内生效
- 🎯 **采样控制**: 动态调整测试图片生成频率
- 💾 **保存控制**: 动态调整模型保存频率
- 📊 **日志控制**: 动态调整日志记录频率
- 🌐 **多种接口**: Web UI + 命令行工具
- 🛡️ **安全设计**: 配置错误不会影响训练进程

---

## 🚀 快速开始

### 方法1: Web UI（推荐）

1. **启动训练**:
   ```bash
   cd ai-toolkit
   python run.py config/your_config.yaml
   ```

2. **打开Web界面**:
   - 访问 `http://localhost:6006`
   - 进入 Jobs → [选择训练任务] → **Settings** 标签页

3. **修改配置**:
   - 调整 "Sample Every" 值（如从100改为50）
   - 点击 "Save Changes"
   - 配置将在10步内生效！

### 方法2: 命令行工具

```bash
# 查看所有训练任务
python scripts/dynamic_config_cli.py list

# 查看当前配置
python scripts/dynamic_config_cli.py get my_training_job

# 修改采样间隔为50步
python scripts/dynamic_config_cli.py set my_training_job sample_every 50

# 修改保存间隔为1000步
python scripts/dynamic_config_cli.py set my_training_job save_every 1000
```

---

## 📋 详细功能说明

### 🎛️ 可配置参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `sample_every` | 生成测试图片的间隔步数 | 100 | 50, 200 |
| `save_every` | 保存模型的间隔步数 | (使用原配置) | 500, 1000 |
| `log_every` | 记录日志的间隔步数 | (使用原配置) | 10, 100 |

### 🔄 生效机制

- **检查频率**: 训练进程每10步检查一次配置文件
- **变更通知**: 配置变更时会在训练日志中显示提示
- **容错设计**: 配置文件错误不会中断训练

---

## 🌐 Web UI 使用教程

### 界面布局

```
┌─────────────────────────────────────────────────────────┐
│ Job: my_training_job                    [Actions]       │
├─────────────────────────────────────────────────────────┤
│ [Overview] [Metrics] [Settings] [Samples]              │
├─────────────────────────────────────────────────────────┤
│ Dynamic Training Settings                   [Refresh]   │
│                                                         │
│ 📄 Config file: /path/to/dynamic_config.yaml           │
│ ✓ File exists  Last updated: 2025-01-XX XX:XX:XX       │
│                                                         │
│ Sample Every (steps) *                                  │
│ [100                               ]                    │
│ How often to generate sample images during training     │
│                                                         │
│ Save Every (steps) - Optional                           │
│ [                                  ]                    │
│ Leave empty to use config default                       │
│                                                         │
│ [Save Changes] [Reset]                                  │
│                                                         │
│ 💡 Changes will take effect within 10 training steps   │
└─────────────────────────────────────────────────────────┘
```

### 操作步骤

1. **访问设置页面**:
   - 训练开始后，打开 `http://localhost:6006`
   - 选择对应的训练任务
   - 点击 "Settings" 标签页

2. **修改配置**:
   - 在 "Sample Every" 输入框中输入新值
   - 其他参数可选填（留空使用原配置）
   - 点击 "Save Changes" 保存

3. **监控生效**:
   - 界面会显示保存成功的消息
   - 训练日志会显示配置变更提示
   - 新的采样间隔将在10步内生效

---

## 💻 命令行工具详解

### 安装和使用

```bash
# 给脚本添加执行权限（Linux/Mac）
chmod +x scripts/dynamic_config_cli.py

# 查看帮助
python scripts/dynamic_config_cli.py --help
```

### 常用命令

#### 1. 列出所有训练任务
```bash
python scripts/dynamic_config_cli.py list

# 输出示例：
# Found 2 training job(s):
# --------------------------------------------------------------------------------
#   my_flux_lora              ✓ Has config
#     Path: /path/to/output/my_flux_lora
#     Config: /path/to/output/my_flux_lora/dynamic_config.yaml
#
#   another_training          ✗ No config
#     Path: /path/to/output/another_training
```

#### 2. 查看配置
```bash
python scripts/dynamic_config_cli.py get my_flux_lora

# 输出示例：
# Dynamic configuration for job: my_flux_lora
# --------------------------------------------------
#   sample_every   : 50
#   save_every     : (use default)
#   log_every      : (use default)
#   last_updated   : 2025-01-15 14:30:25
#
# Config file: /path/to/output/my_flux_lora/dynamic_config.yaml
```

#### 3. 修改配置
```bash
# 修改采样间隔
python scripts/dynamic_config_cli.py set my_flux_lora sample_every 30

# 修改保存间隔
python scripts/dynamic_config_cli.py set my_flux_lora save_every 800

# 禁用某个设置（使用原配置）
python scripts/dynamic_config_cli.py set my_flux_lora save_every none
```

#### 4. 创建默认配置
```bash
python scripts/dynamic_config_cli.py create my_new_training
```

---

## 📂 配置文件格式

配置文件路径: `output/[训练任务名]/dynamic_config.yaml`

```yaml
# 采样间隔（必填）
sample_every: 100

# 保存间隔（可选，null表示使用原配置）
save_every: null

# 日志间隔（可选，null表示使用原配置）  
log_every: null

# 最后更新时间（自动生成）
last_updated: 1705312225.123
```

### 手动编辑配置文件

您也可以直接编辑YAML文件：

```bash
# 找到配置文件
ls output/your_job_name/dynamic_config.yaml

# 编辑文件
nano output/your_job_name/dynamic_config.yaml
```

**注意**: 手动编辑后，更改会在10步内自动生效。

---

## 🎯 实际应用场景

### 场景1: 调试阶段
```bash
# 开始时频繁采样查看效果
python scripts/dynamic_config_cli.py set my_job sample_every 10

# 效果满意后减少采样频率
python scripts/dynamic_config_cli.py set my_job sample_every 100
```

### 场景2: 长时间训练
```bash
# 前期频繁保存防止丢失
python scripts/dynamic_config_cli.py set my_job save_every 200

# 后期减少保存频率节省空间
python scripts/dynamic_config_cli.py set my_job save_every 1000
```

### 场景3: 性能优化
```bash
# 如果采样影响训练速度，可以临时禁用
python scripts/dynamic_config_cli.py set my_job sample_every 99999

# 或者减少日志频率
python scripts/dynamic_config_cli.py set my_job log_every 500
```

---

## 🔍 监控和日志

### 训练日志中的提示信息

当配置发生变化时，训练日志会显示：

```
Dynamic config: sample_every changed from 100 to 50 at step 1520
```

### Web UI 实时反馈

- ✅ **成功**: 绿色提示"Configuration updated successfully"
- ❌ **错误**: 红色提示具体错误信息
- 📄 **状态**: 显示配置文件路径和最后更新时间

---

## ⚠️ 注意事项和最佳实践

### ⚠️ 重要提醒

1. **参数验证**: 所有间隔参数必须是正整数
2. **生效延迟**: 更改在10个训练步骤内生效
3. **文件权限**: 确保训练进程有读写配置文件的权限
4. **备份重要**: 重要的长时间训练建议定期备份

### 🎯 最佳实践

#### 采样间隔设置建议
- **调试期**: 10-50步，快速查看效果
- **正式训练**: 100-500步，平衡效果和性能
- **长时间训练**: 500-1000步，减少文件数量

#### 保存间隔设置建议
- **短训练** (< 5000步): 200-500步
- **中等训练** (5000-20000步): 500-1000步  
- **长训练** (> 20000步): 1000-2000步

#### 性能优化建议
- 避免过于频繁的采样和保存
- 在训练稳定后适当减少监控频率
- 使用SSD存储可以提高文件操作性能

---

## 🛠️ 故障排除

### 常见问题

#### 1. 配置不生效
**症状**: 修改了配置但采样间隔没有变化

**解决方案**:
- 检查配置文件是否正确保存
- 确认训练进程正在运行
- 等待最多10个训练步骤
- 查看训练日志是否有错误提示

#### 2. 配置文件不存在
**症状**: Web UI显示 "File will be created when saved"

**解决方案**:
```bash
# 手动创建默认配置
python scripts/dynamic_config_cli.py create your_job_name

# 或者在Web UI中直接保存
```

#### 3. 权限错误
**症状**: 无法保存配置文件

**解决方案**:
```bash
# 检查目录权限
ls -la output/your_job_name/

# 修复权限（如果需要）
chmod 755 output/your_job_name/
```

#### 4. 训练日志报错
**症状**: 看到 "Failed to get dynamic sample_every" 警告

**解决方案**:
- 检查YAML文件格式是否正确
- 确认参数值是正整数
- 删除配置文件重新创建

### 调试技巧

#### 查看详细错误
```bash
# 测试配置文件格式
python -c "import yaml; print(yaml.safe_load(open('output/job/dynamic_config.yaml')))"

# 手动检查权限
ls -la output/your_job_name/dynamic_config.yaml
```

#### 重置配置
```bash
# 删除配置文件，训练将使用原始设置
rm output/your_job_name/dynamic_config.yaml

# 重新创建默认配置
python scripts/dynamic_config_cli.py create your_job_name
```

---

## 🚀 高级用法

### 批量管理

```bash
# 为所有训练任务设置相同的采样间隔
for job in output/*/; do
    job_name=$(basename "$job")
    python scripts/dynamic_config_cli.py set "$job_name" sample_every 200
done
```

### 自动化脚本

```bash
#!/bin/bash
# auto_adjust_sampling.sh

JOB_NAME="my_training"
STEP_FILE="output/$JOB_NAME/step.txt"

# 根据训练步数自动调整采样频率
if [ -f "$STEP_FILE" ]; then
    CURRENT_STEP=$(cat "$STEP_FILE")
    
    if [ "$CURRENT_STEP" -lt 1000 ]; then
        python scripts/dynamic_config_cli.py set "$JOB_NAME" sample_every 50
    elif [ "$CURRENT_STEP" -lt 5000 ]; then
        python scripts/dynamic_config_cli.py set "$JOB_NAME" sample_every 100
    else
        python scripts/dynamic_config_cli.py set "$JOB_NAME" sample_every 200
    fi
fi
```

### API 集成

如果您有自己的监控系统，可以直接调用Web API：

```bash
# 获取配置
curl "http://localhost:6006/api/dynamic-config?jobName=my_job"

# 更新配置
curl -X POST "http://localhost:6006/api/dynamic-config" \
  -H "Content-Type: application/json" \
  -d '{"jobName": "my_job", "config": {"sample_every": 150}}'
```

---

## 📈 性能影响分析

### CPU/IO 影响
- **配置检查**: 每10步进行一次文件检查，影响极小
- **文件操作**: 使用缓存机制，避免频繁读取
- **内存使用**: 增加 < 1MB

### 训练速度影响
- **正常情况**: 几乎无影响 (< 0.1%)
- **频繁更改**: 建议间隔 > 10步再次修改
- **大量任务**: 每个任务独立，无相互影响

---

通过这个动态配置功能，您可以更加灵活地控制训练过程，实时调整参数以获得最佳的训练效果！🎉