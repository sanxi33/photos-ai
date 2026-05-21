# 发布检查清单

- [ ] README 的 4 步命令全部实跑通过
- [ ] `.env.example` 字段和代码读取字段一致
- [ ] `./scripts/doctor.sh` 输出通过或仅保留可接受警告
- [ ] `./scripts/run.sh --oneshot` 能跑完整一张
- [ ] `./scripts/run.sh --daemon` 能正常启动与 Ctrl+C 退出
- [ ] `./scripts/launchd.sh install/status/stop/start/uninstall` 都通过
- [ ] 仓库内无 `state*.json`、`logs/*`、`.env`、`.venv/` 等私密或本地产物
- [ ] License、模型说明、故障排查已更新
