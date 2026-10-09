# 仓库工作规则

本仓库聚合 `lim-tools-web` 与 `lim-tools-server` 两个 Git 子模块。

- 进入子仓库处理代码前，使用 [.agents/skills/nested-repository-router/SKILL.md](.agents/skills/nested-repository-router/SKILL.md) 定位目标 Git 根，并读取目标路径适用的规则。
- 处理 Go 代码时，使用 [.agents/skills/golang-how-to/SKILL.md](.agents/skills/golang-how-to/SKILL.md) 按任务选择技能。
- 跨仓库提交或更新子模块指针时，使用 [.agents/skills/submodule-aggregate-workflow/SKILL.md](.agents/skills/submodule-aggregate-workflow/SKILL.md)。
- `.agents/skills` 为项目技能的维护入口；`.claude/skills` 保留共享技能的兼容副本。修改公共技能后运行 `python scripts/sync_agent_config.py --apply`，再运行 `python scripts/check_skills.py`；插件例外维护在 `.agents/sync.json`。
- 整理本机 Claude/Codex 配置时，按 [配置维护说明](docs/agent-config.md) 操作；同步脚本默认只检查，`--personal` 才包含个人配置。

需要查询 PostgreSQL 时，优先使用 MCP server `postgres`（只读，RESTRICTED 模式，连 `limtools` 库）。
测试排错默认使用 namespace `portal`；只有用户明确要求或需要对比时才使用 `qa` 或 `auto`。
