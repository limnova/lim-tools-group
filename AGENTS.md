# 仓库工作规则

本仓库聚合 `lim-tools-web` 与 `lim-tools-server` 两个 Git 子模块。

- 进入子仓库处理代码前，使用 [.agents/skills/nested-repository-router/SKILL.md](.agents/skills/nested-repository-router/SKILL.md) 定位目标 Git 根，并读取目标路径适用的规则。
- 处理 Go 代码时，使用 [.agents/skills/golang-how-to/SKILL.md](.agents/skills/golang-how-to/SKILL.md) 按任务选择技能。
- 跨仓库提交或更新子模块指针时，使用 [.agents/skills/submodule-aggregate-workflow/SKILL.md](.agents/skills/submodule-aggregate-workflow/SKILL.md)。
- `.agents/skills` 为项目技能的维护入口；`.claude/skills` 保留共享技能的兼容副本。修改公共技能后同步对应文件，并运行 `python scripts/check_skills.py`。

需要 Kubernetes 日志上下文时，优先使用 MCP server `k8s-log-mcp`。
测试排错默认使用 namespace `portal`；只有用户明确要求或需要对比时才使用 `qa` 或 `auto`。
