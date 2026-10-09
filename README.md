# Lim Tools Group

聚合仓库，用于统一管理 Lim Tools 的后端和前端子仓库。

## 子仓库

- [后端](https://github.com/limnova/lim-tools-server)：Go + Gin HTTP API 服务
- [前端](https://github.com/limnova/lim-tools-web)：Vite + React 19 + Tailwind CSS v4

在线表格第一阶段的功能范围、存储方案和评论 / 协作路线见 [实施方案](docs/spreadsheet-plan.md)。
本地启动与浏览器验证见 [前端说明](lim-tools-web/README.md)，保存 API 见 [服务端说明](lim-tools-server/README.md)。

## 克隆

首次克隆时同时初始化子模块：

```bash
git clone --recurse-submodules https://github.com/limnova/lim-tools-group.git
```

如果已经克隆了父仓库：

```bash
git submodule update --init --recursive
```

## 子模块日常操作

父仓库记录的是两个子仓库的具体 commit。先在子仓库完成验证和本地提交，再在父仓库目录执行：

```bash
git add lim-tools-server lim-tools-web
git commit -m "chore: bump lim-tools-web, lim-tools-server to verified updates"
```

这样可以保证每个父仓库版本都对应一组确定的前后端版本。

需要推送时，先推子仓库，再在父仓库执行 `git push --recurse-submodules=check`，
保证其他人能获取聚合仓库引用的所有子模块提交。

## 项目 skills

`.agents/skills` 是项目技能的维护入口，`.claude/skills` 提供共享技能的兼容副本。
公共技能修改后运行 `python scripts/sync_agent_config.py --apply` 同步两处，
再运行 `python scripts/check_skills.py` 检查一致性和入口引用。
`frontend-design` 与 `skill-creator` 在 Claude 中由 `.claude/settings.json` 的插件提供，因此无须另复制一份。

`golang-how-to` 和 `submodule-aggregate-workflow` 已针对项目做本地适配。
更新上游 skills 时请检查差异并保留这些适配；`skills-lock.json` 保留导入来源信息。
本次代码修复与技能建议见 [检查记录](docs/code-review.md)。

## Claude / Codex 配置维护

同步脚本需要 Python 3.11+，默认仅检查差异：

```powershell
python scripts/sync_agent_config.py --check
python scripts/sync_agent_config.py --personal --check
python scripts/sync_agent_config.py --personal --apply
```

`--personal` 包含用户目录的共享 MCP、skills 和规则。每次应用前自动备份，
已有的客户端专属配置由各客户端管理。项目 MCP 以本机 `.mcp.json` 为源，
生成 `.codex/config.toml`；两者均忽略提交，团队模板为 `.mcp.example.json`。
首次配置、维护方向、恢复方式与验证范围见 [配置维护说明](docs/agent-config.md)。
