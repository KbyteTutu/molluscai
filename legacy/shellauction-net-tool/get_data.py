#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2024-03-29 12:42:10
# @ LastEditors: tukechao
# @ LastEditTime: 2024-06-10 20:55:11
# @ FilePath: /shell-auction-bot/get_data.py
# @ description:意拍爬虫

import asyncio
import aiohttp
import time
import traceback
import asyncpg
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dataclasses import dataclass

# from psycopg_pool import ConnectionPool

# # 数据库连接配置
# pool = ConnectionPool(
#     conninfo="postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres",
#     min_size=1,
#     max_size=50,
#     open=True,  # 立即开始连接过程
# )


@dataclass
class BidItem:

    item: int = 0
    name: str = ""
    family: str = ""
    size: str = ""
    locality: str = ""
    note: str = ""
    seller: str = ""
    start_price: float = 0.0
    current_price: float = 0.0
    end_date = ""
    image: str = ""
    owner: str = ""


async def get_current_cnt() -> int:
    conn = await asyncpg.connect("postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres")
    try:
        result = await conn.fetchval("SELECT MAX(item) FROM shellauction;")
        return result
    finally:
        await conn.close()


async def get_info(id, session):
    try:
        item_obj = BidItem()
        url = f"https://shellauction.net/auction_shell.php?id={id}&pres=1"
        async with session.get(url) as response:
            html = await response.text()
            if "ERROR NO LOT<br>" in html:
                item_obj.item = id
                # await insert_bid_item(item_obj)
                return
            soup = BeautifulSoup(html, "lxml")

            img_start = soup.find(string="Item Images\n")
            img_end = soup.find(string="Item")

            # 获取开始点和结束点之间的所有内容
            current = img_start.find_parent("tr")  # 假设“Item Images”位于一个<tr>标签内
            images = []
            while current and current != img_end.find_parent("tr"):
                # 检查是否有<img>标签且没有title属性
                for img in current.find_all("img", title=False):
                    images.append(img["src"])  # 收集图片链接
                current = current.find_next_sibling("tr")
            item_obj.image = ";".join(images)
            item_obj.end_date = soup.find("td", string="End").find_next_sibling("td").text.split(">")[0].strip()

            item_obj.item = int(soup.find("td", class_="B11", string="Item").find_next_sibling("td").text[1:].strip())
            item_obj.family = soup.find("td", string="Family").find_next_sibling("td").text.strip()
            item_obj.name = soup.find("td", string="Name").find_next_sibling("td").text.strip()
            item_obj.size = soup.find("td", string="Size").find_next_sibling("td").text.strip()
            item_obj.locality = soup.find("td", string="Locality").find_next_sibling("td").text.strip()
            item_obj.note = soup.find("td", string="Note").find_next_sibling("td").text.strip()
            seller = soup.find("td", string="Seller").find_next_sibling("td").text.strip()
            item_obj.seller = seller.split("(")[0].strip()

            st_v_text = soup.find("td", string="Start Price").find_next_sibling("td").text
            if "approx" not in st_v_text:
                item_obj.start_price = float(st_v_text.split("€")[0].strip().replace(",", "."))
            else:
                item_obj.start_price = float(st_v_text.split(" (approx. ")[1].split("€")[0].strip().replace(",", "."))
            current_price_td = soup.find("td", string="Current Price").find_next_sibling("td")
            current_price_content = current_price_td.text.strip()

            if "approx" not in current_price_content:
                item_obj.current_price = float(current_price_content.split("€")[0].strip().replace(",", "."))
            else:
                item_obj.current_price = float(
                    current_price_content.split(" (approx. ")[1].split("€")[0].strip().replace(",", ".")
                )

            # 提取offered by的信息
            offered_by_prefix = "offered by"
            item_obj.owner = (
                current_price_content[current_price_content.find(offered_by_prefix) + len(offered_by_prefix) :]
                .split("\xa0")[0]
                .strip()
            )
            item_obj.end_date = soup.find("td", string="End").find_next_sibling("td").text.split(">")[0].strip()

            await insert_bid_item(item_obj)
    except AttributeError:
        with open("skip.log", "a", encoding="utf-8") as f:
            f.write(f"{id}\n")
    except:
        with open("error.log", "a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")


async def create_db():
    # 建立连接（请根据实际情况替换`database_url`）
    conn = await asyncpg.connect("postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres")
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shellauction (
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
        )
    """
    )
    await conn.close()


async def insert_bid_item(bid_item):
    # 建立连接（请根据实际情况替换`database_url`）
    conn = await asyncpg.connect("postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres")
    await conn.execute(
        """
        INSERT INTO shellauction (item, name, image, family, size, locality, note, seller, start_price, current_price,end_date, owner)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
    """,
        bid_item.item,
        bid_item.name,
        bid_item.image,
        bid_item.family,
        bid_item.size,
        bid_item.locality,
        bid_item.note,
        bid_item.seller,
        bid_item.start_price,
        bid_item.current_price,
        bid_item.end_date,
        bid_item.owner,
    )

    await conn.close()


async def worker(queue, semaphore, sleep_time):
    async with aiohttp.ClientSession() as session:
        while not queue.empty():
            await semaphore.acquire()
            try:
                task = await queue.get()
                start_time = datetime.now()
                await get_info(task, session)
                semaphore.release()

                end_time = datetime.now()
                elapsed = (end_time - start_time).total_seconds()
                await asyncio.sleep(max(sleep_time - elapsed, 0))
            except Exception as e:
                print(f"Task {task} failed: {e}")
                semaphore.release()


async def main():
    await create_db()
    cnt = await get_current_cnt()
    print(cnt)
    queue = asyncio.Queue()  # 不需要设置maxsize除非有特别的需求
    for i in range(cnt, cnt + 40000, 1):  # 添加1000个任务到队列中
        await queue.put(i)

    request_per_second = 100
    # 计算每个请求之间应该睡眠的时间
    sleep_time = 1 / request_per_second

    semaphore = asyncio.Semaphore(request_per_second)  # 控制每秒的请求量

    workers = [worker(queue, semaphore, sleep_time) for _ in range(10)]  # 你可以根据需要调整worker的数量
    await asyncio.gather(*workers)


if __name__ == "__main__":
    st = time.time()
    asyncio.run(main())
    end = time.time()
    print(end - st)
