# vue-shellauction-net-tool 功能总结

## 项目概述

一个基于 **Vue 3 + Vite** 构建的单页面应用 (SPA)，为 shellauction.net 历史拍卖数据提供交互式查询界面。

- **版本**: v1.2
- **技术栈**: Vue 3.4, Vite 5.1, Axios 1.6
- **部署**: 构建静态文件，部署到 Nginx `/var/www/s/`
- **后端 API**: `https://s.tutu.gold/api/search/`

---

## 页面结构

### 标题区
- 标题: **"Shellauction.net 历史数据查询工具 by 涂涂 v1.2"**
- 说明文字（5 条公告，包含使用协议声明、数据上限、功能规划等）

### 搜索表单

#### 第一行输入
| 控件 | 类型 | 说明 |
|------|------|------|
| 名称 (Name) | 文本输入框 | 输入拉丁名，支持模糊搜索，格式建议：属名+空格+种名 |
| 科属 (Family) | 下拉选择框 | 60+ 预定义科属选项，含不限 |

#### 第二行输入
| 控件 | 类型 | 说明 |
|------|------|------|
| 排序顺序 (Order) | 下拉选择框 | 4 个选项：由最新到最早 / 由最早到最新 / 截拍价格降序 / 起拍价格降序 |
| 匹配精度 (Similarity) | 数字输入框 | 范围 1-10，默认 3（越高越精确）|

#### 附加控件
- **售出过滤复选框**: "只显示已售出的贝壳"
- **SEARCH 按钮**: 触发查询

### 结果表格

| 列名 | 宽度 | 说明 |
|------|------|------|
| 图片 | 135px | 缩略图列表，点击弹出大图模态框 |
| 名称 | 180px | 拉丁学名 |
| 状态 | 50px | 已售 / 流拍 |
| 科 | 120px | 科属分类 |
| 起拍价 | 66px | 起拍价格 (EUR) |
| 截拍价 | 66px | 最终截拍价格 (EUR) |
| 截拍时间 | 100px | 拍卖结束时间 |
| 尺寸 | 110px | 贝壳尺寸 |
| 卖家 | 100px | 卖家名称 |
| 信息 | 250px | 备注信息 |

### 底部

- 版权信息 © 2024 + ICP 备案号

---

## 组件树

```
App.vue (根组件 — 包含全部业务逻辑)
├── HelloWorld.vue      (未使用 — Vue 脚手架模板)
├── TheWelcome.vue       (未使用 — Vue 脚手架模板)
│   └── WelcomeItem.vue
│       └── icons/IconDocumentation.vue
│       └── icons/IconTooling.vue
│       └── icons/IconEcosystem.vue
│       └── icons/IconCommunity.vue
│       └── icons/IconSupport.vue
```

> **注意**: `HelloWorld.vue`、`TheWelcome.vue` 及 icon 组件是 Vue 官方脚手架生成的模板代码，实际应用中**未被使用**。所有业务逻辑集中在 `App.vue` 中。

---

## 核心交互流程

### 1. 搜索流程

```
用户填写表单 → 点击 SEARCH → 
  axios.post('https://s.tutu.gold/api/search/', {
    name, family, order, similarity, sold_status
  }) →
  接收 JSON 数组 → 
  渲染结果表格
```

### 2. 图片查看

- 缩略图显示在表格中
- 点击缩略图触发 `openModal()` 
- 全屏半透明遮罩层展示大图
- 点击遮罩层任意位置关闭

### 3. 响应式设计

- 桌面端: 两列输入布局，最大宽度 1800px
- 移动端 (≤1024px): 单列布局，字号缩小至 11px，缩略图缩小至 50px
- 表格支持横向滚动

---

## 预定义科属列表 (Family)

共 60+ 个选项，覆盖主要软体动物分类：

**腹足纲**: Angaridae, Architectonicidae, Buccinidae, Bursidae, Cancellariidae, Cassidae, Cerithiidae, Columbellidae, Conidae, Coralliophilidae, Costellariidae, Cypraeidae (宝贝科), Epitoniidae, Fasciolariidae, Fissurellidae, Haliotidae (鲍科), Harpidae, Littorinidae, Marginellidae, Melongenidae, Mitridae, Muricidae (骨螺科), Nassariidae, Naticidae, Neritidae, Olividae, Ovulidae, Patellidae, Pleurotomariidae, Ranellidae, Strombidae, Terebridae, Tonnidae, Triviidae, Trochidae, Turbinellidae, Turbinidae, Turridae, Turritellidae, Volutidae, Xenophoridae

**双壳纲**: Arcidae, Cardiidae, Mactridae, Mytilidae, Pectinidae, Spondylidae, Tellinidae, Veneridae + BIVALVIA

**其他**: AMMONOIDEA (菊石), BRACHIOPODA (腕足), CEPHALOPODA (头足), CRUSTACEA (甲壳), ECHINOIDEA (海胆), FRESHWATER (淡水), LANDSNAILS (陆贝), MEDITERRANEAN (地中海), MICROSHELLS (微型贝壳), OTHER, PLANTAE (植物), POLIPLACOPHORA (多板), PRINTINGS (印刷品), STAMPS (邮票), TRILOBITA (三叶虫), USED BOOKS (二手书), VERTEBRATA (脊椎动物)

---

## API 接口协议

### 请求

```
POST https://s.tutu.gold/api/search/
Content-Type: application/json

{
  "name": "Conus",
  "family": "Conidae",
  "order": "nto",
  "similarity": 3,
  "sold_status": false
}
```

### 响应

```json
[
  {
    "idx": 0,
    "image": ["/path/to/image.jpg"],
    "name": "Conus textile",
    "family": "Conidae",
    "size": "45 mm",
    "note": "F++",
    "seller": "SellerName",
    "end_date": "31-03-2024",
    "start_price": 5.0,
    "current_price": 12.0,
    "sold": true
  }
]
```

---

## 构建与部署

### 开发
```bash
npm run dev        # Vite 开发服务器
```

### 生产构建
```bash
npm run build      # 输出到 dist/
```

### 部署 (copy.sh)
```bash
npm run build
sudo rm -rf /var/www/s/
sudo cp -r dist/ /var/www/s
```
即将构建产物部署到 Nginx 静态目录 `/var/www/s/`。

---

## 外部依赖

| 包 | 版本 | 用途 |
|----|------|------|
| vue | ^3.4.21 | 前端框架 |
| axios | ^1.6.8 | HTTP 请求 |
| vite | ^5.1.6 | 构建工具 (dev) |
| @vitejs/plugin-vue | ^5.0.4 | Vue SFC 编译 (dev) |

## 其他

- **统计分析**: 内嵌百度统计 (`hm.baidu.com`) 跟踪代码
- **网站图标**: `snail.webp` (蜗牛图标)
- **ICP 备案**: 京ICP备2022009849号
- **域名**: s.tutu.gold
