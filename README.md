# Photos AI（macOS）

一句话：这是一个给 `Photos.app` 自动加描述和关键词的工具；它会读取你的照片，调用你本地已部署好的视觉模型生成文字，再写回相册元数据；你需要先准备一个 OpenAI 兼容接口的本地视觉模型服务（例如你自己用 OMLX 或 Ollama 搭好）。

## 先决条件（先做这个）

- macOS
- 你已经有可用的本地视觉模型服务（OpenAI 兼容接口）
- 已知道模型接口地址、密钥、模型名
- `Photos.app` 首次运行时允许权限请求

注意：本项目脚本**不负责部署模型服务本身**，只负责本工具的环境安装和运行。

## 第 1 步：一键安装本工具环境（curl）

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/photos-ai/main/scripts/bootstrap.sh | bash
```

说明：

- 如果你当前目录已经是项目目录，脚本会直接在当前目录安装依赖。
- 如果你不是在项目目录执行，脚本会：
  1) 自动 `git clone` 仓库
  2) 默认安装到 `~/photos-ai`
- 你也可以手动指定：
  - `PHOTOS_AI_REPO_URL`：仓库地址
  - `PHOTOS_AI_INSTALL_DIR`：安装目录

示例：

```bash
PHOTOS_AI_REPO_URL=https://github.com/yourname/photos-ai.git PHOTOS_AI_INSTALL_DIR=$HOME/photos-ai curl -fsSL https://raw.githubusercontent.com/yourname/photos-ai/main/scripts/bootstrap.sh | bash
```

## 第 2 步：填写配置（.env）

先复制模板：

```bash
cp .env.example .env
```

`.env` 是隐藏文件，Finder 默认不显示。你可以用下面任一方式编辑：

```bash
open -e .env
# 或
nano .env
```

至少确认这几项：

- `PHOTOS_AI_API_URL`：你的模型接口地址（含 `/v1/chat/completions`）
- `PHOTOS_AI_API_KEY`：接口密钥
- `PHOTOS_AI_MODEL`：模型名（默认 `Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4`）

## 第 3 步：选择运行方式

先做测试（推荐先跑这条）：

```bash
./scripts/run.sh --oneshot
```

`--oneshot` 含义：

- 只处理 **1 张未处理照片**，然后退出
- 用于验证“接口通不通、模型能不能返回、能不能写回 Photos”
- 不是批量模式

持续守护模式：

```bash
./scripts/run.sh --daemon
```

`--daemon` 含义：

- 长期运行
- 只有在你空闲时才继续处理更多照片

## 第 4 步（可选）：开机自动启动 daemon

```bash
./scripts/launchd.sh install
```

常用管理命令：

```bash
./scripts/launchd.sh status
./scripts/launchd.sh stop
./scripts/launchd.sh start
./scripts/launchd.sh uninstall
```

## 故障排查

先跑体检：

```bash
./scripts/doctor.sh
```

常见问题：

- 提示缺少 `.env`：先执行 `cp .env.example .env`
- 找不到 `.env`：它是隐藏文件，用 `open -e .env` 或 `nano .env` 打开
- 接口连不上：确认模型服务已启动，端口与 `PHOTOS_AI_API_URL` 一致
- 写回失败：确认系统已授权终端/运行器控制 Photos

## 主要文件

- `photos_daemon.py`：批量守护处理
- `photo_analyze.py`：最小链路测试
- `runtime_config.py`：统一读取 `.env` 配置
- `scripts/bootstrap.sh`：一键安装本工具环境
- `scripts/run.sh`：统一运行入口
- `scripts/doctor.sh`：环境体检
- `scripts/launchd.sh`：开机自启管理
