将old文件夹内的 v1 版"贝壳拍卖历史数据查询工具"升级为**基于 RAG（检索增强生成）的智能贝壳知识平台**。用户可以通过**自然语言**提问（中/英/拉丁文），系统自动检索历史拍卖数据并结合 LLM 生成回答，同时保留传统结构化搜索能力。

需要有的功能

1.用户系统，支持查询内容记录

2.可扩展的收费系统

3.添加知识库功能，通过pdf的文献上传，图文混合的资料，逐步完善。这部分图文混合资料多为软体动物学文献和论文，参考下面的设计思路。其中，ocr得到的图片markdown里的图要本地缓存。我希望论文和文献、老文献分开上传，且可以分别定义模型。

4.用户权限系统，分超级管理、文献管理、vip、普通用户等。

5.shellaution的已中拍的拍品需要保存图片，避免后续查询不到

6.信息安全保障，禁止别家二次爬取

7.数据库采用postgres

8.整体使用docker部署

# 基于线上模型的软体动物学知识库方案

技术栈确定后，架构可以大幅简化。下面给出完整的工程方案。先提醒一点：我知识截止到2025年5月，**deepseek-v4-flash** 和 **Qwen3-VL-Embedding-8B** 可能是之后发布的版本，具体API参数请以你看到的官方文档为准，我按合理推测给出设计。

## 一、整体架构

```
PDF文献
  ├─ 解析层：PyMuPDF拆页 + 版面分析
  ├─ OCR层：GLM-OCR（文本 + 表格 + 公式）
  ├─ 图像层：抽取图版 → 存对象存储
  ├─ 增强层：DeepSeek做元数据抽取 + 学名校对
  ├─ 向量层：Qwen3-VL-Embedding-8B（文本chunk + 图像双通路）
  └─ 存储层：Milvus（多collection） + MinIO/OSS（图像原件）
       ↓
    检索：混合检索（稠密+BM25+视觉）→ DeepSeek生成答案
```

## 二、PDF解析与OCR

### 2.1 分页与图文分离

```python
import fitz  # PyMuPDF

def parse_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        # 渲染整页为高分辨率图像（供GLM-OCR和视觉embedding用）
        pix = page.get_pixmap(dpi=200)
        page_image = pix.tobytes("png")
        
        # 抽取页面内嵌图像（图版）
        images = []
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            images.append({
                "page": page_num,
                "idx": img_idx,
                "bytes": base_image["image"],
                "ext": base_image["ext"],
                "bbox": page.get_image_bbox(img)
            })
        
        pages.append({
            "page_num": page_num,
            "page_image": page_image,
            "embedded_images": images
        })
    return pages
```

### 2.2 GLM-OCR调用

建议让GLM-OCR输出Markdown格式，保留结构（标题、表格、公式）：

```python
from zhipuai import ZhipuAI

client = ZhipuAI(api_key="YOUR_KEY")

def glm_ocr(image_bytes):
    resp = client.chat.completions.create(
        model="glm-ocr",  # 以官方模型名为准
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", 
                 "image_url": {"url": f"data:image/png;base64,{b64(image_bytes)}"}},
                {"type": "text", 
                 "text": "请将图片内容识别为Markdown，保留标题层级、表格用Markdown语法、"
                         "公式用LaTeX、图注保持原样。拉丁学名原样输出不要改写。"}
            ]
        }]
    )
    return resp.choices[0].message.content
```

**软体动物学特别提醒**：在prompt里明确强调"拉丁学名原样输出"，因为OCR模型有时会"自作聪明"修正它认为的拼写错误，这对学名是灾难。

## 三、元数据抽取（用DeepSeek）

每篇文献OCR完成后，用DeepSeek-V4-Flash一次性抽取结构化元数据，成本低且极大提升后续检索精度：

```python
from openai import OpenAI

ds_client = OpenAI(
    api_key="YOUR_KEY",
    base_url="https://api.deepseek.com"
)

EXTRACTION_PROMPT = """你是软体动物学文献分析助手。从以下文献前3页文本中抽取JSON：
{
  "title": "...",
  "authors": [...],
  "year": 2023,
  "journal": "...",
  "doi": "...",
  "abstract": "...",
  "taxa_mentioned": ["属 种 作者, 年份", ...],
  "higher_taxa": ["科", "目", "纲"],
  "geographic_scope": [...],
  "content_type": "taxonomy|ecology|phylogeny|anatomy|review|other",
  "keywords": [...]
}
仅输出JSON，不要额外说明。学名必须完整保留作者引证。

文献内容：
{content}
"""

def extract_metadata(text):
    resp = ds_client.chat.completions.create(
        model="deepseek-v4-flash",  # 以官方名为准
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(content=text[:8000])}],
        response_format={"type": "json_object"},
        temperature=0
    )
    return json.loads(resp.choices[0].message.content)
```

## 四、学名校对（关键环节）

抽取到的学名用 **MolluscaBase API** 校对，免费无需key：

```python
import requests

def verify_taxon(scientific_name):
    """用MolluscaBase校对学名，返回接受名和分类层级"""
    url = f"https://www.molluscabase.org/rest/AphiaRecordsByName/{scientific_name}"
    params = {"like": "false", "marine_only": "false"}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200 and r.json():
        rec = r.json()[0]
        return {
            "accepted_name": rec.get("valid_name"),
            "rank": rec.get("rank"),
            "kingdom": rec.get("kingdom"),
            "phylum": rec.get("phylum"),
            "class": rec.get("class"),
            "order": rec.get("order"),
            "family": rec.get("family"),
            "genus": rec.get("genus"),
            "aphia_id": rec.get("AphiaID"),
            "status": rec.get("status")  # accepted / unaccepted
        }
    return None
```

把校对结果附在元数据里，这样"Conidae"的查询能召回所有芋螺科物种的文献，即使原文只出现了具体物种名。

## 五、切分与双通路Embedding

### 5.1 文本切分策略

软体动物学文献建议按**语义块**而非固定字数切分：

- 分类描述段落：一个物种描述作为一个chunk（通常300-800字）
- 讨论/方法段：按小标题切
- 表格：整张表作为一个chunk，转Markdown保留结构
- 图注：图注 + 引用该图的正文段落 合并为一个chunk（"图文耦合chunk"）

```python
def chunk_document(markdown_text, metadata):
    chunks = []
    # 按二级/三级标题切分
    sections = split_by_headings(markdown_text, levels=[2, 3])
    for sec in sections:
        if len(sec["content"]) > 1200:
            # 过长再按段落切
            for sub in split_by_paragraph(sec["content"], max_len=800, overlap=100):
                chunks.append({**sec, "content": sub})
        else:
            chunks.append(sec)
    
    # 每个chunk附上文档级元数据
    for c in chunks:
        c["doc_metadata"] = metadata
    return chunks
```

### 5.2 Qwen3-VL-Embedding-8B 双通路

这个模型是多模态的，**同一向量空间里文本和图像可以互检**，这正是软体动物学需要的：

```python
# 假设通过SiliconFlow或官方API调用
def embed_text(text):
    resp = requests.post(
        "https://api.siliconflow.cn/v1/embeddings",  # 以实际服务商为准
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "Qwen/Qwen3-VL-Embedding-8B",
            "input": text,
            "input_type": "text"
        }
    )
    return resp.json()["data"][0]["embedding"]

def embed_image(image_bytes):
    resp = requests.post(
        "https://api.siliconflow.cn/v1/embeddings",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "Qwen/Qwen3-VL-Embedding-8B",
            "input": base64_encode(image_bytes),
            "input_type": "image"
        }
    )
    return resp.json()["data"][0]["embedding"]
```

**两条通路都入库**：

- 文本chunk → text embedding → `text_collection`
- 图版（贝壳照、解剖图、齿轴SEM等） → image embedding → `image_collection`
- 两个collection共享同一向量空间，检索时可以合并排序

## 六、Milvus建库

建议建**三个collection**：

### 6.1 文本collection

```python
from pymilvus import MilvusClient, DataType

client = MilvusClient(uri="http://localhost:19530")

schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("vector", DataType.FLOAT_VECTOR, dim=3584)  # 8B模型维度以官方为准
schema.add_field("content", DataType.VARCHAR, max_length=4000)
schema.add_field("doc_id", DataType.VARCHAR, max_length=64)
schema.add_field("page_num", DataType.INT32)
schema.add_field("section", DataType.VARCHAR, max_length=200)
# 元数据字段（用于标量过滤）
schema.add_field("year", DataType.INT32)
schema.add_field("journal", DataType.VARCHAR, max_length=200)
schema.add_field("taxa", DataType.ARRAY, element_type=DataType.VARCHAR, 
                 max_capacity=50, max_length=100)
schema.add_field("family", DataType.VARCHAR, max_length=100)
schema.add_field("content_type", DataType.VARCHAR, max_length=50)
# BM25稀疏向量字段（Milvus 2.4+支持）
schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)

index_params = client.prepare_index_params()
index_params.add_index("vector", index_type="HNSW", metric_type="COSINE",
                       params={"M": 16, "efConstruction": 200})
index_params.add_index("sparse", index_type="SPARSE_INVERTED_INDEX", 
                       metric_type="IP")

client.create_collection("mollusca_text", schema=schema, index_params=index_params)
```

### 6.2 图像collection

```python
schema_img = client.create_schema(auto_id=True, enable_dynamic_field=True)
schema_img.add_field("id", DataType.INT64, is_primary=True)
schema_img.add_field("vector", DataType.FLOAT_VECTOR, dim=3584)
schema_img.add_field("image_path", DataType.VARCHAR, max_length=500)  # 对象存储路径
schema_img.add_field("caption", DataType.VARCHAR, max_length=2000)
schema_img.add_field("doc_id", DataType.VARCHAR, max_length=64)
schema_img.add_field("page_num", DataType.INT32)
schema_img.add_field("figure_type", DataType.VARCHAR, max_length=50)  
# shell_photo / radula_SEM / anatomy / map / phylogeny
schema_img.add_field("taxa", DataType.ARRAY, element_type=DataType.VARCHAR,
                     max_capacity=20, max_length=100)

client.create_collection("mollusca_image", schema=schema_img, 
                         index_params=index_params)
```

### 6.3 文档级collection（存摘要和元数据，供粗筛）

存整篇文献的摘要embedding和完整元数据，第一轮检索可以先定位到相关文献，再在文献内深入。

## 七、检索Pipeline

### 7.1 查询理解

先用DeepSeek把用户query做一次解析：

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

这一步能把"菲律宾芋螺科2010年以后的齿舌研究"这种复合查询拆解成过滤条件+检索词。

### 7.2 混合检索

```python
def hybrid_search(query, parsed):
    # 1. 生成query embedding（用Qwen3-VL-Embedding）
    q_vec = embed_text(parsed["rewritten_query"])
    
    # 2. 构造标量过滤
    filters = []
    if parsed.get("taxa"):
        filters.append(f"ARRAY_CONTAINS_ANY(taxa, {parsed['taxa']})")
    if parsed.get("year_range"):
        filters.append(f"year >= {parsed['year_range'][0]} and year <= {parsed['year_range'][1]}")
    filter_expr = " and ".join(filters) if filters else ""
    
    # 3. 文本稠密检索
    text_hits = client.search(
        collection_name="mollusca_text",
        data=[q_vec],
        anns_field="vector",
        filter=filter_expr,
        limit=30,
        output_fields=["content", "doc_id", "page_num", "taxa"]
    )
    
    # 4. BM25稀疏检索（学名、标本号召回关键）
    sparse_hits = client.search(
        collection_name="mollusca_text",
        data=[query],  # 原始文本
        anns_field="sparse",
        filter=filter_expr,
        limit=30
    )
    
    # 5. 图像检索（如果intent包含image）
    image_hits = []
    if parsed["intent"] in ("image_search", "both"):
        image_hits = client.search(
            collection_name="mollusca_image",
            data=[q_vec],  # 同一向量空间，文本query可直接搜图
            anns_field="vector",
            limit=10
        )
    
    # 6. RRF融合
    merged = rrf_fusion([text_hits, sparse_hits], k=60)
    return merged[:15], image_hits
```

Milvus 2.4+ 原生支持 `hybrid_search`，可以一次调用完成稠密+稀疏融合，比上面手写RRF更高效。

### 7.3 重排与生成

由于通道是线上模型，可以省略专门的reranker，直接让DeepSeek在生成时做软性重排：

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

def generate_answer(query, text_hits, image_hits):
    text_ctx = "\n\n".join([f"[{h['doc_id']}-p{h['page_num']}] {h['content']}" 
                            for h in text_hits])
    img_ctx = "\n".join([f"[IMG-{h['id']}] {h['caption']} (类型:{h['figure_type']})"
                          for h in image_hits])
    
    resp = ds_client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{
            "role": "user",
            "content": GENERATION_PROMPT.format(
                query=query, text_chunks=text_ctx, image_refs=img_ctx)
        }],
        temperature=0.1
    )
    return resp.choices[0].message.content, image_hits
```

## 八、成本与性能估算

假设1000篇文献，平均20页：

| 环节                    | 调用量       | 大致成本量级                |
| ----------------------- | ------------ | --------------------------- |
| GLM-OCR                 | 20000页      | 中等（OCR模型通常按页计费） |
| DeepSeek元数据抽取      | 1000次       | 很低                        |
| Qwen3-VL-Embedding 文本 | 约10万chunks | 中等                        |
| Qwen3-VL-Embedding 图像 | 约5000张图   | 中等                        |
| Milvus存储              | 约10万向量   | 自托管几乎免费              |

**优化建议**：

- 批量embedding（通常batch=32能显著降本）
- OCR结果本地持久化，避免重复调用
- 对低价值页面（版权页、空白页）跳过OCR

## 九、关键工程注意事项

1. **幂等与断点续传**：以 `doc_id + page_num` 为key，每个环节的中间结果都落盘（OCR结果、chunk、embedding），任何环节中断可续跑
2. **API限流**：线上模型都有QPS限制，加`asyncio`+`semaphore`做并发控制，失败重试用指数退避
3. **学名优先入BM25**：embedding对拉丁学名不敏感（因为模型训练时见得少），**BM25是学名精确召回的主力**，一定要开
4. **图像caption双写**：VLM生成的描述 + 原始图注都存到 `caption` 字段，搜索时能多一重文本召回
5. **版本化**：embedding模型升级会导致向量不兼容，collection要带版本号（如 `mollusca_text_v1`）便于回滚

## 十、建议的实施顺序

1. **周1**：搭 GLM-OCR + DeepSeek 解析 pipeline，跑通10篇文献，人工校验OCR质量（尤其学名错误率）
2. **周2**：接入 MolluscaBase 校对，建Milvus collection，完成文本通路入库与检索
3. **周3**：加入图像通路，验证"文字搜图"和"以图搜图"效果
4. **周4**：优化查询理解 + 生成prompt，做端到端评测


