# 模型配置说明

本项目默认模型：

`Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4`

你可以在 `.env` 里改 `PHOTOS_AI_MODEL`，但官方默认就是上面这个。

## 需要配的关键项

- `PHOTOS_AI_API_URL`：本地 OpenAI 兼容接口地址（含 `/v1/chat/completions`）
- `PHOTOS_AI_API_KEY`：接口密钥
- `PHOTOS_AI_MODEL`：模型名

## 示例

```env
PHOTOS_AI_API_URL=http://127.0.0.1:8001/v1/chat/completions
PHOTOS_AI_API_KEY=ggg123
PHOTOS_AI_MODEL=Qwen3-VL-8B-NSFW-Caption-V4.5-mxfp4
```
