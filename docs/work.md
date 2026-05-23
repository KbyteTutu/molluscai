# MolluscAI 工作记录

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
- [x] Base 镜像（molluscai:v0.1 — 预装所有 pip 包 + APT 依赖 + 清华镜像源）

### 文件清单（62 个）

| 类别 | 文件 | 说明 |
|------|------|------|
| **基础设施** | `docker-compose.yml` | 7 个服务（postgres/redis/minio/backend/celery-worker/celery-beat/frontend/scraper） |
| | `.env.example` | 全部环境变量 |
| | `Dockerfile.base` | Base 镜像 — 预装 Python 依赖（现位于 `infra/docker/base.Dockerfile`） |
| | `backend/Dockerfile` | 后端容器 |
| | `scraper/Dockerfile` | 数据采集容器 |
| | `frontend/Dockerfile` | 前端构建 + Nginx |
| | `frontend/nginx.conf` | 静态文件 + /api 代理 |
| **数据库** | `postgres/init/01-extensions.sql` | CREATE EXTENSION vector + pg_trgm（现位于 `infra/postgres/init/`） |
| | `postgres/init/02-schema.sql` | 完整 DDL（12 张表）（现位于 `infra/postgres/init/`） |
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

## P0 复审修复（2026-05-11）

work.md 之前标记 P0 ✅，但端到端实测发现一组阻塞性 bug。本轮一并修复。

### 实测验证

| 用例 | 修复前 | 修复后 |
|---|---|---|
| `POST /auth/register` | ✅ 201 | ✅ 201（返回 `{user, tokens}`） |
| `POST /auth/login` | ✅ 200 | ✅ 200（返回 `{user, tokens}`） |
| `GET /auth/me` | ❌ 500 | ✅ 200 |
| `POST /auction/search` (空 DB) | ✅ 200 total=0 | ✅ 200 total=2,990,337 |
| `POST /auction/search?name=aurisiacus` | ❌ 500 | ✅ 200 total=14,588 |
| `GET /auction/{item_no}` | ❌ 500 | ✅ 200 |

### 本轮修复清单

| # | 问题 | 根因 | 修复 |
|---|---|---|---|
| 11 | `/auth/me` 500 ResponseValidationError | `UserRead.id: str`，ORM 返回 `UUID` | `schemas/user.py` 改为 `id: UUID` |
| 12 | `/auction/search` 500（数据导入后） | `AuctionRead/Detail.created_at: str`，ORM 返回 `datetime` | `schemas/auction.py` 改为 `Optional[datetime]` |
| 13 | 长密码 >72 字节登录失败 | `verify_password` 未截断 | `core/security.py` 同步加 `[:72]` 截断 |
| 14 | 注册/登录后前端需二次调 `/me` | 接口只返回 tokens | 新增 `AuthResponse{user,tokens}`，路由改用之，前端 `stores/auth.js` 删除二次调用 |
| 15 | 权限/配额系统裸跑 | `Permission Flag` 和 `check_quota` 定义未挂载 | `api/v1/auction.py` 挂 `RequirePermission(SEARCH_AUCTION)` + `check_quota(..., "auction", ...)` |
| 16 | compose 告警 `version` 已废弃 | docker-compose.yml 第 1 行 | 移除 |
| 17 | **`auctions` 表 0 行 — 拍卖功能完全不能用** | `scraper/` 是空壳；`legacy/postgres_backup.sql` 未导入 | 导入 staging → 转换写入 `auctions`（2,990,337 行，1,727,375 已售，67 个 family） |

### 数据导入步骤（供复现）

```bash
# 1. 拷贝备份进 postgres 容器
docker cp legacy/postgres_backup.sql mollusc-postgres:/tmp/backup.sql

# 2. 创建 staging 表并抽取 COPY 块
docker exec mollusc-postgres psql -U mollusc -d molluscai -c "
  CREATE TABLE shellauction_staging (id int, item int, image text, name text,
    family text, size text, locality text, note text, seller text,
    start_price int, current_price int, end_date text, owner text, deal_date date);"
docker exec mollusc-postgres bash -c "awk '
  /^COPY public\.shellauction/ {print \"COPY shellauction_staging (...) FROM stdin;\"; in_copy=1; next}
  in_copy && /^\\\\\.\$/ {print; exit}
  in_copy {print}
' /tmp/backup.sql > /tmp/staging_copy.sql"
docker exec mollusc-postgres psql -U mollusc -d molluscai -f /tmp/staging_copy.sql

# 3. 字段映射 + 去重写入 auctions
#    item→item_no, current_price→final_price, owner→buyer,
#    image→images_origin[], end_date(DD-MM-YYYY text)→DATE
docker exec mollusc-postgres psql -U mollusc -d molluscai -c "
  INSERT INTO auctions (item_no,name,family,size,locality,note,seller,
    start_price,final_price,end_date,buyer,images_origin)
  SELECT DISTINCT ON (item) item, NULLIF(name,''), NULLIF(family,''), ...
    CASE WHEN end_date ~ '^\d{2}-\d{2}-\d{4}$'
         THEN TO_DATE(end_date,'DD-MM-YYYY') ELSE NULL END, ...
  FROM shellauction_staging WHERE item IS NOT NULL
  ORDER BY item, id DESC ON CONFLICT (item_no) DO NOTHING;"

docker exec mollusc-postgres psql -U mollusc -d molluscai -c "DROP TABLE shellauction_staging;"
```



## 待解决问题

### 向量索引（P3 再处理）
- pgvector 的 ivfflat/hnsw 均限制 ≤ 2000 维；Qwen3-VL-Embedding-8B 输出 3584 维
- P3 时需评估：`halfvec` 量化 or 降维 or 换模型

---

## P0.5 — Scraper / 增量采集（2026-05-11）✅

### 完成内容

| 模块 | 文件 | 说明 |
|---|---|---|
| 拍卖采集 Celery 任务 | `backend/app/tasks/auction_scraper.py` | port 自 `legacy/shellauction-net-tool/get_data.py`，写入新 schema 的 `auctions` 表，`ON CONFLICT (item_no) DO UPDATE` 幂等 |
| 图片下载 Celery 任务 | `backend/app/tasks/image_downloader.py` | 拉取 `is_sold=true` 且 `images_local IS NULL` 的拍品图片入 MinIO bucket `auction-images`，更新 `images_local` |
| MinIO 客户端 helper | `backend/app/services/minio_client.py` | `ensure_bucket / put_bytes / object_exists` |
| Beat 调度 | `backend/app/tasks/celery_app.py` | `scrape_incremental` 每小时 :15、`download_images` 每 30 分钟 |
| 管理触发接口 | `backend/app/api/v1/admin.py` | `POST /admin/scraper/run`、`POST /admin/scraper/download-images`（`Permission.MANAGE_USERS` 限 superadmin） |
| 依赖 | `backend/requirements.txt` | 新增 `beautifulsoup4`、`lxml` |
| 清理 | `docker-compose.yml`、`scraper/` 目录 | 删除空壳 `scraper` 服务（采集逻辑现在跑在 `celery-worker` 内） |

### 实测验证

```
POST /api/v1/admin/scraper/run {batch_size:20, start_id:1}
  → 200 {task_id, task_name}
  → worker: fetched=20 saved=11 skipped=9 (1.07s)

POST /api/v1/admin/scraper/download-images {batch_size:3}
  → 200 {task_id, task_name}
  → worker: downloaded=3 updated=3 (1.29s)
  → MinIO: auction-images/0409/4097217_0.jpg (29908B, JPEG magic ffd8ffe0)
```

### 已知限制

- 旧 v1 的 `bot.py`（自动竞价）未迁移 — 与 P0.5 目标无关，按需再做。
- 采集速率默认 10 并发，未做 robots.txt 检查 — 若 shellauction.net 后续限流，调整 `_run_scraper(..., concurrency=...)`。
- 图片去重靠 MinIO `object_exists()`，object name 用 `{item_no // 10000}/{item_no}_{idx}.{ext}` 分桶，避免单目录千万级文件。

---

## P0-P6 实施计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| **P0 — 基础骨架** | Docker + PostgreSQL + FastAPI + 用户认证 + 拍卖搜索 | ✅ 已完成 |
| **P0.5 — 增量采集** | Scraper Celery + 图片下载 MinIO + 管理触发接口 | ✅ 已完成 |
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
docker build -f infra/docker/base.Dockerfile -t molluscai:v0.1 .

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

---

## P1.5 — 前端全面重写 & UI 现代化 (2026-05-12~13) ✅

### 技术栈更换

| 组件 | 旧 | 新 |
|------|----|----|
| UI 框架 | Element Plus | [Reka UI](https://reka-ui.com/) (Radix Vue) |
| CSS | 无框架 | [Tailwind CSS v4](https://tailwindcss.com/) (OKLCH 双主题) |
| 字体 | 系统默认 | Fraunces (标题) + Inter (正文) |
| 工具库 | 无 | `tailwind-merge` + `clsx` (`lib/utils.js`) |
| 通知 | 无 | Sonner (toast) |

### 新增文件 (约 70+ 个)

**UI 组件库** (`frontend/src/components/ui/` - 40 个):
Button, Card (Header/Content/Description/Footer/Title), Input, Label, Badge, Avatar, Alert (Title/Description), Collapsible (Content/Trigger), DropdownMenu (Content/Item/Separator/Trigger), Sheet (Content/Description/Header/Title), Table (Body/Cell/Head/Header/Row), Tabs (Content/List/Trigger), Separator, Skeleton, Sonner

**布局组件** (`frontend/src/components/layout/`):
- `AppShell.vue` — 主布局：左侧边栏 sticky + 内容区
- `AppSidebar.vue` — 导航侧边栏（拍卖/分类学/对比/个人中心/管理），移动端响应式 (Sheet 抽屉)
- `ThemeToggle.vue` — OKLCH 亮/暗主题切换

**拍卖组件** (`frontend/src/components/auction/`):
- `AuctionCard.vue` — 拍品卡片（图片、名称、价格、已售标签）
- `AuctionTable.vue` — 拍品表格视图
- `AdvancedFilters.vue` — 高级筛选面板（family/seller/locality/size/date range）
- `CompareToggle.vue` / `CompareBar.vue` — 对比功能（见下方）

**品牌组件** (`frontend/src/components/brand/`):
- Logo + 品牌标语

**通用组件** (`frontend/src/components/common/`):
- 加载状态、空状态、错误边界等

**视图重写** (Element Plus → Reka UI):
| 旧文件 | 新文件 | 说明 |
|--------|--------|------|
| `AuctionSearch.vue` | `HomeView.vue` | 拍卖搜索主页（默认最近 1 月 + 价格降序 + 10 条/页） |
| `UserProfile.vue` | `ProfileView.vue` | 用户资料页 |
| — | `AuctionDetailView.vue` | 拍卖详情页（~301 行，含图片、元数据、分类学校验） |
| — | `CompareView.vue` | 拍品对比页（横向并排视图） |
| — | `TaxaSearchView.vue` | 物种分类搜索页 |
| — | `TaxonDetailView.vue` | 物种详情页 |
| — | `AdminScraperView.vue` | 管理 - 采集控制 |
| — | `AdminModelsView.vue` | 管理 - 模型管理 |
| — | `AdminEmbeddingsView.vue` | 管理 - 嵌入进度 |
| — | `AdminUsageView.vue` | 管理 - 用量统计 |

### 路由表 (10 条)

| 路径 | 名称 | 认证 | 说明 |
|------|------|------|------|
| `/login` | Login | Guest | 登录/注册 |
| `/` | Home | Auth | 拍卖搜索主页 |
| `/auctions/:itemNo` | AuctionDetail | Auth | 拍卖详情 |
| `/taxa` | Taxa | Auth | 物种搜索 |
| `/taxa/:aphiaId` | TaxonDetail | Auth | 物种详情 |
| `/compare` | Compare | Auth | 拍品对比 |
| `/me` | Profile | Auth | 个人中心 |
| `/admin/scraper` | AdminScraper | Superadmin | 采集管理 |
| `/admin/models` | AdminModels | Superadmin | 模型管理 |
| `/admin/embeddings` | AdminEmbeddings | Superadmin | 嵌入管理 |
| `/admin/usage` | AdminUsage | Superadmin | 用量统计 |

---

## P1.6 — 拍卖功能增强 (2026-05-13) ✅

### 搜索改进
- 默认筛选：最近 1 个月 + 价格降序 + 10 条/页
- 排序下拉：价格升降 / 名称升降 / 日期升降
- 高级筛选面板：family / seller / locality / size range / date range (Collapsible)
- 左侧边栏 sticky + 移动端响应式 (Sheet 抽屉)

### 图片显示修复
- `AuctionRead` schema 补 `images_origin` 字段
- 前端 `imageUrls()` 去重 + `_thumb` 后缀过滤

### 拍品对比
- **Pinia store**: `stores/compare.js` — localStorage 持久化，最多 5 个拍品
- **浮动底栏**: `CompareBar.vue` — 显示已选拍品数量，点击进入对比页
- **对比视图**: `CompareView.vue` — 横向并排网格，高亮最高/最低价格
- **开关**: `CompareToggle.vue` — 拍品卡片/详情页添加/移除对比

### 拍卖详情页
- 图片轮播、元数据卡片（family/size/locality/seller/buyer/date/price）
- 分类学校验区块（见下方 P1.8）

---

## P1.7 — 物种分类检索 & 向量化 (2026-05-13~14) ✅

### Taxa 数据导入

| 步骤 | 内容 |
|------|------|
| 数据源 | `legacy/Mollusca_species.xlsx` (141,670 条软体动物物种) |
| 导入 | `pandas` → `taxa` 表，`aphia_id` 为主键 |
| DDL | `infra/postgres/init/04-taxa.sql` |
| 字段 | aphia_id, scientific_name, authority, status, unaccepted_aphia_id, rank, kingdom, phylum, class, order, family, genus, lsid |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/taxa/search` | 关键词搜索（ILIKE + trigram + 分页） |
| `GET` | `/api/v1/taxa/search?mode=hybrid` | 混合搜索（词法 + 向量 RRF 融合 + 可选 rerank） |
| `GET` | `/api/v1/taxa/{aphia_id}` | 物种详情 |

### 向量化

| 项目 | 详情 |
|------|------|
| 嵌入表 | `taxa_embeddings` — halfvec(2000) + HNSW 索引 |
| 模型 | Qwen3-Embedding-8B (4096 维 → MRL 截断为 2000 维 halfvec) |
| 规模 | 141,670 条，100% 嵌入完成 |
| 性能优化 | asyncpg connection pool + 6 并发 → 71 rows/s (35x 提速) |
| DDL | `infra/postgres/init/05-taxa-embeddings.sql` |
| 脚本 | `backend/scripts/embed_taxa.py` |
| Celery 任务 | `backend/app/tasks/embedding_job.py` |

### 混合搜索实现 (`backend/app/services/taxa_search.py`)

- 词法搜索：PostgreSQL full-text search (`tsvector` / `tsquery`)
- 向量搜索：pgvector HNSW + cosine distance
- RRF (Reciprocal Rank Fusion) 融合两组排序
- 可选 Cohere / Jina rerank

### 前端
- `TaxaSearchView.vue` — 搜索栏 + 结果列表 + 搜索模式切换
- `TaxonDetailView.vue` — 物种详情（分类阶层、权威、状态、同义名）

---

## P1.8 — 拍卖-分类学匹配 (2026-05-14) ✅

### 后端

| 文件 | 说明 |
|------|------|
| `backend/app/api/v1/auction.py` | 新增 `GET /{item_no}/taxon-match` 端点 |
| `backend/app/services/auction_taxon_match.py` | 名称规范化 + 混合搜索 + 同义名解析 |
| `backend/app/schemas/taxon.py` | TaxonRead / TaxonMatchResponse schema |

### 名称规范化 (`normalize_auction_name()`)
- 截断到 ` - ` 前
- 去除命名权威括号内容
- 跳过变体标记 (var., subsp., f., form.)
- 取前 2 词作为搜索关键词
- 6 个测试 case 全部验证通过

### 匹配流程
1. 规范化拍卖名称 → 生成 cleaned_query
2. 混合搜索 taxa → 取 top-5 候选
3. 若最佳匹配有 `unaccepted_aphia_id` → 解析为 accepted 名称
4. 返回 `{cleaned_query, matched, accepted, alternatives, confidence, similarity}`

### 前端

| 文件 | 说明 |
|------|------|
| `frontend/src/stores/taxonMatch.js` | Pinia store — `Map<itemNo, result>` 内存缓存，`force=true` 重新匹配 |
| `frontend/src/api/index.js` | 新增 `auctionApi.taxonMatch(itemNo)` |
| `frontend/src/views/AuctionDetailView.vue` | "分类学校验"区块 — 手动点击按钮触发，显示匹配结果 |

**设计决策**:
- 仅手动触发（不自动，节省 API 配额）
- 仅内存缓存（刷新失效，不持久化）
- 仅详情页（搜索结果列表不做联动）

---

## P1.9 — 模型管理 UI (2026-05-14) ✅

### 后端

| 文件 | 说明 |
|------|------|
| `backend/app/api/v1/models.py` | CRUD + 测试 + 用量统计 + 嵌入状态 |
| `backend/app/services/llm_providers.py` | LLM provider 抽象（OpenAI 兼容接口） |
| `backend/app/schemas/model_config.py` | ModelConfig 完整 schema |

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/models` | 列出所有模型 |
| `POST` | `/admin/models` | 创建模型 |
| `PATCH` | `/admin/models/{id}` | 更新模型 |
| `DELETE` | `/admin/models/{id}` | 删除模型 |
| `POST` | `/admin/models/{id}/test` | 测试模型连接 |
| `GET` | `/admin/models/usage/summary` | 用量摘要（按天） |
| `GET` | `/admin/models/usage/recent` | 最近用量记录 |
| `GET` | `/admin/models/embeddings/status` | 嵌入进度 |
| `POST` | `/admin/embed/run` | 触发嵌入任务 |
| `POST` | `/admin/embed/cancel` | 取消嵌入任务 |

### 前端管理页面
- `AdminModelsView.vue` — 模型 CRUD 表格 + 新建/编辑对话框 + 测试按钮
- `AdminUsageView.vue` — 用量统计图表 + 最近记录
- `AdminEmbeddingsView.vue` — 嵌入进度条 + 开始/取消按钮
- 所有管理页路由 `requiresSuperadmin: true`

---

## P1.10 — 管理功能完善 + 拍卖 UX 优化 ✅ (2026-05-20)

### 已完成

- **主题切换优化**: ThemeToggle 从侧边栏底部用户区移至顶部标题栏 Logo 旁
- **图片下载增强**: 后端新增 `item_no_from` / `item_no_to` 参数，前端图片下载卡片新增编号范围输入框
- **拍卖 ID 混淆**: 全站 item_no 改为与 "tukechao" 逐字符 XOR 后的大写十六进制，`lib/utils.js` 新增 `xorId()` 函数
- **拍卖搜索优化**: 移除买家筛选，新增成交状态筛选（全部 / 已卖出 / 未卖出）；买家为 "- no Bids" 时显示"流拍"
- **数据采集统计**: 后端新增 `GET /admin/scraper/stats`，前端采集页面展示完整统计（记录总数、最大编号、已下载图片数等 6 项），支持手动刷新
- **任务管理器**: 新增独立任务管理界面 (`/admin/tasks`)
  - 后端: Redis 记录任务 + Celery inspect 监控，`GET /admin/tasks` / `POST /admin/tasks/{id}/revoke`
  - 前端: `AdminTasksView.vue` 展示最近 50 条任务，自动 5 秒刷新，支持撤消活跃任务

### 文件变更

| 文件 | 说明 |
|------|------|
| `backend/app/services/task_tracker.py` | Redis 任务记录 + Celery AsyncResult 状态查询 |
| `backend/app/api/v1/admin.py` | 新增 tasks/stats 端点，dispatch 时 record_task |
| `backend/app/tasks/image_downloader.py` | 支持 item_no_from / item_no_to 范围下载 |
| `backend/app/schemas/auction.py` | buyer → is_sold 筛选字段 |
| `backend/app/services/auction_service.py` | 同步 buyer → is_sold 过滤 |
| `frontend/src/views/AdminTasksView.vue` | 新建任务管理页面 |
| `frontend/src/views/AdminScraperView.vue` | 统计卡片 + 图片下载编号范围 |
| `frontend/src/views/AuctionDetailView.vue` | xorId + 移除买家 + 流拍标记 + 分类学校验移至左栏 |
| `frontend/src/views/HomeView.vue` | is_sold 筛选取代 buyer，每月 1 日更新 |
| `frontend/src/components/auction/AuctionCard.vue` | 移除 item_no + 流拍标记 |
| `frontend/src/components/auction/AuctionTable.vue` | 移除编号列 + 流拍标记 |
| `frontend/src/components/auction/AdvancedFilters.vue` | 移除买家 + 新增成交状态下拉 |
| `frontend/src/components/layout/AppSidebar.vue` | ThemeToggle 移至标题栏 + 任务管理链接 |
| `frontend/src/components/layout/ThemeToggle.vue` | 位置优化 |
| `frontend/src/lib/utils.js` | 新增 xorId() 函数 |
| `frontend/src/api/index.js` | 新增 adminApi.scraperStats / listTasks / getTask / revokeTask |
| `frontend/src/router/index.js` | 新增 /admin/tasks 路由 |

---

## 待解决问题

### WoRMS Dump 脚本（P2+ 再做）
- `scripts/worms/worms_dump.py` — 独立爬取脚本

---

## P0-P6 实施计划（当前）

| 阶段 | 内容 | 状态 |
|------|------|------|
| **P0 — 基础骨架** | Docker + PostgreSQL + FastAPI + 用户认证 + 拍卖搜索 | ✅ 已完成 |
| **P0.5 — 增量采集** | Scraper Celery + 图片下载 MinIO + 管理触发接口 | ✅ 已完成 |
| **P1.5 — 前端现代化** | Reka UI + Tailwind v4 + 双主题 + 响应式 | ✅ 已完成 |
| **P1.6 — 拍卖增强** | 搜索改进 + 图片修复 + 拍品对比 + 详情页 | ✅ 已完成 |
| **P1.7 — 物种分类** | taxa 表 + 向量化 + 混合搜索 + RRF | ✅ 已完成 |
| **P1.8 — 分类学匹配** | auction→taxon 匹配 + 前端区块 | ✅ 已完成 |
| **P1.9 — 模型管理** | LLM model CRUD + 用量 + 嵌入管理 UI | ✅ 已完成 |
| **P1.10 — 管理完善** | 任务管理 + 采集统计 + 图片下载范围 + ID 混淆 + 主题优化 | ✅ 已完成 |
| **P1.11 — UX + 搜索** | 邮箱登录 + logo 头像 + 侧边栏布局 + 查询日志过滤 + IP 显示 + 拍卖全时段搜索 + relevance 排序 + family 下拉 + size 范围 + locality trigram | ✅ 已完成 |
| **P2 — 知识库核心** | PDF 上传 + 解析 Pipeline（OCR → 元数据 → 切分 → Embedding） | 🔲 待实施 |
| **P3 — RAG 检索** | 混合检索 + 生成回答 + 问答界面 | 🔲 待实施 |
| **P4 — 收费系统** | 计费 + 余额 + 充值 | 🔲 待实施 |
| **P5 — 安全加固** | 限流 + 反爬 + 图片缓存 + HTTPS | 🔲 待实施 |
| **P6 — 优化** | 检索质量调优 + 前端美化 + 性能优化 | 🔲 待实施 |

---

## 变更日志

### 2026-05-17 — 项目重命名 malacoagent → molluscai

- GitHub 仓库已从 `KbyteTutu/malacoagent` 重命名为 `KbyteTutu/molluscai`
- 全局替换品牌名：`MalacoAgent` → `MolluscAI`
- 技术标识统一：`malacoagent` → `molluscai`（DB名、bucket、包名、镜像名、Celery app）
- Docker container 前缀：`malaco-` → `mollusc-`
- PG 默认用户：`malaco` → `mollusc`
- 前端 localStorage key：`malaco-theme/compare` → `mollusc-theme/compare`
- 涉及 20 个文件，64 处替换
- **注意**：已有环境需 `docker compose down` 后重建；已有 DB 需 rename 或重建

### 2026-05-20 — P1.10 管理功能完善 + 拍卖 UX 优化

**拍卖显示优化**:
- item_no 与 "tukechao" 逐字符 XOR 后以十六进制大写展示（全站）
- 买家为 "- no Bids" 时显示"流拍"标记
- 搜索筛选：买家筛选 → 成交状态筛选（全部 / 已卖出 / 未卖出）
- 首页默认日期范围：本月 1 日更新，默认显示上月数据
- AuctionDetailView: 分类学校验移至左栏图片下方，移除买家字段

**管理功能**:
- 数据采集页：新增统计卡片（总记录/最大编号/已下载/存储占用），刷新按钮
- 独立任务管理页 (`/admin/tasks`)：任务列表、自动刷新、撤消活跃任务
- 图片下载：支持指定 item_no 范围下载
- 主题按钮：从侧边栏底部移至顶部标题栏

**后端**:
- `GET /admin/scraper/stats` — 采集统计端点
- `GET /admin/tasks`、`POST /admin/tasks/{id}/revoke` — 任务管理端点
- `backend/app/services/task_tracker.py` — Redis 任务记录 + Celery 状态追踪

**提交**: 8 个原子化 commits，已推送 `origin/main`

---

## WoRMS 数据全字段导入与多源检索（2026-05-21）✅

**背景**:
`scripts/worms/worms_dump.py` 可在墙外把 Mollusca 整个亚树（≈ 120k 分类元）抓成
单文件 SQLite。本 session 把这份富数据完整导入 Postgres，并把检索能力从“只查
学名前缀”升级到“学名 + 曾用名 + 各语言俗名一站式模糊匹配”，命中曾用名/俗名
时在 UI 上显著标注来源。

**数据层**:
- `infra/postgres/init/06-taxa-extras.sql` — 新增四张表：
  `taxa_classification`（祖先链）、`taxa_children`（直接子级）、
  `taxa_attributes`（生境/分布/特征键值对）、`taxa_external_ids`（NCBI / TSN /
  IUCN / BOLD / FishBase / AlgaeBase 等十数据源外部 ID）。
- 既有 `taxa / taxa_synonyms / taxa_vernaculars / taxa_sources /
  taxa_distributions` 已在 04-taxa.sql 中存在，本次仅追加扩展表。

**导入器**:
- `backend/scripts/import_worms_sqlite.py`（538 行）— asyncpg + sqlite3 异步
  分批（4 096/批）upsert，9 张表全量同步，单事务内 ANALYZE。
- 合并策略：WoRMS 提供的字段以 WoRMS 为准；本地 xlsx 独有字段（subphylum /
  subclass / infraclass / superorder / suborder / infraorder / superfamily）
  保留不动；`data_source` 自动从 `xlsx` → `merged` 翻转，不可逆地承认混源。
- `scripts/prod_import.sh` — 生产环境一键脚本：先跑 WoRMS sqlite，再用 dev.sh
  的 staging-COPY 流程恢复 `auctions` 表（来自 `postgres_backup.sql`）。
- `./dev worms-import <file>` / `./dev prod-import [worms] [backup]` 两个新子命令。
- `data_import/` 目录：源数据存放点，已加入 `.gitignore`。

**检索（核心改造）**:
- `backend/app/services/taxa_search.py::_lexical_with_match()` 同时打三张表：
  `taxa.scientificname`（学名）、`taxa_synonyms.scientificname`（曾用名）、
  `taxa_vernaculars.vernacular`（俗名），各自取 trgm similarity Top-K，再按
  aphia_id 去重。同一物种被多源命中时按 `name > synonym > vernacular` 选最优
  注解，但**结果间的相对排序仍按 trgm 相似度**——保证 `Loricata`（曾用名，
  sim=1.0）能压过 `Loricidae`（学名，sim=0.36）排到第一位。
- 每条结果附带 `match_info: {kind, term, authority?, language?}`。
- 新增 `lexical_search()` 公共接口供 `/taxa/search?mode=lexical` 路径直接调用，
  不再走原来仅查 `taxa.scientificname` 的旧 SQL。

**API 扩充** (`backend/app/api/v1/taxa.py`，从 2 个端点扩到 8 个):
- `GET /taxa/search` — 现已多源 + match_info
- `GET /taxa/{id}` — 详情（既有）
- `GET /taxa/{id}/synonyms` — 曾用名清单
- `GET /taxa/{id}/vernaculars` — 各语言俗名
- `GET /taxa/{id}/distributions` — WoRMS 分布数据
- `GET /taxa/{id}/children?accepted_only=true` — 下级分类
- `GET /taxa/{id}/classification` — 完整祖先链
- `GET /taxa/{id}/external-ids` — 跨数据库外部 ID

**前端**:
- `TaxaSearchView.vue` — 命中曾用名时琥珀色 `命中曾用名: <Term> <authority>`
  banner，命中俗名时天蓝色 `命中俗名: <Term> <lang>` banner，均带 lucide
  图标 (`History` / `Languages`)。占位文案改为 `学名、曾用名 或 各语言俗名,
  如 Conus、Loricata、chiton…`。
- `TaxonDetailView.vue` — 新增 5 个区块：曾用名、各语言俗名（按语言代码分列）、
  分布、下级分类（可点击跳转）、外部数据库（可点击跳到 NCBI / ITIS / IUCN /
  FishBase / AlgaeBase / BOLD）。Header 增加面包屑式祖先链导航。
- `frontend/src/api/index.js` — `taxaApi` 加 6 个方法。

**端到端验证**:
1. 用 `tiny.sqlite`（500 个 Polyplacophora 节点）跑导入器：0.3 s 完成，9 张表
   行数与源 SQLite 完全一致。
2. 验证合并语义：手动把 aphia=55 改成 `data_source='xlsx'` + 假数据，重跑导入
   后 `authority` 被 WoRMS 覆盖、`subphylum` 保留、`data_source` 变 `merged`。
3. 真实 API 调用 `q=Loricata`：Polyplacophora #55 排第一，`match_info.kind=
   synonym, term=Loricata, authority=Schumacher, 1817`。
4. `q=chiton`：命中 #55 的德语俗名 `Chitone`，`match_info.kind=vernacular,
   language=deu`。
5. `/taxa/55/{synonyms,children,classification,external-ids}` 全部返回 ok。
6. `npx vite build` 全量产物 OK，新视图 8.73 / 12.95 KB gzip。

**剩余动作**: 用户自己拿真实 `worms_mollusca.sqlite` 跑一次 `./dev
worms-import` 即可全量上线（预计全 120k 节点 ≈ 10–20 分钟）。

---

## 物种检索详情页 — 冈瓦纳词典 / WoRMS 链接重排 ✅

**背景**: 物种详情页需要接入第三方中文释义数据源（冈瓦纳英汉博物词典），并把
`在 WoRMS 查看` 这枚一直挂在卡片底部的按钮搬到顶部徽章行，让信息层级更清晰。

**前端改动**:

- `frontend/src/views/TaxonDetailView.vue`:
  - 头部 `accepted / rank / #aphia` 同一行末尾追加 `在 WoRMS 查看` 按钮
    （`ml-auto`），底部老位置删除。
  - 新增「冈瓦纳英汉博物词典」翠绿渐变 Card：
    - 标题外链 `ganvana.com`、副链 `点击进入冈瓦纳自然网 ›`
    - 输入框默认填入 `taxon.scientificname`（拉丁名，无 author）
    - 物种加载完毕自动检索一次；用户可改写后重查
    - 结果项展示「中文名 · 英文名 · 拉丁名 · 编号」，超 10 条折叠
- `frontend/vite.config.js` + `frontend/nginx.conf`:
  - 新增 `/ganvana/` 反向代理（dev = vite proxy，生产 = nginx），规避浏览器
    跨域，并自动 `Origin/Referer` 改写到 `https://ganvana.com`。

**端到端验证**: 浏览器登录 → `/taxa/140895` (Aartsenia candida) →
WoRMS 按钮在头部右侧；冈瓦纳卡片在底部，自动用拉丁名查询；手动改成
`Gonaxis` 重查，拿到雷克 / 伊土 / 钻石 / 开泊 / 乱世 / 四面体共 6 条扭轴蜗牛
中文释义，含英文俗名「mashed gonaxis」「four-sided gonaxis」。

---

## 物种检索页 — 警示语精简 ✅

`frontend/src/views/TaxaSearchView.vue` 顶部的整块「使用须知」Alert 改为
`物种检索` H1 下方的一行小字（琥珀色 `text-xs`，前缀 ShieldAlert 图标），
正文「数据来源 WoRMS 数据库等公开渠道，仅供便捷集合查询使用，不得用于
违法违规目的。」。视觉降权，不再抢标题焦点。

---

## 品牌资源 — 替换 Logo / 添加 Footer / 加大顶部 Logo ✅

**Logo 资源接入**:

- 用户在仓库根放置 `logo.png`（约 168 KB 真实素材）。
- 新增 `frontend/public/logo.png`，构建期 Vite 直接拷贝至产物根，运行时由
  Nginx 在 `/logo.png` 提供。
- `frontend/index.html` 增加 `<link rel="icon" type="image/png" href="/logo.png" />`，
  浏览器标签页同步更新。

**`<ShellLogo>` 重写** (`frontend/src/components/brand/ShellLogo.vue`):
原占位 SVG 全部替换为 `<img src="/logo.png">`，保留 `size` / `class` props，
统一作用于所有调用点（侧边栏、移动端 header、登录页、空状态、缺图占位）。

**水印**: `frontend/src/views/LoginView.vue` 登录页右上角
480 px 装饰水印从 `text-primary/5`（仅着色 SVG）改为 `opacity-5`（适配
PNG）。

**左上角 Logo 放大 1.5×**:

- `AppSidebar.vue` 桌面端 `:size="22"` → `33`
- `AppShell.vue` 移动 header `:size="20"` → `30`

**全站底部 Footer** (`AppShell.vue`):
所有内页（侧边栏布局下的 main 列）底部加细线分割的 `<footer>`，居中显示：

```
© 2026  京ICP备2022009849号  ·  tutu.gold
```

`京ICP备2022009849号` 链接到 `https://beian.miit.gov.cn/`，`tutu.gold`
链接到 `https://tutu.gold`，均 `target="_blank" rel="noopener noreferrer"`。

`CompareBar` 仍 `fixed bottom-4`，浮在 footer 之上，不互相遮挡。

---

## 拍卖记录列表 — 每页 12 条 ✅

`frontend/src/views/HomeView.vue` 中常量 `PAGE_SIZE = 10` 改为 `12`，是
唯一改动点；分页计数、骨架屏数量、`offset` 步进、`下一页` 禁用阈值全部
通过该常量驱动，已自动同步。后端 `app/schemas/auction.py` 限制
`limit ≤ 50`，12 在合法范围内。

---

## P5 — 公开首页 / 角色配额 / 查询审计 / 后台数据统计（2026-05-21）✅


普通用户每小时 10 次智能检索，VIP 100 次，其他不限；限额可后台修改；查询留日志
（IP/用户名/查询内容）；提供数据统计界面。"

### 后端

- `infra/postgres/init/02-schema.sql` 与 `backend/alembic/versions/0001_hourly_quotas_and_audit_ip.py`：
  `role_quotas` 增加 `hourly_ai_limit / hourly_auction_limit / hourly_taxa_limit /
  daily_ai_limit / daily_taxa_limit`（`-1=不限`，`0=禁用`，`>0=窗口内上限`），
  种子值 user→AI 10/小时·50/日，vip→100/小时·500/日，其他不限；
  `query_logs` 增加 `ip_address INET / status_code SMALLINT`，
  并加 `idx_query_logs_(user_id, created_at DESC) WHERE user_id IS NOT NULL`、
  `idx_query_logs_(query_type, created_at DESC)` 两个降序索引；
  外键 `query_logs.user_id_fkey` 改为 `ON DELETE SET NULL`，避免删用户被审计日志阻塞。
- `backend/app/core/request_ip.py`：`get_client_ip()` 优先读 `X-Real-IP`，
  其次 `X-Forwarded-For` 最左项，再回落 `request.client.host`，全部经
  `ipaddress.ip_address()` 验证后返回。
- `backend/app/core/quota.py`（新）：`check_quota()` 取 `pg_advisory_xact_lock`
  避免同一用户并发请求绕过窗口；分别 `COUNT(*) WHERE created_at >= now()-interval` 算
  小时窗 + 日窗；命中阈值时**先写一条 `status_code=429` 的审计日志**再抛
  `HTTPException(429, detail={error,query_type,window,used,limit,reset_at,
  retry_after_seconds})` 并附 `Retry-After` 头；`_count_queries_since` 仅计入
  `status_code < 400` 的请求，确保 429 不计入下次配额，重置语义正确。
- `backend/app/api/v1/auction.py` `POST /search` 走配额 + `finally` 写审计；
  新增 **`GET /auction/recent`** 公开端点（无 auth，硬上限 12 条，60s Redis 缓存
  键 `molluscai:auction:recent:v1`，缓存读写失败均静默回落到直查 DB）；
  `GET /auction/{item_no}/taxon-match` 标记为 `query_type='ai'`。
- `backend/app/api/v1/taxa.py` `GET /search`：`mode=hybrid` 标记 `query_type='ai'`，
  `lexical` 标记 `'taxa'`，统一走 `check_quota` + `log_query`。
- `backend/app/api/v1/users.py`（新）：`GET /me/quota` 返回三类查询的 `{hourly,daily}`
  `{used,limit,remaining,reset_at}` 快照，前端用于侧边栏配额胶囊。
- `backend/app/api/v1/admin.py`：新增 `GET/PATCH /admin/quotas[/{role}]`
  （PATCH 走 `SELECT … FOR UPDATE`），`GET /admin/queries/stats?days=N`
  （总数 / 429 数 / by_type / by_day 时序 / Top10 用户 / Top10 关键词 /
  range_days），`GET /admin/queries/recent?limit=N`（联表 users 取 username）。
- `backend/app/api/deps.py`：`check_quota` / `log_query` 改为从 `core.quota` 重导出，
  增加 `get_current_user_optional` 用于 `/auction/recent` 这类可选 auth 端点。
- `backend/app/main.py`：注册 `/api/v1/users` 路由。

### 前端

- `frontend/src/router/index.js`：`/` 改为 `meta.requiresAuth=false`；新增
  `/admin/quotas`、`/admin/queries`（`requiresSuperadmin: true`）。其余受保护路由
  原有 `requiresAuth=true` 守卫保持不变，会自动 `redirect=/login?redirect=…`。
- `frontend/src/views/HomeView.vue`：根据 `auth.isAuthenticated` 切换两套界面。
  匿名态调用 `auctionApi.recent()`，渲染 4 张 stat tile + 一张主色 CTA Card
  （Lock 图标 + 登录/注册按钮）+ "最近上拍" 网格 + "登录后查看更多" CTA；
  搜索表单 / 排序 / 视图切换 / 分页全部隐藏。已登录态保持原有筛选 + 分页 +
  500 条上限提示等全部行为。
- `frontend/src/api/index.js`：新增 `auctionApi.recent()`、`userApi.myQuota()`、
  `adminApi.{listQuotas, updateQuota, queryStats, recentQueries}`。
  axios 响应拦截器处理 429：调 `formatQuotaToast(detail)` 弹 `vue-sonner` 错误 toast
  （文案如 "智能检索本小时配额已用尽（10/10），约 21 分钟后重置"），同时把
  `error.response.data.detail` 改写成同一友好字符串，避免视图把结构化对象当字符串
  渲染成 JSON；命中 429 时还会触发 `auth.refreshQuota()` 刷新胶囊。
- `frontend/src/stores/auth.js`：新增 `quota` ref + `refreshQuota()` action；
  `login/register` 成功后自动 fetch `/me/quota`。
- `frontend/src/components/layout/AppSidebar.vue`：登录态在底部账号区上方加智能检索
  小时配额胶囊（`{used}/{limit}`，进度条按 ≥60% 转琥珀、≥90% 转
  `bg-destructive`，`-1` 显示 "不限" 不画条）；匿名态把头像 dropdown 替换成
  "登录" + "注册" 双按钮。`onMounted` + 路由变化均 `refreshQuota()`。
  管理组新增 "配额管理"（Gauge 图标）和 "查询日志"（ScrollText 图标）两项，
  仍走 `isSuperadmin` 渲染。
- `frontend/src/views/AdminQuotasView.vue`（新）：4 行（user / vip / doc_admin /
  superadmin）× 9 列（hourly_ai / hourly_auction / hourly_taxa / daily_ai /
  daily_auction / daily_taxa / daily_rag / rate_limit_per_min + 操作）的 Table，
  逐单元 `<Input type=number min=-1>`；逐行 dirty-state 跟踪，仅修改字段才进
  PATCH body，`-1` 单元下显示 "∞ 不限" 微文，dirty 行操作列出现 "已修改" Badge +
  撤销 / 保存 按钮，保存后 toast.success + 重置基准。
- `frontend/src/views/AdminQueriesView.vue`（新）：顶部范围 `<select>`（1/7/30/90 天）
  + 刷新按钮；4 张 stat tile（总查询 / 429 命中 / 类型分布迷你条 / 范围）；按类型
  Badge 列表 + 每日趋势 SVG 折线图（无外部图表库）+ Top10 用户 + Top10 关键词 +
  近 100 条原始日志（时间 / 用户 / IP / 类型 Badge / 查询内容截断 / 结果数 / 状态
  Badge）。状态 Badge 200→默认 OK，429→destructive 限流，4xx→outline 拒，5xx→错。

### 验证（Playwright）

- 匿名访问 `/` → 渲染 stat 网格 + CTA Card + 12 条最近拍卖；无搜索/排序/分页；
  无登录残留，无 console 错误。
- 匿名 `/taxa` → 跳 `/login?redirect=/taxa`，登录后回到 `/taxa`。
- `qa_user` 用尽 10 次配额：第 11 次 `taxa/search?mode=hybrid` 返回 HTTP 429，
  body 含 `error/query_type/window/used/limit/reset_at/retry_after_seconds` 全部
  字段，`Retry-After` 头存在，下一次请求 `query_logs` 多一条 `status_code=429` 行
  且 `used` 仍为 10（未自吃）。
- `/admin/quotas` 把 user.hourly_ai_limit 从 10 改为 15 并保存 → DB 同步落到 15，
  随后 PATCH 还原为 10。
- `/admin/queries` 全部 6 块面板（总数 / 429 数 / 类型分布 / 每日趋势 / Top 用户 /
  Top 关键词 / 近 100 条日志）渲染，IP 与状态码 Badge 正确显示。
- 全程 `docker compose build frontend`（Vite + Nginx 多阶段）成功。

### 风险 & 后续

- "Top 关键词" 直接 `GROUP BY lower(query_text)`，量大时需要改用按周 rollup；
  当前实测 ms 级，足够。
- Postgres `COUNT(*)` 滑动窗口在单实例 + 高并发下能支撑到约 100 req/s；
  扩到多实例时需切到 Redis sorted-set，已在 Oracle 评审中标记。
- 现有 `users.daily_query_limit`（per-user override）仍未接入；如需要个体豁免，
  需在 `_hourly_limit / _daily_limit` 中按用户优先读取该列。

---

## 列表页 → 详情页 → 返回 — 保留搜索状态（2026-05-21）✅

之前 `/` 与 `/taxa` 列表页点详情后再 ←，搜索条件 / 翻页位置 / 结果全部丢
失（因为 `<router-view>` 卸载列表组件、`onMounted` 重新跑空查询）。改用
Vue Router 4 + `<keep-alive>` 让被纳入白名单的列表组件在切换路由时**只
失活不卸载**：

- `frontend/src/components/layout/AppShell.vue`：`<router-view>` 改为
  `v-slot="{ Component }"` + `<keep-alive :include="['HomeView',
  'TaxaSearchView']">`，仅缓存这两个列表页；详情页继续按原样卸载，避免
  跨 `aphia_id` / `item_no` 残留旧内容。
- `frontend/src/router/index.js`：新增 `scrollBehavior(to, from,
  savedPosition)`，浏览器后退使用 `savedPosition` 恢复滚动条，前进/新跳
  转回到顶部。
- `frontend/src/views/HomeView.vue`：`defineOptions({ name: 'HomeView' })`
  让 `<keep-alive :include>` 能匹配到组件；`onMounted` 增加守卫——已登录
  时若 `search.hasResults` 跳过初次拉取，未登录时若 `anonItems.length`
  跳过；新增 `watch(isAuthenticated)`，登录↔登出切换时主动拉取目标态数
  据，登出时调用 `search.clearResults()` + `offset.value = 0`，避免缓存
  在两种身份之间串。
- `frontend/src/views/TaxaSearchView.vue`：`defineOptions({ name:
  'TaxaSearchView' })`。其余状态本就是组件内 ref，`<keep-alive>` 一并
  保留，无需改 onMounted。

### 验证（Playwright）

- `/taxa` 输入 `q=conus` + `family=Conidae` → 4 条结果 → 点 Conus
  circumcisus → `/taxa/426455` → 浏览器 ← → 回到 `/taxa` 时 q/family/结
  果列表/`pageInfo "1 – 20 / 97"` 全部保留。
- `/`（已登录）输入 `q=conus` → 检索 → 下一页 → `pageInfo "13 – 24 /
  6,114"` → 点第一张拍卖卡 → `/auctions/...` → ← → 回到 `/` 时 q/分页/
  12 张卡片完整保留。
- 登出后 `/` 立即切到匿名态：渲染 stat 网格 + "登录后查看更多" CTA + 12
  条最近上拍，控制台 0 error / 0 warning。

---

## 后台用户管理 — 角色 / 锁定 / 重置密码（2026-05-21）✅

`users` 表本就有 `role` 与 `is_active`（auth_service / get_current_user 已
将 `not is_active` 视为登录失败 / 鉴权拒绝），无需新增列；直接复用即可。

### 后端（`backend/app/api/v1/admin.py`）

新增三个端点，全部走 `require_admin = RequirePermission(Permission.MANAGE_USERS)`：

- `GET /admin/users?q=&role=&is_active=&limit=&offset=`：用户名 / 邮箱
  ILIKE 模糊搜索 + 角色 / 状态过滤，按 `created_at DESC` 分页，返回
  `{items, total, limit, offset}`。
- `PATCH /admin/users/{user_id}`：可选 `role`（白名单 user / vip /
  doc_admin / superadmin）+ `is_active`。**自我保护**：actor.id ===
  target.id 时禁止把超管降级（`不能降级自己的超级管理员权限`）也禁止把
  自己锁定（`不能锁定自己的账号`），返回 400。事务内 `with_for_update()`
  锁行避免并发覆盖。
- `POST /admin/users/{user_id}/reset-password`：body
  `{new_password}`（8-128 字符，pydantic Field 校验），复用
  `app.core.security.hash_password`，行级锁后写回 `password_hash`，返回
  `{ok: true, user_id, username}`。**不返回 password**，不写日志。

### 前端

- `frontend/src/api/index.js` adminApi 扩展：`listUsers / updateUser /
  resetUserPassword`。
- `frontend/src/router/index.js`：注册 `/admin/users → AdminUsersView`，
  `meta: { requiresAuth: true, requiresSuperadmin: true }`。
- `frontend/src/components/layout/AppSidebar.vue`：管理组追加「用户管理」
  入口，`Users` 图标。
- `frontend/src/views/AdminUsersView.vue`（新文件）：
  - 顶部筛选条：搜索框（用户名 / 邮箱，300ms debounce）+ 角色 select +
    状态 select（启用 / 已锁定）+ 刷新按钮。
  - 表格列：用户名（自身行追加「本人」Badge）/ 邮箱 / 角色（行内 select，
    切换即提交）/ 状态 Badge / 注册时间 / 操作（锁定 / 解锁 + 重置密码）。
  - **自我保护（前端层）**：`row.id === auth.currentUser.id` 时，超管行的
    role select 禁用、`is_active === true` 时锁定按钮禁用；后端仍兜底
    400。
  - **重置密码 UX**：点击「重置密码」在该行下方展开一行内嵌面板（用
    `Table` 的 colspan 6 实现，无需新 Dialog 组件），含 `password` 输入
    框（带显示 / 隐藏切换 + Enter 提交）+ 取消 / 保存按钮，提交后 toast
    并自动收起面板。
  - 分页：`PAGE_SIZE = 20`，offset 模式，复用拍卖列表的「上一页 / 下一
    页 + `1 – N / total`」样式。
  - 切换角色到 superadmin、锁定 / 解锁均走 `confirm()` 二次确认。

### 验证

- 后端 curl：列表 / 过滤 / 角色变更 / 锁定后登录被拒 / 重置密码后用新密
  码登录成功 / **自我降级** & **自我锁定** 均返回 400。
- Playwright 浏览器流：
  - 用 superadmin token 注入 localStorage 后访问 `/admin/users`，渲染 5
    条用户、`pageInfo "1 – 5 / 5"`；
  - 搜索 `qa` debounce 后 → 1 条结果；
  - 通过 select 把 `qa_check2` 改为 vip → DB `role=vip` 且行内 select 反
    映；
  - 点锁定按钮 → 行底色变浅、Badge 变「已锁定」、按钮翻为「解锁」、DB
    `is_active=f`；
  - 打开重置密码面板 → 输入 `BrowserQA9876!` → 保存后面板收起 → curl
    `/auth/login` 用新密码成功；
  - 搜索 `kbytetutu`（自身）→ 行带「本人」Badge、role select disabled、
    锁定按钮 disabled；后端 curl 自我降级 / 自我锁定均 400 兜底。

### 注意

- 第一次 `docker compose build frontend` 因 layer 缓存命中跳过了 `npm
  run build`，导致 `AdminUsersView` chunk 没出现在 bundle，须用
  `--no-cache` 重新构建。后续如再增视图请确认 `dist/assets` 已包含对应
  hash 文件。
- 暂未提供 "删除用户"。如需，建议改为软删除（标记 `is_active=false` +
   额外 `deleted_at` 列），避免破坏 `query_logs / billing_records` 外键。

---

## 冈瓦纳词典功能下线（2026-05-22）⊘

**原因**: 阿里云 ECS 出口（华北 2）从容器内 / 宿主机直接 `curl https://www.ganvana.com/searchDic` 都返 9-byte `Not Found`（`text/plain`）；本地开发机同样 POST 返 200 + JSON。
经容器内多次变体验证（带 `Origin/Referer/UA/Cookie/X-Requested-With`、试 `ganvana.com` 与 `www.ganvana.com` 双形式），全部 404。
排查结论：**该 ECS 网络出口被 ganvana 上游 CDN/WAF 拒绝**（推测是阿里云 IP 段反爬名单），nginx 反向代理无法绕过。
浏览器直连 `ganvana.com` 也被 CORS 阻断（无 `Access-Control-Allow-Origin`，`OPTIONS` preflight 返 404），无可行方案。

**改动**:

- `frontend/src/views/TaxonDetailView.vue`: 删除冈瓦纳 Card（含表单、结果列表、外链），删除
  `searchGanvana()` / `ganvana*` 状态、`watch(taxon.scientificname)` 自动触发钩子；
  顺手清理仅冈瓦纳使用的 import（`axios`、`Input`、`BookOpen`、`Search`、`Loader2`）。
- `frontend/vite.config.js`: 移除 `/ganvana` dev proxy。
- `frontend/nginx.conf`: 移除 `location /ganvana/` 反向代理块。

**保留**: 文档历史段（[`物种检索详情页 — 冈瓦纳词典 / WoRMS 链接重排`](#物种检索详情页--冈瓦纳词典--worms-链接重排-)）保留原状作为历史记录。
若未来网络恢复或换出口可访问 ganvana，恢复方法：从此 commit 之前的 git history 提取 4 个文件的 diff。

---

## Round 1 Bug 修复 — 本机部署与路由 (2026-05-22) ✅

**背景**: `./dev nuke && ./dev up && ./dev prod-import` 从零重建全栈时发现 3 个阻塞性 bug。修复涉及 3 个文件：`scripts/dev.sh`（`env_get` 缺 key 静默退出）、`frontend/nginx.conf`（变量化 proxy_pass 后 URI 塌缩）、`backend/app/api/v1/auction.py`（GET /search 被 item_no 路由捕获返回 422）。已推送 `origin/main`。

---

## Round 2 Bug修复 — UI 体验 & 查询日志 (2026-05-22) ✅

### 用户反馈修复

| # | 问题 | 修复 |
|---|------|------|
| 18 | 侧边栏「反馈建议」按钮贴在底部，视觉下沉 | `FeedbackTrigger.vue`: `mt-auto` → `px-3 mt-2 mb-auto`，上提到配额条与用户区之间 |
| 19 | 默认用户头像用缩写 (KB)，不够品牌化 | `AppSidebar.vue` + `ProfileView.vue`: `{{ initials }}` → `<img src="/logo.png">`，清理 `initials` computed |
| 20 | 登录仅支持用户名，不支持邮箱 | `auth_service.py`: `WHERE username = x` → 含 `@` 则 `WHERE email = x`，保持 JSON key 兼容；`LoginView.vue`: label `用户名` → `用户名 / 邮箱`，placeholder `用户名或邮箱` |

### 查询日志界面修复

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 21 | Top 关键词榜首永远是 auction 默认加载 JSON | `top_keywords` SQL 对所有 `query_type` 做 `GROUP BY`，首页空搜索 JSON 与有效查询混在一起 | `admin.py` → SQL 加 `AND query_type IN ('taxa', 'ai')`，仅统计名称/混合搜索 |
| 22 | IP 列显示 `172.18.0.1`（Docker 网关），无意义 | `get_client_ip()` 取 X-Forwarded-For 最左项，回退到 `request.client.host` | `request_ip.py` 重写：新增 `_PROXY_NETS` 跳过私有/代理 IP；`admin.py` → `QueryLogOut.display_ip` 对内部 IP 标 `(内网)` |
| 23 | 查询日志页无过滤控件，固定 100 条 | 后端 `query_recent` 无 keyword 参数，前端无过滤 UI | 后端加 `q` ILIKE 参数；前端新增「最近 N 条」(50/100/200/500) + 关键字搜索 + 过滤按钮 |
| 24 | 拍卖搜索默认仅显示上月数据，"eludens" 只 3 条 | 默认 `end_date_from/to` 限制为上月；无 relevance 排序 | `HomeView.vue` 移除默认日期过滤，改为全时段；`auction_service.py` 新增 `relevance` 排序（trigram 相似度 → 日期） |
| 25 | 科/尺寸/产地筛选功能弱 | family 是纯文本输入；size 不支持范围；locality 仅 ILIKE | family → 可搜索下拉框（`GET /auction/families`）；size → 数值范围 + 无数据勾选；locality → trigram 模糊匹配 |

### 本 Session 总变更

| 文件 | 改动 |
|------|------|
| `backend/app/api/v1/admin.py` | top_keywords SQL 限定 `taxa`/`ai`；query_recent 加 `q` 参数 + `display_ip` 字段 |
| `backend/app/core/request_ip.py` | 重写：`_PROXY_NETS` 跳过私有 IP；`get_display_ip()` 加 `(内网)` 标记 |
| `backend/app/services/auth_service.py` | `authenticate_user()` 支持 `@` 分支 → email 登录 |
| `frontend/src/views/LoginView.vue` | label `用户名 / 邮箱` + placeholder `用户名或邮箱` |
| `frontend/src/components/layout/AppSidebar.vue` | 头像换 logo 图片；清理 `initials` computed；反馈按钮位置上提 |
| `frontend/src/components/layout/FeedbackTrigger.vue` | `mt-auto` → `px-3 mt-2 mb-auto` |
| `frontend/src/views/ProfileView.vue` | 头像换 logo 图片；清理 `initials` computed |
| `frontend/src/views/AdminQueriesView.vue` | 新增最近条数选择器 + 关键字搜索；IP 列改用 `display_ip` |
| `backend/app/schemas/auction.py` | sort pattern 加 `relevance` 选项 |
| `frontend/src/components/ui/Checkbox.vue` | 新增 UI 组件 |
| `frontend/src/components/auction/AdvancedFilters.vue` | family 可搜索下拉 + size 范围 + no-size 勾选 |
| `frontend/src/views/HomeView.vue` | 移除默认日期过滤，默认排序改为 relevance，文案更新 |
| `frontend/src/api/index.js` | `recentQueries()` 加 `q` 参数 |

---

## Round 3 Bug修复 — 布局溢出 (2026-05-23) ✅

### 问题与修复

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 26 | 拍卖高级筛选框中 size/price 双输入框溢出网格边界 | `Input` 有 `w-full`，flex 容器内两个 `w-full` 互相挤压，无 `flex-1 min-w-0` | `AdvancedFilters.vue`: 双输入框加 `class="flex-1 min-w-0"`，中间分隔符加 `shrink-0`，外层 grid 加 `p-[6px]` |
| 27 | 物种检索页模式切换按钮（词法/智能）在窄屏右溢出 | 容器有 `shrink-0` 阻止收缩 | `TaxaSearchView.vue`: 移除模式切换 `div` 的 `shrink-0` |
| 28 | 物种检索筛选网格（阶元/状态/科/属）在窄屏 `grid-cols-2` 格子太挤 | 最窄屏（~320px）下 2 列容纳不下 label + select/input | `TaxaSearchView.vue`: `grid-cols-2` → `grid-cols-1 sm:grid-cols-2 md:grid-cols-4` |

### 涉及文件

| 文件 | 改动 |
|------|------|
| `frontend/src/components/auction/AdvancedFilters.vue` | 尺寸/价格输入 `flex-1 min-w-0` + `shrink-0` 分隔符 + `p-[6px]` |
| `frontend/src/views/TaxaSearchView.vue` | 移除 `shrink-0`；筛选网格加 `sm:` 断点单列 |

---

## 拍卖向量智能搜索 (2026-05-23) ✅

为拍卖检索添加基于 pgvector 的语义搜索能力，复用物种检索已有的混合搜索架构（pg_trgm 词法 + pgvector 向量 + RRF 融合）。

### 架构

```
用户搜索 "Conus gloriamaris"
       │
       ├─ mode="lexical"  → pg_trgm 模糊匹配（原有逻辑不变）
       ├─ mode="vector"   → 文本嵌入 → pgvector cosine 距离排序
       └─ mode="hybrid"   → lexical TOP-50 + vector TOP-50 → RRF 融合 TOP-30
                            无嵌入模型时自动回退 lexical
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `infra/postgres/init/07-auction-embeddings.sql` | `auction_embeddings` 表 + HNSW 索引（`halfvec(2000)`, `m=16, ef_construction=64`） |
| `backend/app/models/auction_embedding.py` | `AuctionEmbedding` ORM 模型（`HALFVEC(2000)`） |
| `backend/scripts/embed_auctions.py` | 批量嵌入脚本，组合 `name/family/locality/size/note` 为嵌入文本，复用 `embed_taxa.py` 的并发+批次模式 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `backend/app/models/__init__.py` | 注册 `AuctionEmbedding` |
| `backend/app/schemas/auction.py` | `AuctionSearchRequest` 新增 `mode: "lexical"\|"vector"\|"hybrid"` |
| `backend/app/services/auction_service.py` | 重构为 `_build_conditions` + `_lexical_ids` + `_vector_ids` + `_rrf_fuse`；`search_auctions()` 支持 `mode` 参数 |
| `backend/app/api/v1/auction.py` | `POST /search` 根据 mode 选择配额类型（hybrid→AI 配额），传递 `mode` + `user_id` |
| `backend/app/api/v1/admin.py` | 新增 `POST /embed/auction/run` + `/cancel` 管理端点 |
| `backend/app/api/v1/models.py` | 新增 `GET /admin/models/auction-embeddings/status` 拍卖嵌入覆盖率端点 |
| `backend/app/tasks/embedding_job.py` | 新增 `auction.embed_run` / `auction.embed_cancel` Celery 任务 |
| `frontend/src/views/HomeView.vue` | 搜索栏新增「词法/智能」模式切换按钮（Type / Sparkles 图标） |
| `frontend/src/views/AdminEmbeddingsView.vue` | 向量管理页新增「拍卖记录嵌入」区块：进度条 + 嵌入/重建/停止按钮，`load()` 并行拉取两个 status |
| `frontend/src/api/index.js` | 新增 `runAuctionEmbed`, `cancelAuctionEmbed`, `auctionEmbeddingsStatus` |

### 启用步骤

1. 在 Admin「模型配置」中添加一个 `purpose=embedding` 的模型（如 SiliconFlow Qwen3-Embedding-8B）
2. 进入「向量管理」点击拍卖记录区块的「嵌入剩余 N 条」
3. 前端搜索栏点击「智能」按钮即发送 `mode=hybrid`

---

## 物种检索阶元中文名显示 (2026-05-23) ✅

仅显示层支持中文阶元名（不影响搜索逻辑/不改物种数据）。从 `data_import/fenlei.xlsx` Sheet2 解析「拉丁→中文」映射，存入独立查找表，前端在分类阶元处显示 `拉丁 中文` 格式。

### 数据来源

- `data_import/fenlei.xlsx` Sheet2（实际表名 "Sheet2"，非 sheetnames 顺序第一个的 references sheet）
- 列结构：A-H 为高阶阶元（`中文 拉丁` 格式合并文本）；J=科拉丁名；L=科中文名
- 解析结果：8 class + 14 subclass + 5 superorder + 6 order + 14 suborder + 77 infraorder + 768 family = **892 条**

### 数据覆盖率（DB 中相关阶元能匹配到中文名的数量）

| 阶元 | 覆盖 |
|------|------|
| Class | 7/15 |
| Order | 55/100 |
| Family | 765/1489 |

缺漏的不显示（按用户要求）。

### 新增/修改文件

| 文件 | 改动 |
|------|------|
| `infra/postgres/init/08-taxon-name-zh.sql` | 建表 + **内置 894 条 seed**（xlsx 解析结果 + Animalia/Mollusca 手填）；`ON CONFLICT DO NOTHING` 幂等；新部署自动加载 |
| `backend/scripts/import_taxon_zh.py` | 解析 xlsx 进 DB（默认）；`--emit-sql` 模式生成上面的 init SQL；含 `SEED_ENTRIES`（kingdom/phylum） |
| `backend/requirements.txt` | 新增 `openpyxl>=3.1`（仅 `--emit-sql` 维护用）|
| `backend/app/api/v1/taxa.py` | 新增 `GET /taxa/rank-names-zh` **公开端点**（无需登录），返回 `{latin: chinese}` 字典；**必须放在 `/{aphia_id}` 路由前**否则会被 int 路径转换器吞掉返回 401 |
| `frontend/src/api/index.js` | `taxaApi.rankNamesZh()` |
| `frontend/src/views/TaxonDetailView.vue` | `zhNames` ref + `withZh()` helper；`classificationDisplay` 中所有阶元 value 包装为 `Latin 中文` |
| `frontend/src/views/TaxaSearchView.vue` | `zhName()` 函数；搜索结果列表中 `family`/`class` 显示中文 |

### 启用步骤

数据已内置到 init SQL，**新部署 (`docker compose up`) 自动加载**，无需运行导入脚本。

```bash
docker compose up -d
docker compose restart frontend  # 静态构建产物，需重建镜像才生效新前端代码
```

### 维护：xlsx 数据更新后重新生成 seed

```bash
# 1. 把新 xlsx 放到 backend:/app/data_import/fenlei.xlsx
docker compose cp data_import/fenlei.xlsx backend:/app/data_import/fenlei.xlsx
# 2. 输出新 seed SQL
docker compose exec backend python -m scripts.import_taxon_zh --emit-sql \
    > infra/postgres/init/08-taxon-name-zh.sql
# 3. 提交。新 DB 自动加载；运行中 DB 可手动应用：
docker compose exec -T postgres psql -U mollusc -d molluscai \
    < infra/postgres/init/08-taxon-name-zh.sql
```

新增 `SEED_ENTRIES` 列表（脚本里硬编码的 kingdom/phylum 等 xlsx 不包含的阶元），编辑后重跑 `--emit-sql`。

### 关键决策

1. **不改 `taxa` / `taxa_vernaculars` 表** — Chinese 名是阶元级别的（非物种级），新建独立查找表更简单
2. **前端一次性加载全表** — 892 条 ≈ 30 KB，比每次详情请求都 JOIN 高效；首次进入搜索/详情页时懒加载，后续复用
3. **路由顺序坑** — FastAPI 路由按声明顺序匹配，`/{aphia_id}` 用 `int` 转换器，但 `rank-names-zh` 实际 401 因为 path 验证失败时直接 fallthrough 到 auth dependency。**必须把字面量路由放前面**

---

## 运行命令

```bash
# 启动全部服务
./dev up

# 仅重启后端（代码修改后）
./dev restart backend

# 仅重启 celery-worker（任务代码修改后）
./dev restart celery-worker

# 查看日志
./dev logs backend
./dev logs celery-worker

# 触发采集（需 ADMIN 环境变量）
./dev scrape 20
./dev images 10

# 全栈健康检查
./dev status

# WoRMS 数据导入（参见上文 "WoRMS 数据全字段导入"）
./dev worms-import data_import/worms_mollusca.sqlite.gz
./dev prod-import data_import/worms_mollusca.sqlite.gz \
                  data_import/postgres_backup.sql

# 清空重建
./dev nuke && ./dev up && ./dev seed
```

## 访问地址

| 入口 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9003 |
