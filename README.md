# Lim Tools Group

聚合仓库，用于统一管理 Lim Tools 的后端和前端子仓库。

## 子仓库

- [后端](https://github.com/limnova/lim-tools-server)：待初始化
- [前端](https://github.com/limnova/lim-tools-web)：Vite + React 19 + Tailwind CSS v4

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

父仓库记录的是两个子仓库的具体 commit。子仓库有更新后，在父仓库目录执行：

```bash
git add lim-tools-server lim-tools-web
git commit -m "chore: update submodules"
git push
```

这样可以保证每个父仓库版本都对应一组确定的前后端版本。
