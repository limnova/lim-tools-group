# 代码检查与 skills 建议

检查日期：2026-10-09。范围为当前聚合仓库及两个已初始化的子模块。
本次阅读前后端源码、检查现有构建和测试，并对可复现的问题完成修复。

## 已修复的代码问题

| 位置 | 触发与原有结果 | 修复结果与证据 |
| --- | --- | --- |
| 前端 `OptimisticDemo` | 连续发送相同正文，两个乐观条目使用相同临时 ID；浏览器复现了两条残留的“发送中” | 每次发送生成独立 ID，确认前后复用该 ID，合并时按 ID 去重；重复发送后恰好显示两条已确认消息，无浏览器错误 |
| 前端消息输入 | 非受控表单在异步 action 成功后自动重置，可能清掉请求期间输入的下一条草稿 | 改为受控输入，只在当前消息提交时清空；浏览器断言发送期间的新草稿保留 |
| 后端 panic 恢复 | `gin.CustomRecovery` 仍向 Gin writer 输出额外文本；debug 模式还会转储请求头 | 使用 `CustomRecoveryWithWriter(nil, ...)`，保留 Gin 断连处理并统一输出结构化日志；debug/release 回归用例验证 Gin writer 无输出 |
| 后端访问日志 | Recovery 在访问日志外层，panic 展开调用栈时跳过访问日志后半段 | AccessLog 包住 Recovery，恢复后记录最终状态；在实际服务组装上验证 panic 请求包含状态 500 与请求 ID |
| 后端关闭流程 | `Shutdown` 超时直接返回，活跃连接仍未关闭，请求 context 仍存活 | 超时后调用 `Close`，等待监听 goroutine 结束，保留关闭和监听错误；真实本地 HTTP 请求验证返回超时错误后请求 context 已取消 |
| 后端配置与测试 | `0s`、负时长被接受，关闭期限立即失效；配置测试可能受外部环境变量影响 | 非正时长回落到默认值；测试先清空配置环境变量，新增零值和负值用例 |
| 聚合 README | 后端仍标注“待初始化” | 更新为实际 Go + Gin 服务，并说明本地提交与远程推送的区别 |

消息合并与 action 处理参考 [React useOptimistic](https://react.dev/reference/react/useOptimistic)；
受控输入的选择依据是 [React form 的自动重置行为](https://react.dev/reference/react-dom/components/form)。
关闭超时后的处理与 [Go HTTP Server 的 Shutdown/Close 语义](https://go.dev/src/net/http/server.go) 一致。

## 验证结果

- 前端：`pnpm lint`、`pnpm build` 均通过。
- 浏览器：`tests/browser_smoke.py` 通过，覆盖 ref 聚焦、订阅成功/失败、待办加载/重载、列表筛选、重复发送、草稿保留及主题持久化；无控制台错误或页面异常。
- 后端：`go test ./...`、`go test -race ./...`、`go vet ./...`、`go build ./...` 均通过。
- Skills：`python scripts/check_skills.py` 通过，公共副本一致、入口 Markdown 相对链接可解析；临时目录验证了副本漂移、源文件缺失和断链均会使检查失败。
- 重写的 Go 路由、子模块工作流及新增的嵌套仓库路由通过系统 skill-creator 的结构校验。

本机未安装 `golangci-lint`，因此未运行 `.golangci.yml` 中的扩展检查。
前端目前使用模拟接口，浏览器验证覆盖脚手架交互，不代表已经接通后端业务接口。

## Skills 的处理建议

本次重点检查实际用到的技能及其项目适配。建议优先修正本地规则和触发边界，
已有技能能够覆盖的工作无需重新寻找整套替代品。

| Skill | 具体问题或适用边界 | 建议与本次处理 |
| --- | --- | --- |
| `golang-how-to` | 上游表格将多项未安装技能作为必读项，并依赖当前环境未提供的专用工具 | **已重写项目入口**：只路由到已安装技能，工具按可用性选择，配置 agent 规则仅在用户要求时进行；保留来源信息 |
| `submodule-aggregate-workflow` | 把本地 commit 与远程 push 写成统一必执行步骤，还建议修改全局 Git 设置 | **已重写**：区分本地提交与获授权的远程推送；保留同名分支、子仓库先提交、配套指针一起提交及推送检查 |
| `conventional-git` | 将分支命名说成 Conventional Commits 标准要求 | **已纠正文案**：提交信息遵循标准，分支/工作树规则是本地约定；其余命名规则保留。标准自身描述的是[提交信息约定](https://www.conventionalcommits.org/en/v1.0.0/) |
| `nested-repository-router` | 项目此前依赖个人安装目录，其他协作者未必能读取相同入口 | **已加入项目**：在 `.agents` 与 `.claude` 中提供相同入口；根 `AGENTS.md` 建立指针 |
| `diagnosing-bugs` | 固定要求先有失败命令才读源码，并要求每次列出 3–5 个假设；对简单、直接的问题流程偏重 | 建议后续做小幅改写：保留复杂故障的复现循环；允许先读源码确定复现入口，假设数量按不确定性决定。暂保留上游版本 |
| `writing-for-agents` 的 `SKILL-MECHANICS.md` | 将特定环境的 `disable-model-invocation` 与其他 skill 的调用能力绑定，不能直接作为跨环境规则 | 保留写作原则；机械配置应按 Claude/Codex 分开说明，并在使用时核对宿主支持的字段。暂未修改 |
| 项目 `skill-creator` | 已有评估流程依赖 Claude CLI；当前会话同时有 Codex 系统同名 skill | 简单创建/改写优先使用宿主自带 creator；需要 Claude 评估时使用项目版本。后续若整理技能命名，可将项目评估入口单独命名以避免歧义，无需删除资源 |
| React 最佳实践、Go 并发/错误/测试技能 | 适合提供专题参考；其中部分规则、工具或版本示例需要按项目适配 | 保留并按任务读取。本项目开启 React Compiler，不因性能指南就批量添加手动记忆化；Go 示例以 `go.mod` 和实际编译验证为准 |

## 维护方式

`.agents/skills` 是维护入口；`.claude/skills` 保留已经存在的公共兼容副本。
本次将原有未跟踪的 `.agents` 内容纳入版本管理，没有批量删除上游参考资源。
`frontend-design` 与项目 `skill-creator` 的 Claude 入口由现有插件提供。

公共文件修改后同步副本，再运行 `python scripts/check_skills.py`。
该脚本检查文件一致性和入口断链，不证明技能的行为质量；较大改写仍应使用真实任务验证。
`skills-lock.json` 保留导入来源记录；更新上游时检查差异，保留本地适配。

三个仓库使用工作分支 `fix/scaffold-reliability`。本次按用户要求完成本地提交；
远程共享时，先推送两个子仓库，再用 `git push --recurse-submodules=check` 推送聚合仓库。
