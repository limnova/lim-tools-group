# Claude / Codex 配置维护

脚本需要 Python 3.11+，只使用标准库。维护共享配置时先修改源文件，再执行同步。

## 维护入口

| 范围 | 维护源 | 同步目标 |
| --- | --- | --- |
| 项目 skills | `.agents/skills` | `.claude/skills` |
| 项目规则 | `AGENTS.md` | `CLAUDE.md` 通过 `@AGENTS.md` 导入 |
| 项目 MCP | 本机 `.mcp.json` | 本机 `.codex/config.toml` |
| 个人 skills | `~/.codex/skills` 的公开技能目录 | `~/.claude/skills` |
| 个人规则 | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` |
| 个人 MCP | `~/.codex/config.toml` 中清单指定的服务器 | `~/.claude.json` 的 `mcpServers` |

`.agents/sync.json` 维护个人 MCP 清单及项目 Claude 插件例外。
`frontend-design`、`skill-creator` 由已启用的 Claude 插件提供；其余项目技能复制到 Claude。
Codex 的 `.system`、浏览器/桌面运行时、插件缓存和客户端模型/权限设置由各宿主管理。

同步会更新维护源对应的文件，不删除目标目录额外文件。新增 Claude 个人技能时，
先将需要共享的内容纳入 Codex 维护源；直接修改兼容副本的内容会在下次同步时被覆盖并备份。
脚本不会从项目技能中擅自删除已有副本；孤立副本由 `check_skills.py` 报告后人工核对。

## 检查、应用与备份

```powershell
# 项目检查；有差异返回 1，配置错误返回 2，无差异返回 0
python scripts/sync_agent_config.py --check

# 同时检查个人配置
python scripts/sync_agent_config.py --personal --check

# 备份后应用项目及个人配置
python scripts/sync_agent_config.py --personal --apply
python scripts/check_skills.py

# 验证配置转换、环境变量、备份、并发修改保护和技能副本检测
python -m unittest discover -s scripts -p 'test_*.py' -v
```

备份位于 `~/.agents/backups/<时间戳>/`，`manifest.json` 对应原始绝对路径和备份文件。
恢复已有文件时按 manifest 将 `.bak` 复制回原路径；`backup: null` 表示当次新增文件，
撤销时先确认它此后没有新改动，再移除。备份可能包含本地凭据，应留在用户目录。
应用前会检查目标是否在计划生成后被修改；发现并发变化则停止，重新运行即可重新规划。
多文件更新若中途失败，先根据 manifest 核对，再恢复或重新同步。

## 项目 PostgreSQL MCP

首次配置时，将 `.mcp.example.json` 复制为 `.mcp.json`，并在本机设置
`LIM_TOOLS_DB_RO_PASSWORD`。可选变量为 `LIM_TOOLS_DB_HOST`、`LIM_TOOLS_DB_PORT`、
`LIM_TOOLS_DB_NAME`；默认分别为 `127.0.0.1`、`5432`、`limtools`。
若在连接 URI 中使用包含特殊字符的密码，应使用 URI 编码后的值。
模板使用 `limtools_ro` 用户以及 `--access-mode=restricted`。
本机 `.mcp.json`、生成的 `.codex/config.toml`、Claude 本地设置均已加入 `.gitignore`。

Claude 使用 `.mcp.json` 的环境变量展开；Codex 通过 `scripts/run_mcp.py`
读取相同配置并展开 `${VAR}` / `${VAR:-default}`。缺少必需变量时启动器只报告变量名，
不输出凭据或完整命令。启动器继承标准输入输出，保证 MCP 协议输出不混入日志。
生成的 Codex 配置带本机 Python 和仓库的绝对路径，移动仓库或 Python 后重新同步即可。

环境变量来自启动应用的进程。Windows 用户环境变量修改后，需重启 Claude/Codex 应用和终端；
仅新开应用内对话可能仍继承旧进程环境。必要时重新登录 Windows 后再启动。

## 2026-10-09 本机整理结果

- 19 个个人技能同步到 Claude；24 个项目兼容技能一致，另有 2 个 Claude 插件入口。
- 全局规则合并 MongoDB 脚本约定和 GitLab MCP 使用方式。
- 共享个人 MCP 为 `tapd`、`gitlab`、`github`；项目 MCP 为 `postgres`。
- 四个服务完成 MCP initialize 与 tools/list：分别返回 46、202、44、9 个工具。
  这验证启动和协议协商，不代表已验证每个远程 API 或数据库业务操作。
- PostgreSQL 验证时仅向测试子进程加载现有 Windows 用户密码变量，没有查询业务数据。
- CC Switch 数据库中的 MCP 启用标记与当前生效文件不同，且保留旧名 `glab`。
  本次以客户端实际配置为准，未直接改写 CC Switch 私有数据库；若以后从 CC Switch 应用配置，
  应重新检查实际配置和同步结果，避免旧状态覆盖本次整理。

官方格式说明：[Codex MCP](https://developers.openai.com/codex/mcp)、
[Claude MCP](https://code.claude.com/docs/en/mcp)、
[Claude 共享项目规则](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools)。
