from flask import Blueprint, request
import traceback

search_engine = Blueprint("search_engine", __name__)

from psycopg_pool import ConnectionPool

# 数据库连接配置
pool = ConnectionPool(
    conninfo="postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres",
    min_size=1,
    max_size=50,
    open=True,  # 立即开始连接过程
)


@search_engine.route("/search/", methods=["POST"])
def search():
    try:
        name_param = request.json.get("name")
        family_param = request.json.get("family")
        order_param = request.json.get("order", "nto")
        similirity = request.json.get("similarity", "3")
        sold_filter = request.json.get("sold_status", False)
        try:
            similarity_param = int(similirity) / 10
        except ValueError:
            similarity_param = 0.3
        similarity_param = max(0, min(similarity_param, 1))

        if not any([name_param, family_param]):
            return []
        with pool.connection() as conn:
            with conn.cursor() as cur:
                params = tuple(
                    x
                    for x in [
                        f"%{name_param}%" if name_param != "" else None,
                        f"{family_param}" if family_param != "" else None,
                    ]
                    if x is not None
                )
                sql = construct_query(name_param, family_param, order_param, sold_status=sold_filter)
                cur.execute(f"SELECT set_limit({similarity_param});")
                cur.execute(sql, params)
                results = cur.fetchall()
                if len(results) == 0:
                    return [
                        {
                            "current_price": 0,
                            "family": "",
                            "idx": 0,
                            "image": [],
                            "name": "无结果",
                            "note": "",
                            "seller": "",
                            "size": "",
                            "end_date": "",
                            "start_price": 0,
                        }
                    ]
                return format_result(results)
    except:
        print(traceback.format_exc())
        return "INTERNAL ERROR!"


def format_result(results):

    return [
        {
            "idx": idx,
            "image": images_fix(item[0]),
            "name": item[1],
            "family": item[2],
            "size": item[3],
            "note": item[4],
            "seller": item[5],
            "end_date": item[8] if "..." not in item[8] else "已删除",
            "start_price": item[6],
            "current_price": item[7],
            "sold": owner_convert(item[9]),
        }
        for idx, item in enumerate(results)
    ]


def images_fix(images_links: str):
    res = []
    res2 = []
    imgs = [x for x in images_links.split(";") if x]
    res = imgs
    for img in imgs:
        if "thumb" in img:
            res2.append(img.replace("_thumb", ""))
    if res2:
        return res2
    return res


def owner_convert(i):
    if "no Bids" in i:
        return False
    return True


def construct_query(name: str, family: str, order: str = "nto", sold_status=False) -> str:
    limit = 100
    where = ""
    if name and family:
        where += "name %% %s AND family = %s"
    elif name:
        where += "name %% %s "
    elif family:
        where += "family %% %s"

    if sold_status and (name or family):
        where += "AND owner not like '%%no Bids%%'"

    kw_map = {
        "nto": f"item desc limit {limit}",
        "otn": f"item limit {limit}",
        "cpd": f"current_price desc limit {limit}",
        "cpu": f"current_price limit {limit}",
        "spd": f"start_price limit {limit}",
        "spu": f"start_price limit {limit}",
    }
    order_fix = kw_map.get(order, kw_map.get("nto"))

    re = f"SELECT image,name,family,size,note,seller,start_price,current_price,end_date,owner FROM shellauction WHERE {where} ORDER BY {order_fix};"

    return re


if __name__ == "__main__":

    print(construct_query("123", "dd", ""))
