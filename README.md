# MolluscAI

软体动物学知识平台：物种分类检索、拍卖记录查询、iNaturalist 集成、WoRMS 外部匹配。

## 功能

- **物种检索** — 30 万+ 软体动物（Mollusca）分类数据，支持拉丁学名/俗名/曾用名检索，trigram 模糊匹配 + 语义向量检索
- **WoRMS 外部匹配** — 热加载 WoRMS API，实现在非软体动物门类的精确查找（Foraminifera、Cnidaria 等）
- **iNaturalist 集成** — 物种详情页自动查询 iNaturalist API，同步多语言俗名到本地数据库，支持所有分类阶元
- **拍卖记录** — shellauction.net 历史拍卖数据查询与对比
- **纠错系统** — 用户可提交俗名、学名等字段的修正建议，管理员审核后更新
- **管理后台** — 数据采集、模型配置、向量管理、用户/配额/查询日志管理

## 快速开始

```bash
cp .env.example .env
./dev up          # 一键启动全栈
./dev seed        # 导入历史拍卖数据（需要 legacy/postgres_backup.sql）
./dev status      # 全栈健康检查
```

## 目录结构

```
molluscai/
├── backend/                    # FastAPI + Celery
│   ├── app/
│   │   ├── api/                # REST 路由
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic
│   │   ├── services/           # 业务逻辑（搜索、iNaturalist、LLM）
│   │   ├── tasks/              # Celery 任务
│   │   └── core/               # 安全、限流、缓存
│   └── scripts/                # 数据导入脚本
├── frontend/                   # Vue 3 + Vite
│   └── src/
│       ├── views/              # 页面组件
│       ├── components/         # UI 组件
│       ├── stores/             # Pinia 状态管理
│       └── api/                # API 客户端
├── infra/                      # Docker 镜像 + PostgreSQL DDL
├── scripts/                    # dev.sh 工具箱 + WoRMS dump
├── docs/                       # 设计文档 + 工作记录
└── legacy/                     # v1 历史代码（不参与构建）
```

## 开发

```bash
./dev up                # 启动全栈
./dev rebuild           # 强制重建
./dev restart [svc]     # 重启服务
./dev logs [svc]        # 查看日志
./dev psql [args]       # 进数据库
./dev test              # 冒烟测试
./dev help              # 完整帮助
```

## 部署

```bash
./dev prod-up           # 生产环境启动
./dev prod-import <worms.sqlite> <backup.sql>  # 导入数据
./dev prod-secrets      # 生成安全密钥
```

## 访问地址

| 入口 | 地址 |
|---|---|
| 前端 | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| MinIO | http://localhost:9003 |

## 技术栈

- **后端**: FastAPI + PostgreSQL 16 (pgvector + pg_trgm) + Redis + Celery + MinIO
- **前端**: Vue 3 + Vite + Pinia + Tailwind CSS
- **AI**: DeepSeek / SiliconFlow / 智谱 (多模型支持，可切换)
- **数据源**: WoRMS / MolluscaBase / iNaturalist / shellauction.net

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
