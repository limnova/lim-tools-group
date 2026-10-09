---
name: postgres-conventions
description: "PostgreSQL 建表、改表与迁移的项目约定：表/列/索引/约束命名、主键与时间戳、列类型选择、goose 迁移文件格式、limadmin 与 limtools_ro 的权限边界。新建表、改动 schema、编写或修改迁移文件时使用。"
---

# PostgreSQL 约定

所有 schema 变更都走 `lim-tools-server/migrations/` 下的 goose 迁移文件。
在 psql 里手工改结构会让本地、QA 与其他环境的 schema 各走各的，事后无从对齐。

## 建表

每张表都按这套写：

- 主键固定 `id bigint generated always as identity primary key`。用 identity 而不是 `serial`：
  `serial` 是遗留写法，序列的所有权挂在列上，`information_schema` 里也查不到。
- 表名用复数 snake_case（`users`、`task_runs`），列名用单数 snake_case。
- 外键列命名为 `<单数表名>_id`（`user_id` 指向 `users`），并显式写出 `on delete` ——
  默认的 `no action` 很少是想要的，写出来才是一个决定。
- 每张表都带 `created_at` 与 `updated_at`，类型均为 `timestamptz not null default now()`。
- 列默认 `not null`。写可空时，理由应该是"这个值在业务上确实可以缺失"。

```sql
create table task_runs (
    id         bigint generated always as identity primary key,
    user_id    bigint      not null references users (id) on delete cascade,
    status     text        not null default 'pending'
                           check (status in ('pending', 'running', 'done', 'failed')),
    payload    jsonb       not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_task_runs_user_id on task_runs (user_id);
create index idx_task_runs_running on task_runs (status) where status = 'running';
```

## 列类型

| 用 | 对应场景里的常见替代 | 理由 |
|---|---|---|
| `text` | `varchar(n)` | 两者在 PG 里性能一致；长度约束写成 `check (char_length(x) <= n)`，调整时不必改类型 |
| `timestamptz` | `timestamp` | `timestamp` 不带时区，跨时区与夏令时下会算错 |
| `numeric` | `real` / `double precision` | 二进制浮点存不下精确的十进制金额 |
| `jsonb` | `json` | `json` 只能整段读写，`jsonb` 可索引可查询 |
| `text` + `check (x in (...))` | `create type ... as enum` | enum 加值要 `alter type`，删值几乎做不到 |
| `boolean` | 用 `smallint` / `int` 模拟 | 语义直白，且 PG 对 boolean 有专门的存储优化 |

## 索引

- **外键列一律建索引。** PostgreSQL 不会为外键自动建索引，缺了它，父表的
  `delete` / `update` 会退化成全表扫描 —— 这是最容易漏、代价最大的一条。
- 命名：普通索引 `idx_<表>_<列>`，唯一约束 `uq_<表>_<列>`，检查约束 `ck_<表>_<含义>`。
- 部分索引（带 `where`）留给已经确认很窄的查询条件，不预先铺。

## 迁移

目录 `lim-tools-server/migrations/`，goose 格式：

- 文件名 `NNNNN_<动词>_<对象>.sql`，动词取 `create` / `add` / `alter` / `drop`，
  例如 `00002_add_task_runs_running_index.sql`。
- 每个文件同时写 `-- +goose Up` 与 `-- +goose Down`，Down 必须真能回滚。
  写不出 Down，通常说明这次迁移拆得不够小。
- 一次迁移只做一件事。
- 已经合并进 `main` 的迁移文件不再改动，需要调整就新加一个。
- 迁移以 `limadmin` 执行。

## 权限

| 角色 | 用途 | 边界 |
|---|---|---|
| `limadmin` | 应用连接、执行迁移 | 库 owner，可 DDL、可读写 |
| `limtools_ro` | agent / MCP 的只读查询 | 仅 `select`；新表经 default privileges 自动继承 |

只读查询一律走 `limtools_ro`。它写不动任何东西，查询本身带破坏性也不会生效。

聚合仓库根目录的 `.mcp.json` 配了 `postgres` MCP（`postgres-mcp`，RESTRICTED 模式，9 个工具），
用的就是 `limtools_ro`。连接串里的密码走 `${LIM_TOOLS_DB_RO_PASSWORD}` 展开，取自**启动 Claude Code
时的环境变量** —— 变量没设时字面量会被原样传下去，服务端认证失败。团队成员需要在各自机器上设置它。
