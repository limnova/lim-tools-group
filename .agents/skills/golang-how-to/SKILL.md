---
name: golang-how-to
description: 为 Go 开发、审查和排错选择当前已安装的相关 skills；只有用户要求配置时才修改项目的 agent 规则。
license: MIT
metadata:
  author: samber
  source: samber/cc-skills-golang
  adaptation: lim-tools-group
---

# Go skills 路由

这是本项目对上游路由的本地适配。以当前会话的技能列表、目标仓库规则和实际安装文件为准，按任务加载相关技能。

## 选择技能

先识别当前需要解决的问题，再读取对应入口；只有涉及第二类问题时才加载其他技能。

| 当前任务 | 本项目已有 skill |
| --- | --- |
| 错误传播、panic 恢复、错误日志 | [golang-error-handling](../golang-error-handling/SKILL.md) |
| goroutine、共享状态、取消与退出 | [golang-concurrency](../golang-concurrency/SKILL.md) |
| 测试、回归用例、测试隔离 | [golang-testing](../golang-testing/SKILL.md) |
| nil、切片别名、数值转换、资源生命周期 | [golang-safety](../golang-safety/SKILL.md) |
| 认证、用户输入、文件和网络边界的安全问题 | [golang-security](../golang-security/SKILL.md) |
| golangci-lint 配置与诊断 | [golang-lint](../golang-lint/SKILL.md) |
| 命名决策 | [golang-naming](../golang-naming/SKILL.md) |
| 模块与目录布局 | [golang-project-layout](../golang-project-layout/SKILL.md) |
| 生产日志、指标和追踪 | [golang-observability](../golang-observability/SKILL.md) |
| 选择新增依赖 | [golang-popular-libraries](../golang-popular-libraries/SKILL.md) |
| 复杂故障的复现和诊断 | [diagnosing-bugs](../diagnosing-bugs/SKILL.md) |

例如，修复关闭时 goroutine 或连接残留时加载并发技能；需要回归测试时再加载测试技能；涉及返回错误时再加载错误处理技能。普通审查按正在检查的代码选择技能，不默认展开整个技能库。

## 工具与缺失依赖

- 本地构建与依赖 API 以 `go.mod`、`go.sum` 和实际工具链为准。
- `gopls`、专用 MCP 或语言服务器可用时用于语义导航；否则使用文本搜索、编译器、`go test` 和 `go vet`。
- 子技能引用未安装的技能时，先判断是否为完成任务的必要依赖。可选参考使用本地源码或官方文档替代，并在影响结论时说明缺口。
- 只有必要步骤确实无法执行时才报告阻塞。安装工具、更换依赖或配置外部服务按用户任务范围决定。
- 不把仅在 Claude Code 中存在的命令、工具名称或思考模式当作其他环境的执行要求。

## 项目配置

只有用户要求配置 Go agent 规则时才修改 `AGENTS.md` 等文件。保留现有指令，以项目可访问的技能路径建立简短指针；只增加任务所需的规则。

完成后说明加载了哪些技能、实际执行的验证，以及影响结果的工具限制。
