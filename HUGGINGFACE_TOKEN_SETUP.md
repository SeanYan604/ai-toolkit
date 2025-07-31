# HuggingFace Token 配置指南

## 概述

为了下载受限制的模型（如 FLUX.1-dev），您需要配置 HuggingFace token。本指南将帮助您完成配置。

## 🔑 获取 HuggingFace Token

1. 访问 [HuggingFace Settings](https://huggingface.co/settings/tokens)
2. 点击 "New token" 创建新的访问令牌
3. 选择权限类型：
   - **Read**: 足够下载模型
   - **Write**: 如果您需要上传模型
4. 复制生成的 token

## ⚙️ 配置方法

### 方法1: 环境变量（推荐）

在运行训练之前设置环境变量：

```bash
# 临时设置（当前会话有效）
export HF_TOKEN="hf_your_token_here"

# 或者使用另一个变量名
export HUGGING_FACE_HUB_TOKEN="hf_your_token_here"

# 然后运行训练
python run.py your_config.yaml
```

### 方法2: .env 文件

在项目根目录创建 `.env` 文件：

```bash
# .env
HF_TOKEN=hf_your_token_here
```

### 方法3: 系统级缓存

使用 HuggingFace CLI 登录（一次性设置）：

```bash
huggingface-cli login
```

输入您的 token，系统将缓存认证信息。

## 🚀 使用示例

配置完成后，运行训练：

```bash
# 使用环境变量
export HF_TOKEN="hf_your_token_here"
python run.py config/flux_dev_lora.yaml

# 或者直接在命令中设置
HF_TOKEN="hf_your_token_here" python run.py config/flux_dev_lora.yaml
```

## 📋 验证配置

运行时您将看到以下消息之一：

### ✅ 配置成功
```
🤗 Found HuggingFace token in environment, logging in...
✅ Successfully logged in to HuggingFace Hub
```

### 🔑 使用缓存凭据
```
⚠️  No HuggingFace token found in environment variables.
🔑 Using cached HuggingFace credentials
```

### ⚠️ 需要配置
```
⚠️  No HuggingFace token found in environment variables.
   Set HF_TOKEN or HUGGING_FACE_HUB_TOKEN to download private/gated models.
💡 Tip: Run 'huggingface-cli login' to cache your token, or set HF_TOKEN environment variable
```

## 🔒 安全提示

- **不要**将 token 提交到 Git 仓库
- 使用 `.env` 文件时，确保 `.env` 在 `.gitignore` 中
- 定期轮换您的 token
- 只给 token 必要的权限

## 🛠️ 故障排除

### 问题: "Repository not found" 错误
- 确保您的 token 有效
- 检查您是否已接受模型的许可条款（如 FLUX.1-dev）
- 验证模型名称是否正确

### 问题: Token 无效
- 检查 token 是否以 `hf_` 开头
- 确保 token 没有过期
- 重新生成新的 token

### 问题: 网络连接问题
- 检查网络连接
- 如果在中国，确保 `HF_ENDPOINT` 设置正确（已在代码中预配置）

## 📚 相关链接

- [HuggingFace Token 文档](https://huggingface.co/docs/hub/security-tokens)
- [FLUX.1-dev 模型页面](https://huggingface.co/black-forest-labs/FLUX.1-dev)
- [HuggingFace Hub Python API](https://huggingface.co/docs/huggingface_hub/index)