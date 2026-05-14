<template>
    <div id="app">
        <div class="search-container">
            <h2 class="search-title">Shellauction.net 历史数据查询工具 by 涂涂 v1.2</h2>
            <p class="info">
                1.看了意拍使用协议的，本网站符合使用协议。<br />2.单次数据查询上限为100条。<br /> 3.准备加入worms考据功能。<br />
                4.数据自动更新启用，每月10日前更新完上月数据。<br />5.图片有的显示不出来，是意拍老板删了。
            </p>
            <div class="search-inputs">
                <div class="input-row"> <!-- 第一行 -->
                    <div class="input-group">
                        <label for="name">名称（Name）:</label>
                        <input id="name" class="search-input" v-model="name" placeholder="请输入拉丁名，支持模糊搜索，尽量填写属名+空格+种名">
                    </div>
                    <div class="input-group">
                        <label for="family">科属（Family）:</label>
                        <select id="family" class="search-input" v-model="family">
                            <option value="">不限</option>
                            <option v-for="item in families" :key="item" :value="item">
                                {{ item }}
                            </option>
                        </select>
                    </div>
                </div>
                <div class="input-row"> <!-- 第二行 -->
                    <div class="input-group">
                        <label for="order">排序顺序（Order）:</label>
                        <select id="order" class="search-input" v-model="order">
                            <option value="nto">由最新到最早（From new to old）</option>
                            <option value="otn">由最早到最新（From old to new）</option>
                            <option value="cpd">截拍价格降序（End price down）</option>
                            <option value="spd">起拍价格降序（Start price down）</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label for="similarity">匹配精度（越高越精确匹配，0-10，建议选择1-3）:</label>
                        <input id="similarity" class="search-input" type="number" v-model.number="similarity" min="1"
                            max="10" placeholder="1-10">
                    </div>
                </div>
                <!-- 搜索按钮独立于输入行 -->
                <div class="sold-check-box-container">
                    <input type="checkbox" id="soldCheckBox" v-model="isChecked">
                    <label for="soldCheckBox">只显示已售出的贝壳</label>
                </div>
                <div class="search-button-container">
                    <button class="search-button" @click="fetchData">SEARCH</button>

                </div>
            </div>


            <table class="result-table">
                <thead>
                    <tr>
                        <th class="column-img">图片</th>
                        <th class="column-name">名称</th>
                        <th class="column-sold">状态</th>
                        <th class="column-family">科</th>
                        <th class="column-start-price">起拍价</th>
                        <th class="column-current-price">截拍价</th>
                        <th class="column-end-date">截拍时间</th>
                        <th class="column-size">尺寸</th>
                        <th class="column-seller">卖家</th>
                        <th class="column-note">信息</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in items" :key="item.idx">
                        <td>
                            <img v-if="item.image && item.image.length > 0" v-for="(image, index) in item.image"
                                :key="index" :src="'https://shellauction.net/' + image"
                                @click="openModal('https://shellauction.net/' + image)" class="item-thumbnail"
                                :alt="item.name">
                            <!-- 如果 item.image 为空，则不显示任何内容或显示占位符 -->
                            <div v-else class="image-placeholder">
                                <p class="image-cell">
                                    No Image
                                </p>
                            </div>
                        </td>
                        <td>{{ item.name }}</td>
                        <td>
                            <span v-if="item.sold">已售</span>
                            <span v-else>流拍</span>
                        </td>
                        <td>{{ item.family }}</td>
                        <td>{{ item.start_price }}</td>
                        <td>{{ item.current_price }}</td>
                        <td>{{ item.end_date }}</td>
                        <td>{{ item.size }}</td>
                        <td>{{ item.seller }}</td>
                        <td>{{ item.note }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <footer class="app-footer">
            © 2024 技术测试站点 京ICP备2022009849号 s.tutu.gold
        </footer>
    </div>

    <div v-if="showModal" class="modal" @click="showModal = false">
        <img :src="selectedImage" class="modal-content">
    </div>

</template>

<script>
import axios from 'axios'

export default {
    data() {
        return {
            name: '',
            family: '',
            order: 'nto',
            similarity: 3,
            items: [],
            showModal: false,
            selectedImage: '',
            isChecked: false,
            families: ["Angaridae", "Architectonicidae", "Buccinidae", "Bursidae", "Cancellariidae", "Cassidae", "Cerithiidae", "Columbellidae", "Conidae", "Coralliophilidae", "Costellariidae", "Cypraeidae", "Epitoniidae", "Fasciolariidae", "Fissurellidae", "Haliotidae", "Harpidae", "Littorinidae", "Marginellidae", "Melongenidae", "Mitridae", "Muricidae", "NIGER/ROSTRATED", "Nassariidae", "Naticidae", "Neritidae", "Olividae", "Ovulidae", "Patellidae", "Pleurotomariidae", "Ranellidae", "Strombidae", "Terebridae", "Tonnidae", "Triviidae", "Trochidae", "Turbinellidae", "Turbinidae", "Turridae", "Turritellidae", "Volutidae", "Xenophoridae", "BIVALVIA", "Arcidae", "Cardiidae", "Mactridae", "Mytilidae", "Pectinidae", "Spondylidae", "Tellinidae", "Veneridae", "AMMONOIDEA", "BRACHIOPODA", "CEPHALOPODA", "CRUSTACEA", "ECHINOIDEA", "FRESHWATER", "LANDSNAILS", "MEDITERRANEAN", "MICROSHELLS", "OTHER", "PLANTAE", "POLIPLACOPHORA", "PRINTINGS", "STAMPS", "TRILOBITA", "USED BOOKS", "VERTEBRATA"]

        }
    },
    methods: {
        openModal(imageUrl) {
            this.selectedImage = imageUrl;
            this.showModal = true;
        },
        async fetchData() {
            this.items = [];
            const data = {
                name: this.name,
                family: this.family,
                order: this.order,
                similarity: this.similarity,
                sold_status: this.isChecked
            };
            try {
                const response = await axios.post('https://s.tutu.gold/api/search/', data);
                this.items = response.data;
            } catch (error) {
                console.error("There was an error fetching the data:", error);
                // 在这里处理错误，例如设置错误消息，或者根据错误类型进行特定操作
            }
        }
    }
}
</script>

<style scoped>
#app {
    display: flex;
    flex-direction: column;
    /* 垂直布局 */
    min-height: 100vh;
    font-family: "Segoe UI", "Roboto", sans-serif;
}

.main-content {
    flex-grow: 1;
    /* 填充剩余空间 */
}

.info {
    color: gray;
    text-align: center;
    font-size: 12px;
    margin-bottom: 10px;
}

.app-footer {
    text-align: center;
    padding: 20px;
    font-size: 14px;
    color: #666;
    background-color: #f2f2f2;
    border-top: 1px solid #e1e1e1;
}

.search-container {
    width: 100%;
    max-width: 1800px;
    padding: 20px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    border-radius: 10px;
    background-color: #fff;
}


.search-title {
    margin: 0 0 20px;
    font-weight: bold;
    font-family: "Heiti", "黑体", sans-serif;
    text-align: center;
    font-size: 24px;
}

.search-inputs {
    display: flex;
    flex-direction: column;
    /* 维持垂直布局 */
    align-items: center;
    /* 子元素水平居中 */
    gap: 20px;
    /* 元素间距 */
}

.input-row {
    display: flex;
    justify-content: space-around;
    /* 行内输入组均匀分布 */
    width: 90%;
    /* 调整宽度以适应屏幕大小 */
}

.input-group {
    display: flex;
    flex-direction: column;
    align-items: left;
    /* 输入组内元素垂直、水平居中 */
    width: 100%;
    /* 占满其父容器宽度 */
    max-width: 400px;
    /* 限制最大宽度 */
}

.input-group label {
    align-self: flex-start;
    /* 让label在flex容器内自身左对齐 */
    width: 100%;
    /* 使label宽度填满input-group，以便文本左对齐生效 */
    text-align: left;
    /* 文本左对齐 */
}

.search-input,
select.search-input {
    width: 100%;
    /* 填满父容器宽度 */
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 8px;
    background-color: #f7f7f7;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
    font-size: 14px;
}

.search-input:focus,
select.search-input:focus {
    border-color: #80bdff;
    background-color: #fff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.search-button-container {
    display: flex;
    justify-content: center;
    /* 按钮居中 */
    width: 100%;
    /* 占满父容器宽度 */
}

.search-button {
    padding: 12px 20px;
    background-color: #007bff;
    color: #fff;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s;
    font-weight: bold;
}

.search-button:hover {
    background-color: #0056b3;
}


/* Table Styles */

.image-cell {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    /* 确保垂直居中 */
    justify-content: flex-start;
    /* 水平方向靠左开始排列，根据需要可以调整 */
    gap: 8px;
    /* 图片之间的间距 */
    height: 100%;
    /* 确保单元格充分利用可用高度 */
}

.item-thumbnail {
    max-width: 100px;
    /* 控制缩略图大小 */
    cursor: pointer;
    /* 移除margin-right和margin-bottom，使用gap代替 */
}

.result-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    margin-top: 20px;
    /* 为表格顶部增加一些空间 */
}

.result-table th,
.result-table td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
    white-space: normal;
    /* 允许内容自动换行 */
    /* 移除了 overflow 和 text-overflow 属性 */
}



/* 分别设置每列的固定宽度 */
.column-img {
    width: 135px;
}

.column-name {
    width: 180px;
}

.column-sold {
    width: 50px;
}

.column-family {
    width: 120px;
}

.column-start-price {
    width: 66px;
}

.column-current-price {
    width: 66px;
}

.column-size {
    width: 110px;
}

.column-seller {
    width: 100px;
}

.column-end-date {
    width: 100px;
}

.column-note {
    width: 250px;
}


/* 添加美观性改进 */
.result-table th {
    background-color: #f9f9f9;
    /* 表头背景色 */
    font-weight: bold;
    /* 表头字体加粗 */
}

.result-table tr:nth-child(even) {
    background-color: #f2f2f2;
    /* 为偶数行添加斑马线背景 */
}

/* 搜索按钮居中 */
.search-inputs {
    text-align: center;
}

.search-button {
    margin-top: 10px;
}

.modal {
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    overflow: auto;
    background-color: rgba(0, 0, 0, 0.6);
}

.modal-content {
    margin: auto;
    display: block;
    width: 80%;
    max-width: 700px;
}

.item-image {
    max-width: 100px;
    cursor: pointer;
}

@media (max-width: 1024px) {
    .input-row {
        flex-direction: column;
        align-items: stretch;
    }


    .search-container,
    .app-footer {
        width: calc(100% + 60px);
        margin-top: -30px;
        margin-left: -30px;
        margin-right: -30px;
    }

    .result-table {
        width: auto;
        margin-bottom: 20px;
    }

    .result-table td {
        font-size: 11px;
    }

    .search-title {
        font-size: 20px;
    }

    .search-input,
    .search-button {
        padding: 8px 10px;
    }

    .column-img,
    .column-name,
    .column-family,
    .column-size,
    .column-seller,
    .column-sold,
    .column-end-date,
    .column-start-price,
    .column-current-price,
    .column-note {
        font-size: 11px;
    }

    .item-thumbnail {
        max-width: 50px;
        /* 在小屏幕上减小图片尺寸 */
    }
}
</style>
