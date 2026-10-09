---
name: submodule-aggregate-workflow
description: 聚合仓库 + git submodule 子仓库的提交同步规范。当在 lim-tools-group 这类聚合仓库及其前端/后端子仓库之间提交、推送、更新子模块指针,或排查子模块相关 git 问题(detached HEAD、指针落后、clone 缺子模块、push 被拒)时使用。分支命名与提交信息格式见 conventional-git skill。Triggers on submodule pointer bumps, cross-repo commits, git submodule update, detached HEAD inside submodules.
license: MIT
---

# 聚合仓库 + 子模块:提交同步规范

> 分支命名和提交信息的格式,**以 `conventional-git` skill 为准**,本文件不重复。
> 这里只讲 `conventional-git` 覆盖不到的部分:聚合仓库和子仓库之间怎么同步。

## 适用范围

| 仓库 | 角色 | 默认分支 |
|---|---|---|
| `lim-tools-group` | 聚合仓库(只放 `.gitmodules` / README / 仓库级配置,不放业务代码) | `main` |
| `lim-tools-web` | 子模块,前端 | `main` |
| `lim-tools-server` | 子模块,后端 | `main` |

`tapd-server` / `go-tapd-dingding` / `go-tapd-dingding-web` 是同一套结构,规则通用。
那边后端仍在 `master` 上,属于历史遗留,新仓库一律用 `main`。

---

## 一、铁律:子仓库先行,聚合仓库最后

聚合仓库记录的是子仓库**某一个具体 commit 的 SHA**,不是一个分支。

所以顺序永远是:

```
1. 子仓库里   commit  →  push
2. 聚合仓库里 git add <子模块路径>  →  commit  →  push
```

**反过来做会怎样:** 先 commit 聚合仓库的指针、再去推子仓库 —— 只要子仓库那次推送失败或还没做,
聚合仓库的 `main` 上就挂着一个远程不存在的 SHA。别人 `clone --recurse-submodules` 下来,
子模块直接初始化失败。而且坏指针已经推上去了,得再补一次提交才能修。

**推聚合仓库时加保险:**

```bash
git push --recurse-submodules=check
```

它会在推送前检查:本次要推的子模块指针,对应 commit 是否已存在于远程。有没推上去的直接拒绝,
报 `The following submodule paths contain changes that can not be found on any remote`。

建议固化成习惯 —— 聚合仓库的 `git push` 一律带这个参数。也可以一次性配死:

```bash
git config --global push.recurseSubmodules check
```

---

## 二、跨仓库用同一个分支名

`conventional-git` 定义了 `<type>/<description>` 的格式。本项目在此基础上加两条:

### 1. 用 `feat/`,不用 `feature/`

历史上 `go-tapd-dingding-web` 用过 `feature/admin-dashboard`,但提交类型是 `feat:`,两边对不上。
统一到 `feat/` —— 一套前缀同时管分支名和提交类型。

### 2. 一个功能动多个仓库时,三个仓库用完全相同的分支名

```
lim-tools-group    feat/user-login
lim-tools-web      feat/user-login
lim-tools-server   feat/user-login
```

好处是可以批量操作:

```bash
git submodule foreach 'git switch feat/user-login'
git submodule foreach 'git push -u origin feat/user-login'
```

合并 / 删除时也不会漏掉某个仓库。

### 什么时候必须开分支

单仓库小改动直接推 `main` 可以(个人项目,没问题)。

**但只要一次改动涉及两个及以上仓库,必须开同名分支。** 原因是聚合仓库的 `main`
代表"一组确定的前后端版本",而各仓库的 `main` 是各自独立推进的:

> 先把前端推上 `main`、后端晚两小时再推 —— 这中间任何人 clone 聚合仓库的 `main`,
> 拿到的都是"新前端 + 旧后端"这个从未被验证过的组合。

用分支把三个仓库的改动**攒齐了再一起合**,`main` 才始终对应一组配套的版本。

---

## 三、子模块指针提交的固定格式

常规提交信息按 `conventional-git` 走。只有聚合仓库里 bump 指针这一种提交,格式固定为:

```
chore: bump <子模块名> to <一句话说明>
```

```
chore: bump lim-tools-web to login form
chore: bump lim-tools-web, lim-tools-server to user login
```

两个子模块一起更新时,**合成一个提交**,别拆成两次 —— 它们的指针本来就要配套。

---

## 四、常用操作

### 首次 clone

```bash
git clone --recurse-submodules https://github.com/limnova/lim-tools-group.git
```

已经 clone 了但子模块是空的:

```bash
git submodule update --init --recursive
```

### 拉取别人的更新后,同步子模块

```bash
git pull
git submodule update --init --recursive
```

嫌麻烦可以开一次自动跟随(**只对本仓库生效**):

```bash
git config submodule.recurse true
```

### 开一个跨仓库功能

```bash
# 1) 三个仓库从各自最新的 main 拉同名分支
git -C lim-tools-web    switch -c feat/user-login main
git -C lim-tools-server switch -c feat/user-login main
git switch -c feat/user-login main

# 2) 在子仓库里改 → 提交 → 推送(铁律第 1 步)
git -C lim-tools-web add -A
git -C lim-tools-web commit -m "feat: add login form"
git -C lim-tools-web push -u origin feat/user-login

# 3) 回聚合仓库 bump 指针(铁律第 2 步)
git add lim-tools-web
git commit -m "chore: bump lim-tools-web to login form"
git push --recurse-submodules=check -u origin feat/user-login
```

### 看当前状态是否漂移

```bash
git submodule status
```

行首的符号是关键:

| 符号 | 含义 |
|---|---|
| 空格 | 子模块的 checkout 与聚合仓库记录的 SHA 一致,正常 |
| `+` | 子模块实际在别的 commit 上(通常是你在子模块里切了分支或提交了但没 bump) |
| `-` | 子模块尚未初始化,跑 `git submodule update --init` |
| `U` | 子模块有合并冲突,需要进去手动解决 |

### 批量看子模块改动

```bash
git submodule foreach 'git status -sb'
```

---

## 五、排错

| 现象 | 原因 | 处理 |
|---|---|---|
| 聚合仓库 `git status` 显示 `modified: lim-tools-web (new commits)` | 子模块前进了,聚合仓库还没 bump 指针 | 确认子模块已推送,然后 `git add lim-tools-web` 并提交 |
| 子模块里 `git status` 显示 detached HEAD | `git submodule update` 检出的是具体 commit,不是分支 | 提交前先 `git switch -c <分支>` 或 `git switch main` |
| `git push` 被 `--recurse-submodules=check` 拒绝 | 子模块有未推送的提交 | 先进子模块 `git push`,再推聚合仓库 |
| clone 后子模块目录是空的 | 没用 `--recurse-submodules` | `git submodule update --init --recursive` |
| 在子模块里改完,聚合仓库里没显示变化 | 改动还没提交,未提交的改动不会反映到指针上 | 在子模块里先 commit |
| 双方都 bump 了同一个子模块,产生冲突 | 两侧指针指向不同 SHA | 进子模块 `git merge <对方 SHA>`,再回聚合仓库 `git add` 并提交 |
| 想让子模块跟到远程最新 | — | `git submodule update --remote`(会切到 detached HEAD,注意) |

**不要用 `git submodule update --remote` 来"同步"跨仓库功能分支。** 它按 `.gitmodules` 里配的
分支(默认远程 HEAD)拉最新,会把你正在做的子模块分支覆盖成 detached HEAD。
跨仓库协作走上面第四节的分支流程。

---

## 六、新增子仓库时

```bash
git submodule add https://github.com/limnova/<仓库名>.git <仓库名>
git commit -m "chore: add <仓库名> submodule"
git push --recurse-submodules=check
```

然后记得同步更新聚合仓库 `README.md` 的「子仓库」列表。
