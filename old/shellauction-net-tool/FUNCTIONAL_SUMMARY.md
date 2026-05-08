# shellauction-net-tool 功能总结

## 项目概述

一个针对 [shellauction.net](https://www.shellauction.net)（意大利贝壳/海贝拍卖网站）的 Python 全栈工具集，包含三大核心功能模块：**数据爬取存储**、**模糊搜索API**、**自动竞价机器人**。

- **作者**: tukechao
- **技术栈**: Python 3.10+, Flask, PostgreSQL, aiohttp, BeautifulSoup4, asyncpg, psycopg_pool, Gunicorn
- **部署**: 通过 Gunicorn 运行在 `0.0.0.0:8080`

---

## 模块详解

### 1. app.py — Flask Web 服务入口

```
路径: app.py
```

- 创建 Flask 应用实例
- 注册 `search_engine` 蓝图，挂载在 `/api` 前缀下
- 根路由 `/` 返回简单文本 `"简简单单一个后端"`
- 开发模式启动: `app.run(debug=False, port=8080, host="0.0.0.0")`

**依赖关系**: 导入并使用 `search_engine.py` 中的蓝图

---

### 2. search_engine.py — 贝壳搜索 API

```
路径: search_engine.py
蓝图路由: /api/search/ [POST]
```

这是前端查询的核心后端接口。

#### 请求参数 (JSON Body)

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `name` | string | 拉丁名，支持模糊搜索 | - |
| `family` | string | 科属名 | - |
| `order` | string | 排序方式 | `nto` |
| `similarity` | string/number | 匹配精度 1-10 | `3` |
| `sold_status` | boolean | 只显示已售 | `false` |

#### 排序方式 (order)

| 值 | 含义 |
|----|------|
| `nto` | New to Old — 按拍卖编号降序（最新→最早） |
| `otn` | Old to New — 按拍卖编号升序（最早→最新） |
| `cpd` | Current Price Down — 截拍价降序 |
| `cpu` | Current Price Up — 截拍价升序 |
| `spd` | Start Price Down — 起拍价降序 |
| `spu` | Start Price Up — 起拍价升序 |

#### 实现细节

- 使用 PostgreSQL 的 `pg_trgm` 扩展实现 trigram 模糊匹配 (`name %% %s`)
- `similarity` 参数除以 10 后通过 `set_limit()` 设置相似度阈值（0.0~1.0）
- 查询上限 100 条
- 返回字段: `image`, `name`, `family`, `size`, `note`, `seller`, `start_price`, `current_price`, `end_date`, `sold`
- 当无结果时，返回包含 `"无结果"` 提示的占位数据
- 图片链接自动将 `_thumb` 后缀替换为原图链接
- `end_date` 若包含 `"..."` 则替换为 `"已删除"`
- `owner` 字段包含 `"no Bids"` 判定为流拍，否则为已售

#### 数据库连接

使用 `psycopg_pool.ConnectionPool` 连接 PostgreSQL:
```
postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres
```
连接池大小: 1~50

---

### 3. get_data.py — 数据爬虫/采集器

```
路径: get_data.py
```

全量爬取 shellauction.net 拍卖数据并存入 PostgreSQL。

#### 工作流程

1. **创建表**: 自动创建 `shellauction` 表（如不存在）
2. **获取当前最大ID**: 查询 `SELECT MAX(item) FROM shellauction` 得到已采集的最大物品编号
3. **构建任务队列**: 从当前最大编号开始，顺序生成 +40000 个待爬取编号
4. **并发爬取**: 10 个异步 worker 协程同时工作
5. **速率控制**: 每秒 100 请求（通过 `asyncio.Semaphore(100)` + 睡眠控制）

#### 数据采集字段 (BidItem 数据类)

| 字段 | 说明 |
|------|------|
| `item` | 拍卖物品编号 |
| `name` | 拉丁种名 |
| `family` | 科属 |
| `size` | 尺寸 |
| `locality` | 产地 |
| `note` | 备注信息 |
| `seller` | 卖家 |
| `start_price` | 起拍价 (EUR) |
| `current_price` | 当前/截拍价 (EUR) |
| `end_date` | 截拍日期 |
| `image` | 图片链接（`;`分隔） |
| `owner` | 出价者/状态 |

#### 爬取细节

- 目标 URL 格式: `https://shellauction.net/auction_shell.php?id={id}&pres=1`
- 遇到 `"ERROR NO LOT<br>"` 跳过（不存在的编号）
- 遇到解析错误写入 `error.log`（含完整 traceback）
- 遇到 `AttributeError` 写入 `skip.log`（记录编号）
- 使用 BeautifulSoup + lxml 解析 HTML
- 价格解析兼容普通格式 `€XX,XX` 和近似价格 `approx. XX€`

#### 数据库表结构

```sql
CREATE TABLE shellauction (
    id SERIAL PRIMARY KEY,
    item INTEGER,
    image TEXT,
    name TEXT,
    family TEXT,
    size TEXT,
    locality TEXT,
    note TEXT,
    seller TEXT,
    start_price FLOAT,
    current_price FLOAT,
    end_date TEXT,
    owner TEXT
);
```

---

### 4. bot.py — 自动竞价机器人

```
路径: bot.py
```

在拍卖结束前毫秒级自动提交出价的异步竞价程序。

#### 核心功能

1. **登录**: 使用预设凭证登录 shellauction.net
2. **获取拍卖信息**: 对每个目标物品,解析页面提取:
   - 隐藏表单字段 (`id`, `bid_check`, `hasWatch`, `pres`, `offer_max_increase`, `offerta`)
   - 截拍结束时间 (`end_time`)
3. **定时出价**: 计算等待时间（截拍时间 - 当前时间 - 偏移量），`asyncio.sleep()` 等待后在最佳时机 POST 出价
4. **并发出价**: 对所有目标物品并发执行定时出价

#### 配置

- `SHELL_LIST`: 目标物品列表，每项为 `(物品ID, 最高出价)` 元组
- `USERNAME` / `PASS`: 登录凭证
- 随机偏移量: 每个物品在 0.8~3.0 秒之间随机偏移，避免行为模式检测

#### 出价判定

- 成功: 页面不包含 `"Minimum offer is"` 和 `"Please login to bid"`
- 失败-低于最低出价: 页面包含 `"Minimum offer is"`
- 失败-登录失效: 页面包含 `"Please login to bid"`

#### 测试功能

`test()` 函数用于单物品测试：7秒后（offset=14秒相对15秒目标）对指定物品出价。

---

### 5. date_fetch.py — 数据库状态查询

```
路径: date_fetch.py
```

简单的工具脚本，查询 `shellauction` 表中当前最大物品编号，用于了解数据采集进度。

---

### 6. gunicorn_cfg.py — 生产部署配置

```
路径: gunicorn_cfg.py
```

- 4 个 worker 进程
- 绑定 `0.0.0.0:8080`
- 同步 worker 模式
- 30 秒超时

---

### 7. success.html — 出价结果参考

```
路径: success.html
```

shellauction.net 出价结果页面的本地副本，用于参考页面结构。包含出价失败的提示模式 (`"Minimum offer is 360,00 EURO. Your Maximum offer is 300,00 EURO"`)，被 `bot.py` 用于识别出价结果。

---

## 项目架构

```
shellauction-net-tool/
├── app.py              # Flask 入口，注册蓝图
├── search_engine.py    # /api/search/ 搜索 API (Blueprint)
├── get_data.py         # 异步爬虫，数据采集入库
├── bot.py              # 异步竞价机器人
├── date_fetch.py       # 数据库查询工具
├── gunicorn_cfg.py     # 生产环境 Gunicorn 配置
├── success.html        # 出价页面参考
├── skip.log            # 爬虫跳过记录
└── error.log           # 爬虫错误日志
```

## 外部依赖

| 包 | 用途 |
|----|------|
| flask | Web 框架 |
| aiohttp | 异步 HTTP 客户端（爬虫+机器人） |
| beautifulsoup4 + lxml | HTML 解析 |
| asyncpg | 异步 PostgreSQL 驱动（爬虫用） |
| psycopg_pool | 连接池（搜索API用） |
| gunicorn | WSGI 生产服务器 |
