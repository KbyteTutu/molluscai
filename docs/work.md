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

## 当前进行中: P2.0 — 拍卖详情页布局优化

### 问题
`AuctionDetailView.vue` (~301 行) 因新增分类学校验区块而显得拥挤，纵向过长。

### 计划
1. 重新排列：图片轮播 → 元数据卡片 → 操作按钮 → 分类学校验（折叠）
2. 考虑将"分类学校验"与元数据卡片合并或折叠
3. 响应式验证
4. 完成后提交所有变更

---

## 待解决问题

### WoRMS Dump 脚本（P2+ 再做）
- `scripts/worms/worms_dump.py` — 独立爬取脚本，输出 SQLite `.gz`
- 新增 classification / children / attributes / external_ids 表
- 默认 16 并发
- 需 `scp` 传回后导入
- **当前 blocked** — 向量化任务与业务服务不冲突，不需要重启

### 未提交变更
- 所有 P1.5~P2.0 变更均为 uncommitted（约 108 个文件）
- 需在布局完成后统一提交

---

## P0-P6 实施计划（更新）

| 阶段 | 内容 | 状态 |
|------|------|------|
| **P0 — 基础骨架** | Docker + PostgreSQL + FastAPI + 用户认证 + 拍卖搜索 | ✅ 已完成 |
| **P0.5 — 增量采集** | Scraper Celery + 图片下载 MinIO + 管理触发接口 | ✅ 已完成 |
| **P1.5 — 前端现代化** | Reka UI + Tailwind v4 + 双主题 + 响应式 | ✅ 已完成 |
| **P1.6 — 拍卖增强** | 搜索改进 + 图片修复 + 拍品对比 + 详情页 | ✅ 已完成 |
| **P1.7 — 物种分类** | taxa 表 + 向量化 + 混合搜索 + RRF | ✅ 已完成 |
| **P1.8 — 分类学匹配** | auction→taxon 匹配 + 前端区块 | ✅ 已完成 |
| **P1.9 — 模型管理** | LLM model CRUD + 用量 + 嵌入管理 UI | ✅ 已完成 |
| **P2.0 — 布局优化** | AuctionDetailView 布局重排 | 🔄 进行中 |
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
