# Photos AI（macOS）

用本地大模型给 `Photos.app` 照片自动写描述和关键词。

## 第 1 步：一键安装环境（curl）

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/photos-ai/main/scripts/bootstrap.sh | bash
```

如果你是在本地仓库里运行，也可以直接：

```bash
./scripts/bootstrap.sh
```

## 第 2 步：填写配置

```bash
cp .env.example .env
```

然后编辑 `.env`，至少确认这几项：

- `PHOTOS_AI_API_URL`：你的本地 OpenAI 兼容接口地址
- `PHOTOS_AI_API_KEY`：接口密钥
- `PHOTOS_AI_MODEL`：默认是 `Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4`

## 第 3 步：选择运行方式

先测试一张：

```bash
./scripts/run.sh --oneshot
```

常驻守护（空闲时自动处理）：

```bash
./scripts/run.sh --daemon
```

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

## 先决条件

- macOS
- `Photos.app` 可访问，首次运行时允许权限请求
- 本地 OpenAI 兼容视觉模型服务（默认按 `.env` 的地址和模型名）

## 故障排查

先跑体检：

```bash
./scripts/doctor.sh
```

常见问题：

- 提示缺少 `.env`：先执行 `cp .env.example .env`
- 接口连不上：确认模型服务已启动，端口与 `PHOTOS_AI_API_URL` 一致
- 写回失败：确认系统已授权终端/运行器控制 Photos

## 主要文件

- `photos_daemon.py`：批量守护处理
- `photo_analyze.py`：最小链路测试
- `runtime_config.py`：统一读取 `.env` 配置
- `scripts/bootstrap.sh`：一键安装
- `scripts/run.sh`：统一运行入口
- `scripts/doctor.sh`：环境体检
- `scripts/launchd.sh`：开机自启管理
