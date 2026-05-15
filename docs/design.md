# MolluscAI 项目实施设计方案

## 一、项目总览

MolluscAI 是一个全新的**基于 RAG（检索增强生成）的智能贝壳知识平台**。用户可通过自然语言（中/英/拉丁文）提问，系统自动检索知识库文献并结合 LLM 生成回答。平台同时整合 shellauction.net 拍卖数据查询功能，提供结构化搜索能力。

核心功能模块：拍卖数据查询、知识库检索与问答、用户与权限系统、可扩展收费系统。全栈 Docker 部署。

## 二、技术栈选型

| 层面 | 技术 | 理由 |
|------|------|------|
| **后端框架** | FastAPI (Python 3.11+) | 原生 async、自带 OpenAPI 文档、比 Flask 性能更好 |
| **前端框架** | Vue 3 + Vite + Pinia + Vue Router + Element Plus | 成熟的 Vue 生态，组件化开发 |
| **数据库** | PostgreSQL 16 (pgvector + pg_trgm) | todo.md 明确要求 postgres；pgvector 替代 Milvus 简化部署 |
| **向量检索** | pgvector (替代 Milvus) | 减少一个组件，10 万级向量 pgvector 完全胜任 |
| **缓存/队列** | Redis | 会话管理 + 异步任务队列 |
| **任务队列** | Celery + Redis | 文献处理为后台长任务 |
| **对象存储** | MinIO | 本地部署的 S3 兼容存储，存图片/PDF |
| **OCR** | GLM-OCR (智谱 API) | todo.md 指定 |
| **Embedding** | Qwen3-VL-Embedding-8B (SiliconFlow API) | todo.md 指定，支持图文双通路 |
| **LLM 生成** | DeepSeek-V4-Flash | todo.md 指定 |
| **部署** | Docker Compose | todo.md 明确要求 |

> **关于 pgvector vs Milvus 的取舍**: todo.md 中提到 Milvus，但考虑到：(1) 向量规模约 10 万级，pgvector 完全够用；(2) 已有 PostgreSQL 减少运维负担；(3) Docker 部署更轻量。如果后续规模到百万级，再迁移 Milvus 不迟。

## 三、项目目录结构

```
molluscai/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                    # 数据库迁移
│   │   └── versions/
│   ├── alembic.ini
│   └── app/
│       ├── main.py                 # FastAPI 入口
│       ├── config.py               # 配置管理 (pydantic-settings)
│       ├── database.py             # SQLAlchemy async engine & session
│       ├── models/                 # SQLAlchemy ORM 模型
│       │   ├── user.py
│       │   ├── auction.py          # shellauction 拍卖数据
│       │   ├── document.py         # 知识库文献
│       │   ├── chunk.py            # 文本/图像 chunk + 向量
│       │   ├── billing.py          # 收费记录
│       │   └── model_config.py     # 模型 API 配置 + 调用开销记录
│       ├── schemas/                # Pydantic 请求/响应 schema
│       │   ├── user.py
│       │   ├── auction.py
│       │   ├── document.py
│       │   ├── billing.py
│       │   └── model_config.py     # 模型配置 + 开销
│       ├── api/                    # API 路由
│       │   ├── v1/
│       │   │   ├── auth.py         # 登录/注册/JWT
│       │   │   ├── auction.py      # 拍卖数据搜索
│       │   │   ├── knowledge.py    # RAG 检索 + 问答
│       │   │   ├── documents.py    # 文献管理 (上传/列表/删除)
│       │   │   ├── users.py        # 用户管理
│       │   │   ├── billing.py      # 收费/余额
│       │   │   └── model_config.py # 模型 API 配置管理 (superadmin)
│       │   └── deps.py             # 依赖注入 (当前用户、权限校验)
│       ├── services/               # 业务逻辑层
│       │   ├── auth_service.py
│       │   ├── auction_service.py
│       │   ├── rag_service.py      # RAG 检索 pipeline
│       │   ├── document_service.py
│       │   └── billing_service.py
│       ├── tasks/                  # Celery 异步任务
│       │   ├── celery_app.py
│       │   ├── pdf_pipeline.py     # PDF 解析总控
│       │   ├── ocr_task.py         # GLM-OCR 调用
│       │   ├── metadata_task.py    # DeepSeek 元数据抽取
│       │   ├── embedding_task.py   # Qwen3-VL-Embedding
│       │   ├── taxon_verify.py     # MolluscaBase 学名校对
│       │   └── image_scraper.py    # 拍卖图片下载保存
│       ├── core/                   # 基础设施
│       │   ├── security.py         # JWT + 密码哈希
│       │   ├── rate_limiter.py     # API 限流 (防爬)
│       │   └── exceptions.py       # 统一异常处理
│       └── utils/
│           ├── pdf_parser.py       # PyMuPDF 解析
│           ├── chunker.py          # 语义切分
│           ├── llm_client.py       # DeepSeek 客户端封装
│           ├── embedding_client.py # Qwen3-VL-Embedding 封装
│           └── ocr_client.py       # GLM-OCR 封装
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/index.js
│       ├── stores/                 # Pinia stores
│       │   ├── auth.js
│       │   └── search.js
│       ├── views/
│       │   ├── LoginView.vue
│       │   ├── AuctionSearch.vue   # 拍卖数据搜索
│       │   ├── KnowledgeChat.vue   # RAG 问答界面
│       │   ├── DocumentManager.vue # 文献管理 (管理员)
│       │   └── UserProfile.vue
│       ├── components/
│       │   ├── SearchForm.vue
│       │   ├── ResultTable.vue
│       │   ├── ImageModal.vue
│       │   ├── ChatWindow.vue
│       │   └── UploadDialog.vue
│       └── api/                    # Axios 封装
│           └── index.js
├── scraper/                        # 数据采集
│   ├── Dockerfile
│   └── scraper.py                  # shellauction.net async 爬虫 + 图片下载
└── old/                            # 旧版代码 (仅供参考)
```

## 四、数据库设计 (PostgreSQL)

### 4.1 用户与权限

**四种角色定义**：

| 角色 | 标识 | 说明 |
|------|------|------|
| 普通用户 | `user` | 基础搜索和问答，每日有次数限制 |
| 会员 | `vip` | 更高的使用次数上限，解锁额外功能（如导出、高级筛选） |
| 文献管理员 | `doc_admin` | 管理知识库文献的上传、删除、处理状态 |
| 超级管理员 | `superadmin` | 全部权限：用户管理、模型配置、开销查看、系统设置 |

> 注意：角色之间**不是严格层级关系**。`doc_admin` 拥有文献管理权限但不一定有 VIP 功能，`vip` 也不能管理文献。只有 `superadmin` 拥有全部权限。

```sql
-- 用户表
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(50) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'user',
                  -- 'superadmin' | 'doc_admin' | 'vip' | 'user'
    balance       DECIMAL(10,2) DEFAULT 0.00,
    daily_query_limit INT,         -- 每日查询次数上限，NULL 表示使用角色默认值
    created_at    TIMESTAMPTZ DEFAULT now(),
    is_active     BOOLEAN DEFAULT true
);

-- 角色默认配额表
CREATE TABLE role_quotas (
    role              VARCHAR(20) PRIMARY KEY,
    daily_auction_limit INT NOT NULL,     -- 拍卖搜索 次/天
    daily_rag_limit     INT NOT NULL,     -- RAG 问答 次/天
    features          JSONB DEFAULT '{}', -- 角色专属功能开关
                      -- 如 {"export": true, "advanced_filter": true, "batch_query": true}
    rate_limit_per_min  INT NOT NULL      -- API 每分钟请求上限
);

-- 预设值
INSERT INTO role_quotas VALUES
    ('user',       20,   5,   '{}',                                                     30),
    ('vip',        200,  50,  '{"export":true,"advanced_filter":true,"batch_query":true}', 120),
    ('doc_admin',  200,  50,  '{"export":true}',                                         120),
    ('superadmin', -1,   -1,  '{}',                                                     -1);
    -- -1 表示无限制

-- 查询记录
CREATE TABLE query_logs (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    query_type VARCHAR(20),  -- 'auction' | 'rag'
    result_count INT,
    cost       DECIMAL(10,4) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 4.2 拍卖数据

```sql
CREATE TABLE auctions (
    id            SERIAL PRIMARY KEY,
    item_no       INTEGER UNIQUE NOT NULL,  -- 站点拍品编号，加UNIQUE防重复
    name          TEXT,
    family        TEXT,
    size          TEXT,
    locality      TEXT,
    note          TEXT,
    seller        TEXT,
    start_price   DECIMAL(10,2),
    final_price   DECIMAL(10,2),
    end_date      DATE,                     -- 改为 DATE 类型
    buyer         TEXT,
    is_sold       BOOLEAN GENERATED ALWAYS AS (buyer IS NOT NULL AND buyer NOT LIKE '%no Bids%') STORED,
    images_local  TEXT[],                   -- MinIO 路径数组 (本地缓存)
    images_origin TEXT[],                   -- 原始 URL 数组
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_auctions_name_trgm ON auctions USING GIN (name gin_trgm_ops);
CREATE INDEX idx_auctions_family ON auctions (family);
CREATE INDEX idx_auctions_end_date ON auctions (end_date);
```

### 4.3 知识库 (文献 + chunks + 向量)

```sql
-- 安装扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 文献表
CREATE TABLE documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title         TEXT,
    authors       TEXT[],
    year          INTEGER,
    journal       TEXT,
    doi           TEXT,
    abstract      TEXT,
    taxa_mentioned TEXT[],
    higher_taxa   JSONB,          -- {"family":[], "order":[], "class":[]}
    geographic_scope TEXT[],
    content_type  VARCHAR(50),    -- taxonomy|ecology|phylogeny|anatomy|review
    keywords      TEXT[],
    doc_category  VARCHAR(30) NOT NULL, -- 'paper' | 'literature' | 'old_literature'
    ocr_model     VARCHAR(50),    -- 使用的 OCR 模型名
    llm_model     VARCHAR(50),    -- 使用的元数据抽取模型名
    file_path     TEXT,           -- MinIO 中 PDF 原件路径
    total_pages   INTEGER,
    status        VARCHAR(20) DEFAULT 'pending',
                  -- 'pending' | 'processing' | 'completed' | 'failed'
    uploaded_by   UUID REFERENCES users(id),
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- 文本 chunk 表 (带向量)
CREATE TABLE text_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_num    INTEGER,
    section     TEXT,
    content     TEXT NOT NULL,
    embedding   vector(3584),     -- Qwen3-VL-Embedding 维度
    taxa        TEXT[],
    chunk_idx   INTEGER,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chunks_embedding ON text_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 图像表 (带向量)
CREATE TABLE image_chunks (
    id          BIGSERIAL PRIMARY KEY,
    doc_id      UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_num    INTEGER,
    image_path  TEXT NOT NULL,     -- MinIO 路径
    caption     TEXT,
    figure_type VARCHAR(50),      -- shell_photo|radula_SEM|anatomy|map|phylogeny
    taxa        TEXT[],
    embedding   vector(3584),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_images_embedding ON image_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

### 4.4 收费系统

```sql
CREATE TABLE billing_records (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    amount      DECIMAL(10,4) NOT NULL,  -- 正数=充值，负数=消费
    action_type VARCHAR(30),  -- 'recharge' | 'rag_query' | 'auction_search'
    description TEXT,
    balance_after DECIMAL(10,2),
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 定价规则表 (可扩展)
CREATE TABLE pricing_rules (
    id          SERIAL PRIMARY KEY,
    action_type VARCHAR(30) UNIQUE NOT NULL,
    price       DECIMAL(10,4) NOT NULL,   -- 每次调用价格
    free_quota  INTEGER DEFAULT 0,         -- 免费额度/天
    vip_price   DECIMAL(10,4),            -- VIP 价格
    is_active   BOOLEAN DEFAULT true
);
```

### 4.5 模型 API 配置与调用开销

```sql
-- 模型 API 配置表 (仅 superadmin 可操作)
CREATE TABLE model_configs (
    id          SERIAL PRIMARY KEY,
    model_name  VARCHAR(100) UNIQUE NOT NULL,  -- 如 'glm-ocr', 'deepseek-v4-flash', 'qwen3-vl-embedding-8b'
    provider    VARCHAR(50) NOT NULL,          -- 'zhipu' | 'deepseek' | 'siliconflow'
    api_key     TEXT NOT NULL,                 -- 加密存储
    base_url    TEXT,                          -- API 端点
    model_id    VARCHAR(100),                  -- 实际调用时的 model 参数
    purpose     VARCHAR(30) NOT NULL,          -- 'ocr' | 'llm' | 'embedding'
    price_input  DECIMAL(10,6),               -- 输入单价 (元/千token 或 元/页)
    price_output DECIMAL(10,6),               -- 输出单价
    price_unit  VARCHAR(20) DEFAULT 'per_1k_tokens', -- 'per_1k_tokens' | 'per_page' | 'per_image'
    is_active   BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_by  UUID REFERENCES users(id)
);

-- 模型调用开销记录表
CREATE TABLE model_usage_logs (
    id            BIGSERIAL PRIMARY KEY,
    model_config_id INT REFERENCES model_configs(id),
    model_name    VARCHAR(100) NOT NULL,
    purpose       VARCHAR(30) NOT NULL,        -- 'ocr' | 'llm_metadata' | 'llm_query_parse' | 'llm_generate' | 'embedding_text' | 'embedding_image'
    doc_id        UUID REFERENCES documents(id) ON DELETE SET NULL,  -- 关联文献 (如有)
    user_id       UUID REFERENCES users(id),   -- 触发者
    input_tokens  INTEGER,
    output_tokens INTEGER,
    input_pages   INTEGER,                     -- OCR 专用
    input_images  INTEGER,                     -- 图像 embedding 专用
    cost          DECIMAL(10,6) NOT NULL,      -- 本次调用计算出的费用
    latency_ms    INTEGER,                     -- 响应耗时
    status        VARCHAR(20) DEFAULT 'success', -- 'success' | 'failed' | 'timeout'
    error_message TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_usage_model ON model_usage_logs (model_name, created_at);
CREATE INDEX idx_usage_doc ON model_usage_logs (doc_id);
CREATE INDEX idx_usage_user ON model_usage_logs (user_id, created_at);
```

## 五、核心模块设计

### 5.1 用户认证与权限

- JWT access_token (30min) + refresh_token (7d)
- 密码用 bcrypt 哈希
- 权限校验采用**基于角色的权限集合**，而非简单层级比较：

```python
# api/deps.py
from enum import Flag, auto

class Permission(Flag):
    SEARCH_AUCTION = auto()     # 拍卖搜索
    SEARCH_RAG     = auto()     # RAG 问答
    EXPORT         = auto()     # 导出结果
    ADVANCED_FILTER = auto()    # 高级筛选
    BATCH_QUERY    = auto()     # 批量查询
    MANAGE_DOCS    = auto()     # 文献管理 (上传/删除)
    MANAGE_USERS   = auto()     # 用户管理
    MANAGE_MODELS  = auto()     # 模型 API 配置
    VIEW_USAGE     = auto()     # 查看模型开销

# 角色 → 权限映射
ROLE_PERMISSIONS = {
    'user':       Permission.SEARCH_AUCTION | Permission.SEARCH_RAG,
    'vip':        Permission.SEARCH_AUCTION | Permission.SEARCH_RAG
                  | Permission.EXPORT | Permission.ADVANCED_FILTER | Permission.BATCH_QUERY,
    'doc_admin':  Permission.SEARCH_AUCTION | Permission.SEARCH_RAG
                  | Permission.EXPORT | Permission.MANAGE_DOCS,
    'superadmin': ~Permission(0),  # 全部权限
}

class RequirePermission:
    def __init__(self, perm: Permission):
        self.perm = perm

    async def __call__(self, current_user: User = Depends(get_current_user)):
        role_perms = ROLE_PERMISSIONS[current_user.role]
        if not (role_perms & self.perm):
            raise HTTPException(403, "权限不足")
        return current_user

# 使用示例
@router.post("/documents/upload")
async def upload(user=Depends(RequirePermission(Permission.MANAGE_DOCS))):
    ...

@router.get("/model-configs")
async def list_models(user=Depends(RequirePermission(Permission.MANAGE_MODELS))):
    ...
```

**次数限制检查**（在权限校验后执行）：

```python
# api/deps.py
async def check_quota(user: User, query_type: str, db: AsyncSession):
    """检查用户当日剩余配额"""
    quota = user.daily_query_limit  # 个人覆盖值
    if quota is None:
        role_quota = await db.get(RoleQuota, user.role)
        quota = role_quota.daily_rag_limit if query_type == 'rag' else role_quota.daily_auction_limit
    if quota == -1:
        return  # 无限制
    today_count = await count_today_queries(db, user.id, query_type)
    if today_count >= quota:
        raise HTTPException(429, f"今日{query_type}查询已达上限 ({quota}次)")
```

### 5.2 模型 API 配置管理 (superadmin)

- 所有外部模型的 API Key、端点、单价均存于 `model_configs` 表，仅 superadmin 可增删改
- API Key 使用 AES 加密存储，解密密钥从环境变量读取
- 文献处理 Pipeline 和 RAG 检索按 `purpose` 字段动态获取当前激活的模型配置，不硬编码
- 不同 `doc_category` 可绑定不同的 OCR/LLM 模型：

```python
# services/model_config_service.py
async def get_active_model(purpose: str, doc_category: str = None) -> ModelConfig:
    """根据用途和文献分类获取当前激活的模型配置"""
    query = select(ModelConfig).where(
        ModelConfig.purpose == purpose,
        ModelConfig.is_active == True
    )
    if doc_category:
        # 优先匹配 doc_category 专属配置，否则回退到默认
        ...
    return (await db.execute(query)).scalar_one()
```

### 5.3 模型开销追踪

- 每次调用外部模型 API 时，统一通过包装函数记录到 `model_usage_logs`
- 记录维度：模型名、用途、token 数/页数/图片数、费用、耗时、成功/失败
- 关联 `doc_id`（文献处理场景）和 `user_id`（用户查询场景），支持按文献、按用户、按模型维度汇总

```python
# utils/llm_client.py (所有模型客户端统一使用此模式)
async def call_with_tracking(
    model_config: ModelConfig,
    purpose: str,
    call_fn,           # 实际 API 调用函数
    *,
    doc_id: str = None,
    user_id: str = None,
):
    start = time.monotonic()
    try:
        result = await call_fn()
        cost = calculate_cost(model_config, result.usage)
        await log_usage(model_config, purpose, result.usage, cost,
                        doc_id=doc_id, user_id=user_id,
                        latency_ms=int((time.monotonic() - start) * 1000),
                        status="success")
        return result
    except Exception as e:
        await log_usage(model_config, purpose, None, 0,
                        doc_id=doc_id, user_id=user_id,
                        latency_ms=int((time.monotonic() - start) * 1000),
                        status="failed", error_message=str(e))
        raise
```

### 5.4 文献处理 Pipeline (Celery 异步任务链)

```
上传PDF → celery chain:
  ① pdf_parse_task:   PyMuPDF 拆页 + 图文分离 → 存 MinIO
  ② ocr_task:         GLM-OCR 逐页识别 → Markdown → 存 MinIO + DB
  ③ metadata_task:    DeepSeek 抽取元数据 → 存 documents 表
  ④ taxon_verify_task: MolluscaBase API 校对学名
  ⑤ chunk_task:       语义切分 → text_chunks 表
  ⑥ embedding_task:   Qwen3-VL-Embedding 批量 embedding → 更新向量字段
  ⑦ image_embed_task: 图版 embedding → image_chunks 表
```

**关键设计**：
- 每步结果落盘（MinIO + DB），支持断点续传
- doc_category 为 `'paper'` / `'literature'` / `'old_literature'`，可分别配置 OCR 模型和 LLM 模型
- OCR 产出的 Markdown 中 `![](...)` 引用的图片存 MinIO，替换为本地 URL
- 以 `doc_id + page_num` 为幂等 key，任何环节中断可续跑
- API 限流用 `asyncio` + `semaphore` 做并发控制，失败重试用指数退避

### 5.5 RAG 检索 Pipeline

```
用户提问
  → ① DeepSeek 查询理解 (意图/学名/过滤条件/改写)
  → ② pgvector 稠密检索 text_chunks (cosine similarity)
     + pg_trgm BM25-like 检索 (学名精确召回)
     + 可选 image_chunks 检索
  → ③ RRF 融合排序
  → ④ DeepSeek 生成带引用的回答
  → 返回 {answer, sources[], images[]}
```

查询理解 prompt:
```python
QUERY_PARSE_PROMPT = """解析用户查询，输出JSON：
{
  "intent": "text_search|image_search|both",
  "taxa": ["识别到的学名或类群"],
  "geographic": ["地理范围"],
  "year_range": [起, 止] 或 null,
  "content_focus": "anatomy|taxonomy|ecology|...",
  "rewritten_query": "改写后的检索query，英文"
}
用户查询: {query}"""
```

生成回答 prompt:
```python
GENERATION_PROMPT = """你是软体动物学研究助手。基于以下文献片段回答用户问题。
要求：
1. 只使用提供的资料，不要编造
2. 引用时标注[文献ID-页码]
3. 学名用斜体（Markdown _Genus species_）
4. 如果资料不足，明确说明

用户问题：{query}

相关文字资料：
{text_chunks}

相关图版（已提供图像ID和图注，用户可另行查看）：
{image_refs}
"""
```

### 5.6 拍卖图片保存

针对已中拍的拍品图片保存：

- Celery Beat 定时任务，扫描 `is_sold=true AND images_local IS NULL` 的记录
- 下载原始图片到 MinIO，写入 `images_local` 字段
- 前端优先展示本地缓存图片，原始 URL 失效时无缝降级

### 5.7 反爬与安全

#### 限流

- `slowapi`，按 `role_quotas.rate_limit_per_min` 动态限流：
  - 未登录：仅可访问注册/登录接口，**所有查询接口均需登录**
  - 普通用户：30 req/min
  - 会员/文献管理员：120 req/min
  - 超级管理员：不限

#### 验证码机制 (核心反爬手段)

短时间内连续查询触发验证码，阻断脚本批量爬取：

```sql
-- 验证码会话表
CREATE TABLE captcha_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    answer      VARCHAR(10) NOT NULL,       -- 正确答案 (哈希存储)
    created_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,       -- 5 分钟过期
    verified    BOOLEAN DEFAULT false
);
```

**触发策略**（存 Redis，滑动窗口计数）：

| 条件 | 普通用户 | 会员 |
|------|---------|------|
| 每 N 次查询弹一次验证码 | 每 5 次 | 每 20 次 |
| 窗口时间 | 10 分钟 | 10 分钟 |
| 验证码连续失败 3 次 | 锁定账号 30 分钟 | 锁定账号 30 分钟 |
| 注册接口 | 每次都需要验证码 | — |

```python
# core/captcha.py
import redis.asyncio as redis

CAPTCHA_RULES = {
    'user':      {'threshold': 5,  'window': 600},
    'vip':       {'threshold': 20, 'window': 600},
    'doc_admin': {'threshold': 20, 'window': 600},
    'superadmin': None,  # 不触发
}

async def need_captcha(user_id: str, role: str, r: redis.Redis) -> bool:
    rule = CAPTCHA_RULES.get(role)
    if rule is None:
        return False
    key = f"query_count:{user_id}"
    count = await r.get(key)
    return count is not None and int(count) >= rule['threshold']

async def increment_query_count(user_id: str, role: str, r: redis.Redis):
    rule = CAPTCHA_RULES.get(role)
    if rule is None:
        return
    key = f"query_count:{user_id}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, rule['window'])
    await pipe.execute()

async def reset_query_count(user_id: str, r: redis.Redis):
    """验证码通过后重置计数"""
    await r.delete(f"query_count:{user_id}")
```

**验证码类型**：后端生成图形验证码（`captcha` 库），返回 base64 图片 + session_id。前端提交 session_id + 用户输入，校验通过后重置计数器。

**查询接口调用流程**：

```
客户端请求查询
  → 后端检查 Redis 滑动窗口计数
  → 未达阈值：正常执行查询，计数 +1
  → 已达阈值：返回 HTTP 428，body 含 captcha_required: true
      → 客户端调用 GET /api/v1/captcha 获取验证码图片
      → 客户端提交 POST /api/v1/captcha/verify {session_id, answer}
      → 校验通过 → 重置计数 → 客户端重新发起查询
      → 校验失败 → 失败计数 +1，连续 3 次失败 → 锁定账号
```

#### 行为检测

- 请求指纹：记录 User-Agent、Accept-Language、请求间隔模式
- 异常检测：同一账号短时间内请求间隔过于均匀（机器特征）→ 强制触发验证码
- IP 关联：同一 IP 注册多个账号 → 标记可疑，superadmin 可查看

```sql
-- 安全事件日志
CREATE TABLE security_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    event_type  VARCHAR(30) NOT NULL,
                -- 'captcha_triggered' | 'captcha_failed' | 'account_locked'
                -- | 'suspicious_pattern' | 'multi_account_ip'
    ip_address  INET,
    user_agent  TEXT,
    detail      JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

#### 其他防护

- JWT + HttpOnly Cookie
- CORS 白名单
- 图片通过后端代理返回，不暴露 MinIO 直链
- API 响应不返回总数据量，分页游标式翻页（防止枚举总量）
- 搜索结果单次上限 50 条，禁止深度翻页（offset > 500 拒绝）

## 六、API 端点设计

```
# 公开接口 (无需登录)
POST   /api/v1/auth/register         # 注册 (需验证码)
POST   /api/v1/auth/login             # 登录
POST   /api/v1/auth/refresh           # 刷新 token

# 以下所有接口均需登录 ──────────────────────────

POST   /api/v1/auth/logout            # 登出

# 验证码
GET    /api/v1/captcha                # 获取验证码图片 (返回 base64 + session_id)
POST   /api/v1/captcha/verify         # 校验验证码 {session_id, answer}

# 拍卖数据搜索 (登录用户)
POST   /api/v1/auction/search         # 结构化搜索
GET    /api/v1/auction/{item_no}       # 单品详情

# RAG 知识问答 (登录用户)
POST   /api/v1/knowledge/ask          # 自然语言提问
POST   /api/v1/knowledge/search       # 纯检索 (不生成回答)

# 文献管理 (doc_admin / superadmin)
POST   /api/v1/documents/upload       # 上传 PDF
GET    /api/v1/documents              # 文献列表
GET    /api/v1/documents/{id}         # 文献详情 + 处理状态
DELETE /api/v1/documents/{id}         # 删除文献
GET    /api/v1/documents/{id}/chunks  # 查看该文献的 chunks

# 用户管理 (superadmin)
GET    /api/v1/users                  # 用户列表
PATCH  /api/v1/users/{id}/role        # 修改角色
PATCH  /api/v1/users/{id}/balance     # 调整余额

# 模型 API 配置 (superadmin)
GET    /api/v1/model-configs              # 模型配置列表
POST   /api/v1/model-configs              # 新增模型配置
PATCH  /api/v1/model-configs/{id}         # 修改模型配置 (API Key/端点/单价等)
DELETE /api/v1/model-configs/{id}         # 删除模型配置
PATCH  /api/v1/model-configs/{id}/toggle  # 启用/停用模型

# 模型开销统计 (superadmin)
GET    /api/v1/model-usage/summary        # 开销汇总 (按模型/按时间段)
GET    /api/v1/model-usage/by-document    # 按文献维度查看开销
GET    /api/v1/model-usage/by-user        # 按用户维度查看开销
GET    /api/v1/model-usage/logs           # 原始调用日志 (分页)

# 安全监控 (superadmin)
GET    /api/v1/security/events            # 安全事件日志 (验证码触发/失败/锁定/可疑行为)
GET    /api/v1/security/locked-users      # 当前被锁定的用户列表
POST   /api/v1/security/unlock/{user_id}  # 手动解锁用户

# 收费
GET    /api/v1/billing/balance        # 查余额
GET    /api/v1/billing/history        # 消费记录
POST   /api/v1/billing/recharge       # 充值 (预留接口)

# 个人
GET    /api/v1/me                     # 个人信息
GET    /api/v1/me/queries             # 查询历史
```

## 七、Docker Compose 架构

```yaml
services:
  postgres:       # PostgreSQL 16 + pgvector + pg_trgm
  redis:          # 缓存 + Celery broker
  minio:          # 对象存储 (图片/PDF)
  backend:        # FastAPI (uvicorn)
  celery-worker:  # 文献处理 worker
  celery-beat:    # 定时任务 (图片下载等)
  frontend:       # Vue 3 + Nginx
  scraper:        # 数据采集 (可选，按需启动)
```

## 八、实施分期

| 阶段 | 内容 |
|------|------|
| **P0 - 基础骨架** | Docker Compose + PostgreSQL + FastAPI 骨架 + 用户认证 + 拍卖数据搜索 |
| **P1 - 用户体系** | 完整权限系统 + 查询记录 + 前端登录/注册 |
| **P2 - 知识库核心** | PDF 上传 + 解析 Pipeline (OCR → 元数据 → 切分 → Embedding) |
| **P3 - RAG 检索** | 混合检索 + 生成回答 + 前端问答界面 |
| **P4 - 收费系统** | 计费逻辑 + 余额管理 + 前端充值页 |
| **P5 - 安全加固** | 限流 + 反爬 + 图片缓存 + HTTPS |
| **P6 - 优化** | 检索质量调优 + 前端美化 + 性能优化 |

## 九、旧版问题规避

以下为 old/ 中旧版代码存在的问题，新项目设计中已规避：

| 旧版问题 | 新项目方案 |
|---------|-------------|
| `name` 无 GIN 索引 | 建 `gin_trgm_ops` 索引 |
| 拍品编号无 UNIQUE 约束，可插入重复 | `item_no INTEGER UNIQUE NOT NULL` |
| 数据库密码明文硬编码 | `.env` + pydantic-settings |
| `locality` 采集了但 API 不返回 | API 正常返回 |
| `end_date` 存为 TEXT | 改为 `DATE` 类型 |
| 前端单文件 App.vue | 组件化拆分 |
| 无 API 认证 | JWT 认证 |
| 无反爬措施 | 限流 + 签名 |
