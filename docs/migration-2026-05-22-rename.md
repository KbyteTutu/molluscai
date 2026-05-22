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

---

## 把 MinIO 数据挂到 NAS（可选）

适用于"docker volume 在系统盘上太挤、想把对象存储放更大或更便宜的网络存储上"的场景。

### 前置条件

- NAS 通过 **NFS v3 / v4** 挂载到主机一个固定路径（阿里云 NAS、群晖、TrueNAS 都行；**SMB/CIFS 不行**——MinIO 不支持）。
- 挂载目录对当前用户**可写**。最简单的姿势是 `chmod 1777 <挂载点>`（参考 `/tmp` 的权限模型）。
- **首次启用前 MinIO 里没有要保留的数据**——切换会让旧 named volume 里的对象与新挂载目录脱钩。如果 MinIO 里已有真实数据，先按下面的"迁移现有数据"小节跑一次性拷贝。

### 启用步骤

```bash
# 1. 准备 NAS 子目录
sudo mkdir -p /data_nas/minio
# (如果目录是 root:root 而 NAS 挂载用 sec=sys，需要让 minio 容器进程能写)
# 阿里云 NAS 默认根目录 1777 (rwxrwxrwt)，建出来的子目录继承父权限即可。

# 2. 把路径写进 .env
echo 'MINIO_DATA_PATH=/data_nas/minio' >> .env

# 3. 重新创建 minio 容器（仅 minio，避免动到其他服务）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate minio

# 4. 验证
docker inspect molluscai-minio --format \
  '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
# 期望看到: bind /data_nas/minio -> /data
```

### 关掉（回退到 docker named volume）

```bash
# 1. 从 .env 删掉 MINIO_DATA_PATH= 那一行
sed -i '/^MINIO_DATA_PATH=/d' .env

# 2. recreate minio
./dev prod-restart minio
```

之后 minio 重新写到 docker named volume `molluscai-minio-data`。**NAS 上的数据不会被 docker 自动删**——如需手动清理 `rm -rf /data_nas/minio/*`。

### 迁移现有数据

如果切换时 MinIO 里**有**要保留的对象：

```bash
# 1. 停 minio（避免迁移过程中数据漂移）
docker stop molluscai-minio

# 2. 拷贝 docker volume → NAS
docker run --rm \
  -v molluscai-minio-data:/from \
  -v /data_nas/minio:/to \
  alpine sh -c 'cp -a /from/. /to/'

# 3. 写入 .env，按上面的 "启用步骤" 第 2-4 步走
```

### 关于性能

- NFS（特别是 NFSv3 nolock）的 fsync 延迟比本地 SSD 高 1-2 个数量级。批量上传图片时吞吐会肉眼可见慢一些，但读取（serving 给前端）走 page cache，影响很小。
- **永远不要** 同时跑两个 MinIO 实例指向同一个 NFS 目录——nolock 模式下会数据损坏。本仓库就是单实例部署，OK。

### `prod-nuke` 的行为

`./dev prod-nuke` **不会**碰 NAS 上的数据。删除的只有 docker 管理的资源（network、named volumes、images）。NAS 数据要清理需要操作员手动 `rm -rf $MINIO_DATA_PATH/*`。脚本会在 nuke 时打印这条提示。

