# Migration: 重命名到 `molluscai-` 前缀 + external 网络/卷（2026-05-22）

## 这次改了什么

为了根治"docker daemon 重启后容器掉出 `molluscai_default` 网络、celery-beat 永远解析不到 `redis`"这个故障，把所有 docker 资源命名空间统一并改成 external：

| 维度 | 旧 | 新 |
|---|---|---|
| 容器 | `mollusc-postgres`, `mollusc-redis`, `mollusc-minio`, `mollusc-backend`, `mollusc-celery-worker`, `mollusc-celery-beat`, `mollusc-frontend` | `molluscai-postgres`, `molluscai-redis`, `molluscai-minio`, `molluscai-backend`, `molluscai-celery-worker`, `molluscai-celery-beat`, `molluscai-frontend` |
| compose 镜像 | `molluscai-backend` 等（隐式） | `molluscai-backend:latest` 等（在 compose 里显式 `image:`） |
| base 镜像 | `molluscai:v0.1` | `molluscai-base:v0.2` |
| compose project | 隐式 `molluscai`（来自目录名） | 显式 `name: molluscai` |
| docker network | `molluscai_default`（compose-managed） | `molluscai-net`（**external**） |
| named volumes | `molluscai_postgres_data` 等 | `molluscai-postgres-data`, `molluscai-redis-data`, `molluscai-minio-data`（**external**） |

新行为：

- `./dev prod-up` 会**自动**创建网络和 named volumes（如果不存在），并校验 `.env` 已存在且不含 `replace-me-...` 占位符。
- `./dev prod-down` **不会**删除网络和卷（这是 external 的全部意义）。
- `./dev prod-nuke` 是新加的破坏性命令，需输入 `prod-nuke` 二次确认。
- `data_import/README.md` 不再推荐 `docker compose exec backend python -m scripts.import_worms_sqlite ...`（在新架构下这条命令依然会因为 `data_import/` 没挂载而失败）。统一走 `./dev worms-import` / `./dev prod-import`。

## 旧生产环境迁移步骤

> 前置：你已经接受**全部生产数据丢失**——postgres、redis、minio 全部清空，必须重新跑 `./dev prod-import`。如果你需要保数据，先按下面"可选：迁移前备份"再继续。

### 0. 可选：迁移前备份

```bash
cd /path/to/molluscai
./dev backup                                                      # postgres dump 到 backups/<ts>.sql.gz
docker run --rm \
  -v molluscai_minio_data:/from -v "$PWD/backups:/to" alpine \
  tar czf "/to/minio-$(date +%s).tar.gz" -C /from .              # minio 全量
```

### 1. 拉新代码

```bash
cd /path/to/molluscai
git fetch origin
git checkout <new-branch-or-main>
git pull
```

### 2. 停旧栈，清旧资源

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v --remove-orphans

docker network rm molluscai_default 2>/dev/null || true

docker image rm -f molluscai:v0.1 2>/dev/null || true
docker image rm -f molluscai-backend molluscai-celery-worker \
                   molluscai-celery-beat molluscai-frontend 2>/dev/null || true

docker volume ls --format '{{.Name}}' | grep -E '^molluscai_(postgres|redis|minio)_data$' \
  | xargs -r docker volume rm

docker ps -a --filter 'name=mollusc-' --format '{{.Names}}' | xargs -r docker rm -f
```

### 3. 校验 `.env`

`.env` 必须存在，且 `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` / `ENCRYPTION_KEY` **不能**保持 `replace-me-...` 默认值。如果是干净机器或第一次部署：

```bash
cp .env.example .env
./dev prod-secrets > .env.secrets
# 把 .env.secrets 里的 JWT_*/ENCRYPTION_KEY/POSTGRES_PASSWORD/MINIO_ROOT_PASSWORD
# 拷到 .env，然后填上各家 LLM 的 API key
rm .env.secrets
```

### 4. 一键起新栈

```bash
./dev prod-up
```

`prod-up` 会：
1. 校验 `.env` 不含 `replace-me-...` 占位符（不通过则 die）
2. 创建 `molluscai-net` 网络（如果不存在）
3. 创建 `molluscai-postgres-data` / `molluscai-redis-data` / `molluscai-minio-data` 三个 volume
4. 构建 `molluscai-base:v0.2`（如果缺失或 `requirements.txt` 比镜像新）
5. `docker compose ... up -d --build` 起全部服务
6. 打印 `prod-status` + 提示下一步导入

### 5. 导入数据

```bash
./dev prod-import data_import/worms_mollusca.sqlite.gz data_import/postgres_backup.sql
```

或分开跑：

```bash
./dev worms-import data_import/worms_mollusca.sqlite.gz
./dev seed
```

### 6. 验收

```bash
./dev prod-status
docker network inspect molluscai-net --format \
  '{{range $k,$v := .Containers}}{{$v.Name}} {{end}}' | tr ' ' '\n' | sort
```

应当看到全部七个容器 (`molluscai-postgres molluscai-redis molluscai-minio molluscai-backend molluscai-celery-worker molluscai-celery-beat molluscai-frontend`) 都在 `molluscai-net` 内。

```bash
docker logs molluscai-celery-beat --tail 20
```

应当看到 `Scheduler: Sending due task ...`，**没有** `Error -3 connecting to redis:6379`。

## 新机器干净安装步骤

```bash
git clone <repo> /opt/molluscai
cd /opt/molluscai
cp .env.example .env
./dev prod-secrets > .env.secrets   # 把 secrets 拷进 .env，然后删掉 .env.secrets
# 填上 DEEPSEEK_API_KEY / SILICONFLOW_API_KEY / ZHIPU_API_KEY 等
./dev prod-up

# 把 worms_mollusca.sqlite[.gz] 和 postgres_backup.sql[.gz] scp 到 data_import/
./dev prod-import data_import/worms_mollusca.sqlite.gz data_import/postgres_backup.sql
```

## 故障排查：beat 报 `Error -3 connecting to redis`

如果迁移完成后 beat 日志依然出现：

```
Error -3 connecting to redis:6379. Temporary failure in name resolution.
```

按顺序检查：

```bash
# 1. beat 是否在 molluscai-net？
docker inspect molluscai-celery-beat --format \
  '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# 期望输出: molluscai-net

# 2. redis 是否在 molluscai-net？
docker inspect molluscai-redis --format \
  '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# 期望输出: molluscai-net

# 3. 网络成员名单
docker network inspect molluscai-net --format \
  '{{range $k,$v := .Containers}}{{$v.Name}}{{"\n"}}{{end}}'
# 期望: 7 个 molluscai-* 容器全在
```

如果 redis 不在 `molluscai-net`，恢复办法是直接重建栈：

```bash
./dev prod-down
./dev prod-up
```

`external: true` 让网络/卷在 `prod-down` 期间存活，`prod-up` 重建容器时会全部重新加入同一网络。
