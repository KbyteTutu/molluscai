# MalacoAgent 工作记录

## 项目概述

基于 RAG 的智能贝壳知识平台。用户通过自然语言提问，系统检索知识库文献并结合 LLM 生成回答。

**技术栈**: FastAPI + Vue 3 + PostgreSQL(pgvector) + Redis + Celery + MinIO + Docker

---

## 当前进度: P0 — 基础骨架 ✅

### 已完成

- [x] Docker Compose（PostgreSQL + Redis + MinIO + Backend + Celery + Frontend + Scraper）
- [x] PostgreSQL 完整 DDL（12 张表 + 扩展 pgvector/pg_trgm）
- [x] FastAPI 骨架（配置、数据库、CORS、异常处理）
- [x] 6 个 SQLAlchemy ORM 模型 + 5 个 Pydantic Schema
- [x] JWT 认证（register / login / refresh / me）
- [x] 权限系统（Permission Flag 枚举 + ROLE_PERMISSIONS + RequirePermission）
- [x] 配额检查（check_quota + RoleQuota 按角色限流）
- [x] 拍卖数据搜索 API（POST /search + GET /{item_no} — ILIKE + trigram + 分页）
- [x] 前端 Vue 3 项目（Element Plus / Pinia / Vue Router / Axios）
- [x] 登录/注册页面 + 拍卖搜索页面 + 用户中心
- [x] 前端 nginx 反向代理 + SPA fallback
- [x] Base 镜像（malacoagent:v0.1 — 预装所有 pip 包 + APT 依赖 + 清华镜像源）

### 文件清单（62 个）

| 类别 | 文件 | 说明 |
|------|------|------|
| **基础设施** | `docker-compose.yml` | 7 个服务（postgres/redis/minio/backend/celery-worker/celery-beat/frontend/scraper） |
| | `.env.example` | 全部环境变量 |
| | `Dockerfile.base` | Base 镜像 — 预装 Python 依赖 |
| | `backend/Dockerfile` | 后端容器 |
| | `scraper/Dockerfile` | 数据采集容器 |
| | `frontend/Dockerfile` | 前端构建 + Nginx |
| | `frontend/nginx.conf` | 静态文件 + /api 代理 |
| **数据库** | `postgres/init/01-extensions.sql` | CREATE EXTENSION vector + pg_trgm |
| | `postgres/init/02-schema.sql` | 完整 DDL（12 张表） |
| **后端 - 入口** | `backend/app/main.py` | FastAPI app + CORS + 路由 |
| | `backend/app/config.py` | pydantic-settings（DATABASE_URL 为 @property） |
| | `backend/app/database.py` | async SQLAlchemy engine + session |
| | `backend/requirements.txt` | Python 依赖（44 行） |
| | `backend/alembic.ini` + `alembic/env.py` | 数据库迁移 |
| **后端 - 模型** | `models/user.py` | User / RoleQuota / QueryLog |
| | `models/auction.py` | Auction（is_sold 为 Computed column） |
| | `models/document.py` | Document（图文混合文献） |
| | `models/chunk.py` | TextChunk / ImageChunk（pgvector Vector(3584)） |
| | `models/billing.py` | BillingRecord / PricingRule |
| | `models/model_config.py` | ModelConfig / ModelUsageLog |
| **后端 - Schema** | `schemas/user.py` | UserCreate, UserLogin, UserRead, TokenResponse |
| | `schemas/auction.py` | AuctionSearchRequest（offset≤500, limit≤50）, SearchResponse |
| | `schemas/billing.py` | 桩 |
| | `schemas/document.py` | 桩 |
| | `schemas/model_config.py` | 桩 |
| **后端 - API** | `api/deps.py` | Permission Flag + ROLE_PERMISSIONS + RequirePermission + check_quota |
| | `api/v1/auth.py` | POST register/login/refresh, GET /me |
| | `api/v1/auction.py` | POST /search, GET /{item_no} |
| **后端 - 服务** | `services/auth_service.py` | JWT 认证逻辑 |
| | `services/auction_service.py` | 拍卖搜索（ILIKE + func.similarity） |
| **后端 - 核心** | `core/security.py` | bcrypt + JWT（HS256, access 30min / refresh 7d） |
| | `core/exceptions.py` | 6 种自定义异常 + 全局 handler |
| | `core/rate_limiter.py` | slowapi 桩 |
| **后端 - 任务** | `tasks/celery_app.py` | Celery 实例（P2+ 启用） |
| **前端** | `src/main.js` | Vue 3 + Pinia + Element Plus + 中文 |
| | `src/App.vue` | 导航栏 + 用户下拉菜单 |
| | `src/router/index.js` | /login, /, /me + 认证守卫 |
| | `src/stores/auth.js` | 登录/注册/刷新/登出 + localStorage |
| | `src/stores/search.js` | 拍卖搜索状态 |
| | `src/api/index.js` | Axios + Bearer 拦截 + 401 自动刷新 |
| | `src/views/LoginView.vue` | 登录/注册双 Tab |
| | `src/views/AuctionSearch.vue` | 搜索表单 + 结果 + 详情对话框 |
| | `src/views/UserProfile.vue` | 个人信息 + 角色标签 + 登出 |
| | `src/components/SearchForm.vue` | 9 个筛选条件 |
| | `src/components/ResultTable.vue` | el-table + 价格格式化 + 已售标签 |
| | `vite.config.js` | Vite + /api proxy |

---

## 本 Session 修复清单

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 前端 `/me` 404 | `authApi.me()` 调用 `/me`，后端在 `/auth/me` | 改 `api/index.js` 为 `/auth/me`，登录后 fetch user |
| 2 | 注册返回 500 | `email-validator` 未安装 | 添加 `email-validator` 到 `requirements.txt` |
| 3 | 注册连不上 DB | `DATABASE_URL` 是 @property，env var 被忽略 | docker-compose 改传 `POSTGRES_HOST=postgres` |
| 4 | 注册 SQLAlchemy 报 NoForeignKeysError | `user_id` 缺 ForeignKey 约束 | 6 个模型的 FK 全面修复 |
| 5 | bcrypt 报 72 字节错误 | bcrypt 5.0.0 与 passlib 不兼容 | `requirements.txt` 固定 `bcrypt<4.1` |
| 6 | bcrypt 长密码依旧报错 | verify_password 也走 bcrypt | `hash_password` 内手动 `encode("utf-8")[:72]` |
| 7 | 注册成功但 /me 500 | 7 张表因 init SQL 中断未创建 | 手动创建缺失表 |
| 8 | init SQL 中断根因 | ivfflat 索引不支持 3584 维（上限 2000） | 注释掉 ivfflat 索引，改用 brute-force |
| 9 | 默认端口冲突 | 6379/9000 被占用 | 所有外部端口改为高位（5433/6380/9002/9003） |
| 10 | pip/apt 下载慢 | 国内网络 | 清华镜像源（APT + pip），Docker 镜像加速 |

---

## 待解决问题

### 向量索引
- pgvector 的 ivfflat/hnsw 均限制 ≤ 2000 维
- Qwen3-VL-Embedding-8B 输出 3584 维
- P0 暂时跳过索引，P3 时需评估：`halfvec` 量化 or 降维 or 换模型

### bcrypt 密码
- bcrypt 5.0 与 passlib 1.7.4 不兼容，已固定 bcrypt < 4.1
- 长密码手动截断至 72 字节（`hash_password` 内处理）
- verify_password 也存在长密码问题 — 需同步截断

---

## P0-P6 实施计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| **P0 — 基础骨架** | Docker + PostgreSQL + FastAPI + 用户认证 + 拍卖搜索 | ✅ 已完成 |
| **P1 — 用户体系** | 完整权限 + 查询记录 + 前端优化 | 🔲 待实施 |
| **P2 — 知识库核心** | PDF 上传 + 解析 Pipeline（OCR → 元数据 → 切分 → Embedding） | 🔲 待实施 |
| **P3 — RAG 检索** | 混合检索 + 生成回答 + 问答界面 | 🔲 待实施 |
| **P4 — 收费系统** | 计费 + 余额 + 充值 | 🔲 待实施 |
| **P5 — 安全加固** | 限流 + 反爬 + 图片缓存 + HTTPS | 🔲 待实施 |
| **P6 — 优化** | 检索质量调优 + 前端美化 + 性能优化 | 🔲 待实施 |

---

## 运行命令

```bash
# 首次（或 requirements.txt 变更后）重建 base 镜像
docker build -f Dockerfile.base -t malacoagent:v0.1 .

# 启动全部服务
docker compose up -d --build

# 仅重启后端（代码修改后）
docker compose up -d --build backend

# 查看日志
docker compose logs -f backend

# 清空重建（表结构变更时）
docker compose down -v && docker compose up -d
```

## 访问地址

| 入口 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9003 |
