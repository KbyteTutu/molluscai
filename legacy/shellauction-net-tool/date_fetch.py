from psycopg_pool import ConnectionPool

# 数据库连接配置
pool = ConnectionPool(
    conninfo="postgresql://postgres:Tu1994125@127.0.0.1:5432/postgres",
    min_size=1,
    max_size=50,
    open=True,  # 立即开始连接过程
)


def current_cnt() -> int:
    # 取出当前数据库最大的值
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT MAX(item) FROM shellauction;")
            total = cur.fetchone()
    return total[0]


def data_fetch():
    start_read = current_cnt()
    print(start_read)


if __name__ == "__main__":
    data_fetch()
