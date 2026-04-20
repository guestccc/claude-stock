"""
数据清洗模块
用于补全日线表中缺失的衍生指标（涨跌幅、涨跌额、振幅）
"""
from a_stock_db.database import db, StockDaily


def clean_daily_data(limit: int = None, codes: list = None) -> dict:
    """
    清洗日线数据：计算并补全涨跌幅、涨跌额、振幅

    计算规则（以昨日收盘价为基准）：
      - 涨跌额 = 当日收盘 - 前日收盘
      - 涨跌幅 = (当日收盘 - 前日收盘) / 前日收盘 * 100
      - 振幅   = (当日最高 - 当日最低) / 前日收盘 * 100

    对于每只股票的第一条历史记录（无前日收盘价），无法计算，予以跳过。

    :param limit: 限制处理的股票数量
    :param codes: 指定股票代码列表，None 表示处理全部
    :return: {'processed': 处理股票数, 'updated': 更新记录数, 'skipped': 跳过记录数}
    """
    session = db.get_session()

    try:
        # 获取目标股票代码列表（去重）
        query = session.query(StockDaily.code).distinct()
        if codes:
            query = query.filter(StockDaily.code.in_(codes))
        stock_codes = [r[0] for r in query.all()]

        if limit:
            stock_codes = stock_codes[:limit]

        total_stocks = len(stock_codes)
        print("=" * 50)
        print(f"日线数据清洗: 共 {total_stocks} 只股票待处理")
        print("=" * 50)

        total_updated = 0
        total_skipped = 0

        for i, code in enumerate(stock_codes):
            # 查询该股票所有记录，按日期升序排列
            records = session.query(
                StockDaily.id,
                StockDaily.日期,
                StockDaily.收盘,
                StockDaily.最高,
                StockDaily.最低,
                StockDaily.涨跌幅,
            ).filter(
                StockDaily.code == code
            ).order_by(
                StockDaily.日期.asc()
            ).all()

            if not records:
                continue

            updates = []
            prev_close = None

            for r in records:
                # 如果涨跌幅已有值，跳过更新，但仍需维护 prev_close 链
                if r.涨跌幅 is not None:
                    if r.收盘 is not None:
                        prev_close = r.收盘
                    continue

                # 有前日收盘价且当日收盘价有效时，才能计算
                if prev_close is not None and prev_close > 0 and r.收盘 is not None:
                    涨跌额 = round(r.收盘 - prev_close, 4)
                    涨跌幅 = round((r.收盘 - prev_close) / prev_close * 100, 4)

                    振幅 = None
                    if r.最高 is not None and r.最低 is not None:
                        振幅 = round((r.最高 - r.最低) / prev_close * 100, 4)

                    updates.append({
                        'id': r.id,
                        '涨跌额': 涨跌额,
                        '涨跌幅': 涨跌幅,
                        '振幅': 振幅,
                    })
                    total_updated += 1
                else:
                    total_skipped += 1

                # 更新 prev_close 供下一天使用（即使当天停牌无收盘价，也保持前一天的）
                if r.收盘 is not None:
                    prev_close = r.收盘

            # 批量写入更新（每 500 条一提交，避免单事务过大）
            if updates:
                for j in range(0, len(updates), 500):
                    chunk = updates[j:j + 500]
                    session.bulk_update_mappings(StockDaily, chunk)
                session.commit()

            if (i + 1) % 100 == 0 or (i + 1) == total_stocks:
                print(
                    f"[{i + 1}/{total_stocks}] {code} "
                    f"更新 {len(updates)} 条 "
                    f"(累计更新 {total_updated} 条, 跳过 {total_skipped} 条)"
                )

        print(
            f"\n清洗完成: 处理 {total_stocks} 只股票, "
            f"更新 {total_updated} 条记录, 跳过 {total_skipped} 条记录"
        )
        return {
            'processed': total_stocks,
            'updated': total_updated,
            'skipped': total_skipped,
        }

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
