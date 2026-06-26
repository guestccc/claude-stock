"""
ETF 数据获取器
支持：基础信息同步、日线行情拉取、实时行情获取
日线数据通过 provider 架构获取，可切换数据源（etf_eastmoney / etf_sina）
"""
import time
import json
import re
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import func
from a_stock_db.database import db, to_json, ETFBasic, ETFDaily
from a_stock_db.config import REQUEST_DELAY
from a_stock_fetcher.providers import get_etf_provider


def _build_etf_daily_dict(code: str, record: dict) -> dict:
    """将 provider 返回的标准化记录构建为数据库写入格式"""
    return {
        "code": code,
        "日期": pd.to_datetime(record.get('date')),
        "开盘": record.get('open'),
        "收盘": record.get('close'),
        "最高": record.get('high'),
        "最低": record.get('low'),
        "成交量": record.get('volume'),
        "成交额": record.get('amount'),
        "振幅": record.get('amplitude'),
        "涨跌幅": record.get('pct_change'),
        "涨跌额": record.get('change'),
        "换手率": record.get('turnover'),
        "created_at": datetime.now(),
        "raw_data": to_json(record),
    }


def _upsert_etf_daily(session, daily: dict):
    """ETF 日线数据 upsert"""
    stmt = insert(ETFDaily).values(**daily)
    stmt = stmt.on_conflict_do_update(
        index_elements=['code', '日期'],
        set_={
            "开盘": daily["开盘"],
            "收盘": daily["收盘"],
            "最高": daily["最高"],
            "最低": daily["最低"],
            "成交量": daily["成交量"],
            "成交额": daily["成交额"],
            "振幅": daily["振幅"],
            "涨跌幅": daily["涨跌幅"],
            "涨跌额": daily["涨跌额"],
            "换手率": daily["换手率"],
            "raw_data": daily["raw_data"],
        }
    )
    session.execute(stmt)


def _parse_pct(value) -> float | None:
    """解析百分比字符串（如 '-1.66%' → -1.66）"""
    if value is None or value == '---' or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # 去掉 % 符号
        cleaned = str(value).replace('%', '').strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def fetch_etf_basic() -> dict:
    """
    全量同步 ETF 基础信息
    来源: akshare.fund_etf_fund_daily_em()
    :return: {'success': 成功写入数, 'total': 总数}
    """
    import akshare as ak

    print("=" * 50)
    print("同步 ETF 基础信息...")
    print("=" * 50)

    try:
        df = ak.fund_etf_fund_daily_em()
    except Exception as e:
        print(f"  获取失败: {e}")
        return {'success': 0, 'total': 0, 'error': str(e)}

    if df is None or df.empty:
        print("  返回空数据")
        return {'success': 0, 'total': 0}

    # 确定净值日期列（列名格式: 'YYYY-MM-DD-单位净值'）
    date_cols = [c for c in df.columns if re.match(r'^\d{4}-\d{2}-\d{2}-单位净值$', str(c))]
    nav_date = date_cols[0].replace('-单位净值', '') if date_cols else None

    session = db.get_session()
    success_count = 0

    try:
        for _, row in df.iterrows():
            # 基金简称列名可能不同版本有差异
            name = row.get('基金简称', '')
            etf_type = row.get('类型', '')

            # 净值字段
            nav_col = f'{nav_date}-单位净值' if nav_date else None
            acc_nav_col = f'{nav_date}-累计净值' if nav_date else None
            prev_nav_col = None
            for c in df.columns:
                if re.match(r'^\d{4}-\d{2}-\d{2}-单位净值$', str(c)) and c != nav_col:
                    prev_nav_col = c
                    break

            nav = None
            acc_nav = None
            if nav_col and nav_col in row.index:
                v = row[nav_col]
                nav = float(v) if pd.notna(v) and str(v) != '---' else None
            if acc_nav_col and acc_nav_col in row.index:
                v = row[acc_nav_col]
                acc_nav = float(v) if pd.notna(v) and str(v) != '---' else None

            # 市价和折价率
            market_price = None
            discount_rate = None
            if '市价' in row.index:
                v = row['市价']
                market_price = float(v) if pd.notna(v) and str(v) != '---' else None
            if '折价率' in row.index:
                discount_rate = _parse_pct(row['折价率'])

            fund = {
                'code': str(row['基金代码']).strip(),
                'name': str(name).strip() if name else '',
                'etf_type': str(etf_type).strip() if etf_type else '',
                'nav': nav,
                'acc_nav': acc_nav,
                'market_price': market_price,
                'discount_rate': discount_rate,
                'updated_at': datetime.now(),
                'raw_data': to_json(row.to_dict()),
            }

            stmt = insert(ETFBasic).values(**fund)
            stmt = stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'name': fund['name'],
                    'etf_type': fund['etf_type'],
                    'nav': fund['nav'],
                    'acc_nav': fund['acc_nav'],
                    'market_price': fund['market_price'],
                    'discount_rate': fund['discount_rate'],
                    'updated_at': fund['updated_at'],
                    'raw_data': fund['raw_data'],
                }
            )
            session.execute(stmt)
            success_count += 1

        session.commit()
        print(f"  写入 {success_count}/{len(df)} 只 ETF")
        return {'success': success_count, 'total': len(df)}

    except Exception as e:
        session.rollback()
        print(f"  数据库写入失败: {e}")
        return {'success': 0, 'total': len(df), 'error': str(e)}
    finally:
        session.close()


def fetch_etf_daily(code: str, start_date: str = None, end_date: str = None) -> bool:
    """
    获取单只 ETF 日线数据（通过 provider 架构，默认东方财富前复权）
    :param code: ETF 代码（如 510300）
    :param start_date: 开始日期 YYYY-MM-DD
    :param end_date: 结束日期 YYYY-MM-DD
    """
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    provider = get_etf_provider()
    records = provider.fetch_daily(code, start_date, end_date)

    if not records:
        return False

    session = db.get_session()
    try:
        for record in records:
            daily = _build_etf_daily_dict(code, record)
            _upsert_etf_daily(session, daily)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"  {code} 写入失败: {e}")
        return False
    finally:
        session.close()


def fetch_etf_daily_incremental(code: str, delay: float = REQUEST_DELAY) -> str:
    """
    增量获取单只 ETF 日线数据
    :param code: ETF 代码
    :param delay: 请求间隔
    :return: 成功返回 True，失败返回原因
    """
    session = db.get_session()
    try:
        latest_date = session.query(func.max(ETFDaily.日期)).filter(
            ETFDaily.code == code
        ).scalar()

        today = datetime.now().date()

        if latest_date:
            latest_date_only = latest_date.date()
            if latest_date_only >= today:
                session.close()
                return "已是最新"

        if latest_date:
            start = (latest_date.date() + timedelta(days=1)).strftime('%Y-%m-%d')
            end = today.strftime('%Y-%m-%d')
        else:
            start = (today - timedelta(days=365)).strftime('%Y-%m-%d')  # ETF 历史比股票短，默认拉1年
            end = today.strftime('%Y-%m-%d')

        session.close()

        result = fetch_etf_daily(code, start, end)
        time.sleep(delay)
        return True if result else "无数据"

    except Exception as e:
        session.close()
        return f"{type(e).__name__}: {str(e)[:50]}"


def fetch_all_etf_daily(
    limit: int = None,
    delay: float = REQUEST_DELAY,
) -> dict:
    """
    批量增量获取全部 ETF 日线数据
    :param limit: 限制数量
    :param delay: 请求间隔
    :return: {'success': 成功数, 'failed': [...], 'total': 总数}
    """
    session = db.get_session()
    etfs = session.query(ETFBasic).all()
    session.close()

    if not etfs:
        print("ETF 基础信息为空，请先运行: python3 -m a_stock_fetcher.cli etf-basic")
        return {'success': 0, 'failed': [], 'total': 0}

    if limit:
        etfs = etfs[:limit]

    print("=" * 50)
    print(f"批量增量获取 ETF 日线数据: {len(etfs)} 只")
    print("=" * 50)

    success_count = 0
    failed = []

    for i, etf in enumerate(etfs):
        print(f"[{i+1}/{len(etfs)}] {etf.code} {etf.name} ...", end=' ', flush=True)
        result = fetch_etf_daily_incremental(etf.code, delay=delay)
        if result is True or result == "已是最新":
            success_count += 1
            print("已是最新" if result == "已是最新" else "OK")
        else:
            failed.append({'code': etf.code, 'name': etf.name, 'reason': str(result)})
            print(f"FAIL ({result})")
        time.sleep(delay)

    print(f"\n成功: {success_count}/{len(etfs)}")
    if failed:
        print(f"失败 {len(failed)} 只:")
        for f in failed[:10]:
            print(f"  {f['code']} {f['name']}: {f['reason']}")

    return {'success': success_count, 'failed': failed, 'total': len(etfs)}


def fetch_etf_daily_full_history(code: str, delay: float = REQUEST_DELAY) -> str:
    """
    获取单只 ETF 全部历史日线数据
    :param code: ETF 代码
    :param delay: 请求间隔
    :return: 成功返回 True，已有完整数据返回提示，失败返回原因
    """
    session = db.get_session()
    try:
        # 检查已有数据
        latest_date = session.query(func.max(ETFDaily.日期)).filter(
            ETFDaily.code == code
        ).scalar()

        today = datetime.now().date()

        if latest_date and latest_date.date() >= today:
            count = session.query(ETFDaily).filter(ETFDaily.code == code).count()
            session.close()
            return f"已有完整数据 ({count} 条)"

        session.close()
    except Exception:
        session.close()

    # 拉取全部历史数据
    start_date = '2000-01-01'
    end_date = today.strftime('%Y-%m-%d')

    print(f"  {code} 拉取全部历史 ...", end=' ', flush=True)
    result = fetch_etf_daily(code, start_date, end_date)
    if result:
        print("OK")
        time.sleep(delay)
        return True
    else:
        print("FAIL")
        return "无数据"


def fetch_etf_realtime_ths() -> pd.DataFrame | None:
    """
    获取 ETF 实时行情（同花顺）
    :return: DataFrame 或 None
    """
    import akshare as ak
    try:
        df = ak.fund_etf_spot_ths()
        return df
    except Exception as e:
        print(f"获取 ETF 实时行情失败: {e}")
        return None


def _fix_etf_via_eastmoney(code: str, start: str, end: str, delay: float) -> str:
    """
    通过东方财富直连 API 修复 ETF 数据（使用独立 session）
    :return: 'ok:N' | 'fail:原因'
    """
    from a_stock_fetcher.providers import get_etf_provider
    provider = get_etf_provider('etf_eastmoney')
    records = provider.fetch_daily(code, start, end)
    if not records:
        return 'fail:东财无数据'
    inner_session = db.get_session()
    try:
        for record in records:
            daily = _build_etf_daily_dict(code, record)
            _upsert_etf_daily(inner_session, daily)
        inner_session.commit()
        time.sleep(delay)
        return f'ok:{len(records)}'
    except Exception as e:
        inner_session.rollback()
        return f'fail:数据库错误 {e}'
    finally:
        inner_session.close()


def _fix_etf_via_mx(code: str, start: str, end: str, etf_name: str = '') -> str:
    """
    通过妙想 API 修复 ETF 拆分数据（东财限流时的备用方案）
    妙想 API 返回前复权收盘价和复权单位净值增长率，可正确计算拆分日涨跌幅
    使用独立 session 避免与外层 session 冲突

    :param code: ETF 代码
    :param start: 开始日期 YYYY-MM-DD
    :param end: 结束日期 YYYY-MM-DD
    :param etf_name: ETF 名称（用于构建查询）
    :return: 'ok:修复N条' | 'fail:原因'
    """
    import re as _re
    import requests as _requests
    from a_stock_db.config import MX_APIKEY

    if not MX_APIKEY:
        return 'fail:MX_APIKEY未配置'

    # 构建自然语言查询
    start_dt = datetime.strptime(start, '%Y-%m-%d')
    end_dt = datetime.strptime(end, '%Y-%m-%d')
    time_desc = f"{start_dt.year}年{start_dt.month}月{start_dt.day}日到{end_dt.year}年{end_dt.month}月{end_dt.day}日"
    name_part = f"{code} {etf_name}" if etf_name else code
    query = f"{name_part} {time_desc} 每个交易日的收盘价 涨跌幅"

    headers = {"Content-Type": "application/json", "apikey": MX_APIKEY}
    data = {"toolQuery": query}

    try:
        resp = _requests.post(
            "https://mkapi2.dfcfs.com/finskillshub/api/claw/query",
            headers=headers, json=data, timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return f'fail:妙想API请求失败 {e}'

    if result.get('status') != 0:
        return f'fail:妙想API状态异常 {result.get("message", "")}'

    # 解析返回数据：找到包含 收盘价 + 复权单位净值增长率 的 DTO
    dto_list = (result.get('data', {})
                .get('data', {})
                .get('searchDataResultDTO', {})
                .get('dataTableDTOList', []))

    if not dto_list:
        return 'fail:妙想无数据返回'

    # 提取日期 → 收盘价 和 日期 → 涨跌幅 的映射
    date_close_map = {}
    date_pct_map = {}

    for dto in dto_list:
        if not isinstance(dto, dict):
            continue
        table = dto.get('table', {})
        name_map = dto.get('nameMap', {})
        head = table.get('headName', [])
        if not head:
            continue

        # 识别本 DTO 包含的指标
        has_close = False
        has_pct = False
        close_key = None
        pct_key = None
        for key, label in name_map.items():
            if label == '收盘价':
                has_close = True
                close_key = key
            elif label == '复权单位净值增长率':
                has_pct = True
                pct_key = key

        if not (has_close or has_pct):
            continue

        for i, raw_date in enumerate(head):
            match = _re.match(r'(\d{4}-\d{2}-\d{2})', str(raw_date))
            if not match:
                continue
            date_str = match.group(1)

            if has_close and close_key:
                vals = table.get(close_key, [])
                if i < len(vals):
                    raw = str(vals[i]).replace('元', '').strip()
                    try:
                        date_close_map[date_str] = float(raw)
                    except (ValueError, TypeError):
                        pass

            if has_pct and pct_key:
                vals = table.get(pct_key, [])
                if i < len(vals):
                    pct = _parse_pct(str(vals[i]))
                    if pct is not None:
                        date_pct_map[date_str] = pct

    if not date_close_map and not date_pct_map:
        return 'fail:妙想返回数据无法解析'

    # 使用独立 session 更新数据库，避免与外层 session 冲突
    from sqlalchemy import text
    inner_session = db.get_session()
    try:
        updated = 0
        for date_str, close_price in date_close_map.items():
            pct = date_pct_map.get(date_str)
            if pct is None:
                continue

            result = inner_session.execute(text(
                "UPDATE etf_daily SET 收盘=:close, 涨跌幅=:pct, 涨跌额=NULL "
                "WHERE code=:code AND date(日期)=:date AND ABS(涨跌幅) > 15"
            ), {'close': close_price, 'pct': pct, 'code': code, 'date': date_str})
            if result.rowcount > 0:
                updated += 1

        # 更新涨跌额：用相邻交易日的收盘价计算
        if updated > 0:
            rows = inner_session.execute(text(
                "SELECT 日期, 收盘 FROM etf_daily WHERE code=:code "
                "AND date(日期) >= :start AND date(日期) <= :end ORDER BY 日期"
            ), {'code': code, 'start': start, 'end': end}).fetchall()

            for i in range(1, len(rows)):
                prev_close = rows[i - 1][1]
                curr_close = rows[i][1]
                if prev_close and curr_close:
                    change = round(curr_close - prev_close, 4)
                    inner_session.execute(text(
                        "UPDATE etf_daily SET 涨跌额=:change WHERE code=:code AND date(日期)=:date"
                    ), {'change': change, 'code': code, 'date': str(rows[i][0])[:10]})

        inner_session.commit()
        return f'ok:{updated}'
    except Exception as e:
        inner_session.rollback()
        return f'fail:数据库错误 {e}'
    finally:
        inner_session.close()


def fix_etf_split_data(delay: float = 2.0, source: str = 'auto') -> dict:
    """
    检查并修复 ETF 拆分/合并导致的虚假涨跌幅数据
    扫描所有 abs(涨跌幅) > 15% 的记录，获取正确的前复权数据覆盖

    数据源策略:
      - auto: 先尝试东财直连，失败后自动切换妙想 API
      - eastmoney: 仅使用东财直连（可能被限流）
      - mx: 仅使用妙想 API（稳定但每日有额度限制）

    :param delay: 每次请求间隔（秒）
    :param source: 数据源 'auto' | 'eastmoney' | 'mx'
    :return: {'scanned': 总异常数, 'fixed': 修复数, 'failed': [...]}
    """
    from a_stock_db.database import ETFDaily
    from sqlalchemy import text

    # 1. 扫描阶段：独立 session，用完立即关闭
    scan_session = db.get_session()
    rows = scan_session.execute(text(
        "SELECT code, 日期, 收盘, 涨跌幅 FROM etf_daily "
        "WHERE ABS(涨跌幅) > 15 "
        "ORDER BY 日期"
    )).fetchall()

    if not rows:
        scan_session.close()
        print("未发现异常数据，无需修复")
        return {'scanned': 0, 'fixed': 0, 'failed': []}

    print(f"发现 {len(rows)} 条异常记录，涉及 {len(set(r[0] for r in rows))} 只 ETF")
    print("-" * 60)
    for r in rows:
        print(f"  {r[0]}  {r[1]}  收{r[2]}  涨跌{r[3]:.2f}%")
    print("-" * 60)

    # 收集需要修复的 (code, date) 范围
    code_dates = {}
    for r in rows:
        code = r[0]
        date_str = r[1].strftime('%Y-%m-%d') if hasattr(r[1], 'strftime') else str(r[1])[:10]
        if code not in code_dates:
            code_dates[code] = {'min': date_str, 'max': date_str}
        else:
            if date_str < code_dates[code]['min']:
                code_dates[code]['min'] = date_str
            if date_str > code_dates[code]['max']:
                code_dates[code]['max'] = date_str

    # 获取 ETF 名称映射（用于妙想查询）
    etf_names = {}
    if source in ('auto', 'mx'):
        etfs = scan_session.query(ETFBasic).filter(
            ETFBasic.code.in_(list(code_dates.keys()))
        ).all()
        etf_names = {e.code: e.name for e in etfs}

    # 关闭扫描 session，释放数据库锁
    scan_session.close()

    # 2. 逐只 ETF 修复（每次使用独立 session）
    fixed = 0
    failed = []
    use_mx_fallback = (source == 'auto')

    for code, dates in code_dates.items():
        from datetime import datetime as dt
        min_d = dt.strptime(dates['min'], '%Y-%m-%d') - timedelta(days=3)
        max_d = dt.strptime(dates['max'], '%Y-%m-%d') + timedelta(days=3)
        start = min_d.strftime('%Y-%m-%d')
        end = max_d.strftime('%Y-%m-%d')
        etf_name = etf_names.get(code, '')

        # 策略1: 东财直连（source=eastmoney 或 auto 的首选）
        if source in ('eastmoney', 'auto'):
            print(f"\n修复 {code} {etf_name} ({start} ~ {end}) [东财]...", end=' ', flush=True)
            try:
                result = _fix_etf_via_eastmoney(code, start, end, delay)
                if result.startswith('ok'):
                    fixed += 1
                    print(f"OK ({result})")
                    continue
                else:
                    print(f"东财失败: {result}")
                    if not use_mx_fallback:
                        failed.append({'code': code, 'reason': result})
                        continue
            except Exception as e:
                print(f"东财异常: {e}")
                if not use_mx_fallback:
                    failed.append({'code': code, 'reason': str(e)[:80]})
                    continue

        # 策略2: 妙想 API（source=mx 或 auto 的备用）
        if source in ('mx', 'auto'):
            print(f"  → 切换妙想 API 修复 {code}...", end=' ', flush=True)
            try:
                result = _fix_etf_via_mx(code, start, end, etf_name)
                if result.startswith('ok'):
                    fixed += 1
                    print(f"OK ({result})")
                else:
                    print(f"FAIL ({result})")
                    failed.append({'code': code, 'reason': result})
            except Exception as e:
                print(f"FAIL: {e}")
                failed.append({'code': code, 'reason': str(e)[:80]})
            time.sleep(3)  # 妙想 API 限流保护（需 >= 3s）

    print(f"\n{'=' * 60}")
    print(f"修复完成: {fixed}/{len(code_dates)} 只 ETF, {len(failed)} 只失败")
    if failed:
        print("失败列表:")
        for f in failed:
            print(f"  {f['code']}: {f['reason']}")
    return {'scanned': len(rows), 'fixed': fixed, 'failed': failed}


if __name__ == '__main__':
    # 测试
    print("测试 fetch_etf_basic...")
    result = fetch_etf_basic()
    print(result)
