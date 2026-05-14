# MalacoAgent

基于 RAG 的智能贝壳知识平台：自然语言问答 + shellauction.net 拍卖数据查询 + 软体动物学文献知识库。

详细设计见 [docs/design.md](docs/design.md)，进度见 [docs/work.md](docs/work.md)，需求见 [docs/todo.md](docs/todo.md)。

## 目录结构

```
malacoagent/
├── README.md / LICENSE / .env.example / .gitignore
├── docker-compose.yml          # 服务编排入口
├── backend/                    # FastAPI + Celery
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini / alembic/  # DB 迁移
│   └── app/
│       ├── main.py             # FastAPI 入口
│       ├── config.py
│       ├── database.py
│       ├── api/                # 路由层
│       ├── models/             # SQLAlchemy ORM
│       ├── schemas/            # Pydantic
│       ├── services/           # 业务逻辑
│       ├── tasks/              # Celery 任务（scraper / image downloader / 未来 RAG pipeline）
│       ├── core/               # security / exceptions / rate_limiter
│       └── utils/
├── frontend/                   # Vue 3 + Vite + Element Plus
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.js
│   └── src/                    # views / components / stores / api / router
├── infra/                      # 部署与基础设施
│   ├── docker/
│   │   └── base.Dockerfile     # 预装 pip 依赖的 base 镜像
│   └── postgres/
│       └── init/               # 容器首次启动自动执行的 SQL
├── docs/                       # 项目文档
│   ├── design.md
│   ├── todo.md
│   └── work.md
└── legacy/                     # 历史代码与数据备份（不参与构建）
    ├── postgres_backup.sql     # v1 数据库 dump（已导入新 schema，gitignored）
    ├── shellauction-net-tool/  # v1 Python 后端
    └── vue-shellauction-net-tool/  # v1 Vue 前端
```

## 快速开始

```bash
# 1. 准备环境变量
cp .env.example .env

# 2. 一键启动（自动构建缺失或过期的 base 镜像）
./dev up

# 3. 首次启动后，导入历史拍卖数据（需要 legacy/postgres_backup.sql）
./dev seed

# 4. 查看全栈状态
./dev status
```

## 开发脚本 `./dev`

所有日常操作集中在顶层 `./dev`（指向 [`scripts/dev.sh`](scripts/dev.sh)）：

```
./dev up                    # 启动全栈（智能重建 base 镜像）
./dev down                  # 停止
./dev rebuild               # --no-cache 强制重建 base + backend + celery
./dev restart [svc]         # 重启（默认 backend + celery-worker）
./dev nuke                  # 清空所有数据和镜像（需输入 'nuke' 确认）

./dev logs [svc]            # 跟日志（默认 backend）
./dev status                # 全栈健康检查

./dev psql [args]           # psql 进 postgres（支持 -c "SQL"）
./dev redis [args]          # redis-cli
./dev shell [svc]           # bash 进容器

./dev seed                  # 导入 legacy/postgres_backup.sql
./dev backup [path]         # pg_dump 到 backups/<timestamp>.sql.gz
./dev restore <file>        # 从备份恢复（危险）

./dev scrape [N]            # 触发 scraper（需 ADMIN_USERNAME/PASSWORD env）
./dev images [N]            # 触发图片下载

./dev test                  # 端到端冒烟测试
./dev help                  # 完整帮助
```

常见调试循环：

```bash
# 改完 requirements.txt
./dev rebuild

# 改完 Python 代码（backend 有 --reload，worker 要手动）
./dev restart celery-worker

# 改完 SQL schema
./dev nuke && ./dev up && ./dev seed
```

## 手动构建（跳过 ./dev）

## 手动构建（跳过 ./dev）

```bash
docker build -f infra/docker/base.Dockerfile -t malacoagent:v0.1 .
docker compose up -d --build
```

## 访问地址

| 入口 | 地址 |
|---|---|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9003 |

## 服务清单

| 服务 | 用途 | 外部端口 |
|---|---|---|
| postgres | PostgreSQL 16 + pgvector + pg_trgm | 5433 |
| redis | 缓存 + Celery broker | 6380 |
| minio | 对象存储（图片、PDF） | 9002 (S3) / 9003 (Console) |
| backend | FastAPI | 8000 |
| celery-worker | Scraper / 图片下载 / RAG pipeline | - |
| celery-beat | 定时任务调度 | - |
| frontend | Vue 3 + Nginx | 3000 |
