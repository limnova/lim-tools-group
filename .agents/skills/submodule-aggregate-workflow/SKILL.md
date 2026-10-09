---
name: submodule-aggregate-workflow
description: 在聚合仓库与 Git submodule 之间提交代码、更新指针和按授权推送；也用于处理 detached HEAD、指针漂移与子模块冲突。
license: MIT
---

# 聚合仓库与子模块提交

分支和提交信息格式使用 [conventional-git](../conventional-git/SKILL.md)。仓库路径和远程地址读取实际 `.gitmodules` 与 Git 配置。

## 本地提交

1. 分别检查聚合仓库及涉及子仓库的分支、HEAD、工作区改动，识别既有用户改动。
2. 跨仓库改动使用同名工作分支；保留当前起点。遇到 detached HEAD 时先创建工作分支，保留已有工作。
3. 在实际所属的子仓库修复并验证，只暂存已检查且属于本次任务的文件，然后提交。
4. 子仓库提交完成后，在聚合仓库暂存对应 gitlink。配套的前后端指针放进同一个提交。
5. 验证聚合仓库记录的 SHA 与子仓库 HEAD 一致，并报告分支、提交和剩余改动。

用户只要求“提交”时，完成本地 commit 即可。本地聚合提交可以记录尚未推送的子仓库 SHA；应明确它暂时只在本地可用。

指针提交格式：

```text
chore: bump <子模块名> to <简短说明>
```

普通文档和技能改动按自己的提交类型组织；不要把无关文件夹带入指针提交。

## 远程推送

用户已要求推送或发布到远程时：

1. 先推送涉及的子仓库，确认目标 SHA 可在对应远程取得。
2. 再推聚合仓库，使用 `git push --recurse-submodules=check`。
3. 子仓库推送失败时保留本地提交，处理明确的错误；在子仓库 SHA 可取得前，不发布引用它的聚合提交。
4. 分别报告各仓库的推送结果。创建分支、提交、推送和合并是不同操作，授权按用户指令判断。

需要设置检查选项时优先采用命令参数；项目配置使用本仓库的 `git config`。修改全局 Git 配置需要用户要求。

## 同步与排错

| 情况 | 处理 |
| --- | --- |
| 普通 clone 或拉取后子模块缺失/落后 | 检查子模块工作区后，使用 `git submodule update --init --recursive` 跟随聚合仓库记录的 SHA |
| `git submodule status` 前缀为 `+` | 核对实际 HEAD；属于本次改动时提交配套指针 |
| 前缀为 `-` | 子模块未初始化 |
| 前缀为 `U` | 指针冲突；检查两侧 SHA，在子仓库形成经过验证的合并结果，再暂存 gitlink |
| detached HEAD 且已有工作 | 从当前 HEAD 建工作分支，保留改动 |
| 推送检查拒绝聚合提交 | 先确认子仓库远程已包含目标 SHA，再重试聚合推送 |
| 本地未提交的子模块改动 | 聚合状态可能显示 dirty，但 gitlink 仍指向旧 HEAD；先提交子仓库再更新指针 |

`git submodule update --remote` 跟随配置的远程分支，会改变 checkout；只在用户要求追随远程版本且工作区已检查时使用。跨仓库工作分支通过各仓库的分支操作同步。

新增子模块或改变仓库布局后，更新聚合仓库 README。读取子仓库代码规则使用 [nested-repository-router](../nested-repository-router/SKILL.md)。
