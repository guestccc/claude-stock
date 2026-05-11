"""板块行情服务 — 新浪行业板块实时数据"""
import re
import json
import time
import requests
from typing import List, Optional
from datetime import datetime, timedelta


# 内存缓存
_cache: dict = {'data': [], 'updated_at': 0}

SINA_HY_URL = 'https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php'
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://finance.sina.com.cn',
}


def _fetch_industry_boards() -> List[dict]:
    """从新浪拉取行业板块实时数据并解析"""
    resp = requests.get(SINA_HY_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    match = re.search(r'= ({.+})', resp.text)
    if not match:
        return []
    data = json.loads(match.group(1))

    results = []
    for key, val in data.items():
        parts = val.split(',')
        if len(parts) < 13:
            continue
        try:
            results.append({
                'code': key,
                'name': parts[1],
                'stock_count': int(parts[2]),
                'avg_price': round(float(parts[3]), 2),
                'change': round(float(parts[4]), 2),
                'change_pct': round(float(parts[5]), 2),
                'volume': int(parts[6]),
                'amount': int(parts[7]),
                'lead_stock_code': parts[8],
                'lead_stock_price': round(float(parts[9]), 2),
                'lead_stock_change': round(float(parts[10]), 2),
                'lead_stock_change_pct': round(float(parts[11]), 2),
                'lead_stock_name': parts[12],
            })
        except (ValueError, IndexError):
            continue

    # 按涨跌幅降序
    results.sort(key=lambda x: x['change_pct'], reverse=True)
    return results


def get_industry_boards(cache_minutes: int = 2) -> List[dict]:
    """获取行业板块数据（带缓存）"""
    now = time.time()
    cutoff = now - cache_minutes * 60
    if _cache['data'] and _cache['updated_at'] > cutoff:
        return _cache['data']

    data = _fetch_industry_boards()
    if data:
        _cache['data'] = data
        _cache['updated_at'] = now
    return data


def refresh_industry_boards() -> dict:
    """强制刷新板块数据"""
    data = _fetch_industry_boards()
    if data:
        _cache['data'] = data
        _cache['updated_at'] = time.time()
    return {'total': len(data), 'updated_at': datetime.now().strftime('%H:%M:%S')}
