# Loss Chart 功能设置指南

本文档指导您如何设置和使用新的loss折线图功能。

## 🚀 快速设置

### 1. 更新数据库和依赖

```bash
cd ai-toolkit/ui

# 安装新的图表依赖
npm install

# 更新数据库schema和生成Prisma客户端
npm run update_db

# 构建并启动UI
npm run build_and_start
```

### 2. 启动训练

启动任何训练任务，系统将自动开始收集metrics数据：

```bash
cd ai-toolkit
python run.py config/your_training_config.yaml
```

### 3. 查看Loss图表

1. 打开浏览器访问 `http://localhost:6006`
2. 进入 Jobs 页面
3. 点击任意训练任务进入详情页面  
4. 点击 **"Metrics"** 标签页
5. 查看实时loss变化趋势

## 📊 功能特性

### 图表功能
- ✅ **实时更新**: 每10秒自动刷新数据
- ✅ **多指标显示**: 同时显示多种loss类型
- ✅ **交互式操作**: 缩放、悬停查看详细值
- ✅ **坐标轴切换**: 线性/对数坐标轴
- ✅ **统计信息**: 显示最新值和总步数

### 数据收集
- ✅ **自动收集**: 训练过程中自动记录loss、学习率、GPU内存
- ✅ **高性能**: 批量写入，不影响训练速度
- ✅ **容错设计**: metrics收集失败不会中断训练
- ✅ **历史保存**: 所有数据永久保存在数据库中

## 🛠️ 故障排除

### 问题1: 图表显示"No training data available"
**原因**: 数据库中没有对应job的metrics数据
**解决方案**: 
1. 确认训练已经开始并运行了几个step
2. 检查job名称是否正确
3. 查看训练日志是否有metrics收集错误

### 问题2: 图表显示"Error loading training metrics"  
**原因**: API请求失败或数据库连接问题
**解决方案**:
1. 检查数据库文件是否存在: `ai-toolkit/aitk_db.db`
2. 确认UI服务器正在运行
3. 在浏览器开发者工具中检查网络请求错误

### 问题3: 新训练任务没有收集数据
**原因**: MetricsCollector初始化失败
**解决方案**:
1. 检查训练日志中是否有 "Failed to initialize metrics collector" 警告
2. 确认数据库文件权限正确
3. 重启训练任务

## 📈 使用技巧

### 1. 查看特定指标
- 在图表上方的checkbox中选择/取消选择要显示的metrics
- 建议同时显示不超过5个指标以保持清晰度

### 2. 优化性能
- 对于长时间训练，图表会自动降采样显示以提高性能
- 可以通过缩放功能查看特定时间段的详细数据

### 3. 数据导出
- 所有数据存储在SQLite数据库中，可以使用SQL查询导出
- 数据库路径: `ai-toolkit/aitk_db.db`
- 表名: `TrainingMetrics`

## 🔧 高级配置

### 自定义刷新间隔
修改 `LossChart` 组件的 `refreshInterval` 属性（毫秒）:

```tsx
<LossChart jobId={job.id} refreshInterval={5000} /> // 5秒刷新
```

### 自定义图表高度
```tsx
<LossChart jobId={job.id} height={600} /> // 600px高度
```

### 数据清理
定期清理旧数据以节省存储空间:

```bash
# 删除30天前的数据
curl -X DELETE "http://localhost:6006/api/metrics?jobId=YOUR_JOB_ID&olderThanDays=30"
```

## 🏗️ 架构说明

### 数据流程
```
训练进程 → LossCollector → SQLite数据库 → REST API → React图表组件
```

### 文件结构
```
ai-toolkit/
├── toolkit/metrics_collector.py       # 数据收集器
├── ui/prisma/schema.prisma            # 数据库schema
├── ui/src/app/api/metrics/            # API端点
├── ui/src/components/LossChart.tsx    # 图表组件
└── jobs/process/BaseSDTrainProcess.py # 训练集成
```

## 📝 更新日志

### v1.0.0 (2025-01-XX)
- ✅ 添加基础loss图表功能
- ✅ 实时数据更新
- ✅ 多指标支持
- ✅ 训练进程自动集成

---

如有问题，请查看训练日志或联系开发团队。