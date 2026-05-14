import asyncio
import aiohttp
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


SHELL_LIST = [
    (3075839, 65),
    (3106148, 20),
    (3231635, 20),
    (3231537, 20),
    (2086216, 20),
    (3430398, 500),
    (3413353, 30),
    (3413728, 15),
    (3440994, 30),
    (3293996, 30),
    (3440787, 20),
    (3448714, 2000),
    (3447043, 180),
    (2923920, 30),
    (3430366, 200),
    (3430402, 10),
    (3430403, 50),
]
USERNAME = "kbytetutu"
PASS = "Tu1994125%2C.%2Fsa"
# USERNAME = "sthaohaoting"
# PASS = "Qq_12345679"


async def login(session):
    """
    Logs into the shell auction website using the provided credentials.

    Returns:
        requests.Session: The authenticated session.
    """
    url = "https://www.shellauction.net/login_ok.php"

    payload = f"command=login&user={USERNAME}&pass={PASS}"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": "cookie_accepted=1",
        "Origin": "https://www.shellauction.net",
        "Pragma": "no-cache",
        "Referer": "https://www.shellauction.net/login.php",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    async with session.post(url, headers=headers, data=payload) as response:
        if response.status == 200:
            res = await response.text()
            if "The username or the password are wrong" in res:
                print("登录失败")
            else:
                print("登录成功")
        else:
            print("登录失败")
        return session


async def get_bid_item_info(session: aiohttp.ClientSession, url: str, price: int, offset_time: float) -> dict:
    if not price:
        price = 0
    id = bid_check = has_watch = pres = offer_max_increase = offerta = 0
    async with session.get(url) as response:
        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        # 获取相关数据
        id = soup.find("input", {"type": "hidden", "name": "id"})["value"]
        bid_check = soup.find("input", {"type": "hidden", "name": "bid_check"})["value"]
        has_watch = soup.find("input", {"type": "hidden", "name": "hasWatch"})["value"]
        pres = soup.find("input", {"type": "hidden", "name": "pres"})["value"]
        offer_max_increase = soup.find("input", {"type": "hidden", "name": "offer_max_increase"})["value"]
        offerta = soup.find("input", {"type": "hidden", "name": "offerta"})["value"]

        end_td = soup.find("td", text="End")

        # 检查是否找到了元素，并尝试定位相邻的含日期时间的<td>元素
        if end_td:
            # 获取相邻的含日期时间的<td>元素
            date_time_td = end_td.find_next_sibling("td")
            if date_time_td:
                # 提取日期时间字符串
                date_time_str = date_time_td.text
                # 分割日期和时间
                date_str, time_str = date_time_str.split(" > ")
                full_datetime_str = date_str + " " + time_str
                # 转换为datetime对象
                date_time_obj = datetime.strptime(full_datetime_str, "%d-%m-%Y %H:%M:%S")
                # print(f"截拍时间: {date_time_obj}")
            else:
                print("Date-time element not found")
        else:
            print('Element with text "End" not found')

        # print("---")
        # print(f"id: {id}")
        # print(f"bid_check: {bid_check}")
        # print(f"has_watch: {has_watch}")
        # print(f"pres: {pres}")
        # print(f"offer_max_increase: {offer_max_increase}")
        # print(f"offerta: {offerta}")
        # print("---")
        return {
            "id": id,
            "bid_check": bid_check,
            "has_watch": has_watch,
            "pres": pres,
            "offer_max_increase": offer_max_increase,
            "offerta": offerta,
            "price": price,
            "end_time": date_time_obj,
            "offset_time": offset_time,
        }


async def bid(
    bid_check: str,
    has_watch: str,
    offerta: str,
    price: int,
    offer_max_increase: int,
    id: int,
    session: aiohttp.ClientSession,
    target_time: datetime,
    offset_time: float = 0.8,
):
    bid_url = "https://www.shellauction.net/auction_offer.php"

    # 计算当前时间到目标时间的等待时间（秒）
    now = datetime.now()
    wait_seconds = (target_time - now).total_seconds() - offset_time

    print(f"id {id} 已准备好出价，预计等待{wait_seconds}秒")
    wait_seconds = max(wait_seconds, 0)  # 防止负数

    # 等待直到指定的时间
    await asyncio.sleep(wait_seconds)

    payload = f"bid_check={bid_check}&hasWatch={has_watch}&offerta={offerta}&offerta_max={price}&offer_max_increase={offer_max_increase}&id={id}"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.shellauction.net",
        "Pragma": "no-cache",
        "Referer": f"https://www.shellauction.net/auction_offer_alert.php?id={id}",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    # response = session.post(bid_url, headers=headers, data=payload)
    # if response.ok:
    #     # print(response.text)
    #     print(f"id:{id}的物品出价完毕")
    async with session.post(bid_url, headers=headers, data=payload) as response:
        if response.status == 200:
            bid_time = datetime.now()
            html = await response.text()
            if "Minimum offer is" in html:
                print(f"id {id} 出价失败，时间 {bid_time} ,低于其他出价。")
            elif "Please login to bid" in html:
                print(f"id {id} 出价失败，时间 {bid_time} ,登录失效。")
            else:
                print(f"id {id} 出价成功，时间 {bid_time}")
        else:
            print(f"Failed to bid for item {id}")


async def main_work():
    async with aiohttp.ClientSession() as session:
        await login(session)

        shell_list = []
        for i in SHELL_LIST:
            tmp = ("", 0)
            tmp = (f"https://www.shellauction.net/auction_shell.php?id={i[0]}&pres=1", i[1])
            shell_list.append(tmp)

        to_bid = []
        for item in shell_list:
            if len(item) > 2:
                to_bid.append(await get_bid_item_info(session, item[0], item[1], item[2]))
            else:
                random_offset = random.randint(80, 300) / 100
                to_bid.append(await get_bid_item_info(session, item[0], item[1], random_offset))

        print(shell_list)
        print(to_bid)

        print("开始进入等待模式")

        tasks = [
            bid(
                item["bid_check"],
                item["has_watch"],
                item["offerta"],
                item["price"],
                item["offer_max_increase"],
                item["id"],
                session,
                item["end_time"],
                item["offset_time"],
            )
            for item in to_bid
        ]
        await asyncio.gather(*tasks)

        print("All Done")


async def test():
    async with aiohttp.ClientSession() as session:
        await login(session)
        print(datetime.now())
        await bid(
            "5c4f6704d048e4969cb6a931129ba2c2",
            0,
            offerta=360,
            price=300,
            offer_max_increase=0,
            id=3335188,
            session=session,
            target_time=datetime.now() + timedelta(seconds=15),
            offset_time=14,
        )


if __name__ == "__main__":
    asyncio.run(main_work())
    # asyncio.run(test())
