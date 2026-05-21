# 模型服务说明

本项目不负责部署模型服务本身。

你需要先自己准备一个本地视觉模型服务，并提供 OpenAI 兼容接口。
可以是 OMLX、Ollama，或任何兼容实现。

本项目默认模型名：

`Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4`

## 需要配的关键项

- `PHOTOS_AI_API_URL`：完整接口地址（含 `/v1/chat/completions`）
- `PHOTOS_AI_API_KEY`：接口密钥
- `PHOTOS_AI_MODEL`：模型名

## 示例

```env
PHOTOS_AI_API_URL=http://127.0.0.1:8001/v1/chat/completions
PHOTOS_AI_API_KEY=ggg123
PHOTOS_AI_MODEL=Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4
```
