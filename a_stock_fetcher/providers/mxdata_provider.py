"""
东方财富妙想（MX-Data）日线数据源 Provider
通过自然语言 API 获取股票日线数据，支持批量查询
"""
import os
import re
import json
import math
import requests
from typing import List, Dict, Optional
from datetime import datetime
from .base import DailyDataProvider


# 中文单位 → 数值倍率（按长度降序匹配，避免"万元"被"万"先匹配）
_UNIT_MAP = [
    ('亿元', 1e8),
    ('万股', 1e4),
    ('万元', 1e4),
    ('万', 1e4),
    ('元', 1),
]

# 批量查询每批最多股票数
# 实测：批量查询 API 不稳定（10只命中率约60%），单只100%可靠
# 设为 1 逐只查询，150次额度 = 150只/天
_BATCH_SIZE = 1


def _parse_numeric(value_str: str) -> Optional[float]:
    """
    解析带中文单位后缀的数值字符串
    如 "1371.66元" → 1371.66, "333.7万股" → 3337000, "45.83亿元" → 4583000000
    """
    if not value_str or not isinstance(value_str, str):
        return None

    value_str = value_str.strip()
    if not value_str:
        return None

    for suffix, multiplier in _UNIT_MAP:
        if value_str.endswith(suffix):
            num_part = value_str[:-len(suffix)].strip()
            try:
                result = float(num_part) * multiplier
                # 修整浮点精度：亿元转换后四舍五入到整数
                if multiplier >= 1e8:
                    result = round(result)
                elif multiplier >= 1e4:
                    result = round(result, 2)
                return result
            except ValueError:
                return None

    # 无单位后缀，尝试直接转数值
    try:
        return float(value_str)
    except ValueError:
        return None


def _parse_date(date_str: str) -> Optional[str]:
    """
    解析妙想返回的日期字符串，去掉星期后缀
    如 "2026-04-30(日)" → "2026-04-30"
    如 "2026-05-08 16:56" → "2026-05-08"
    """
    if not date_str:
        return None
    match = re.match(r'(\d{4}-\d{2}-\d{2})', str(date_str))
    return match.group(1) if match else None


def _compute_month_range(start_date: str, end_date: str) -> str:
    """
    根据日期范围构造自然语言时间描述
    :param start_date: "YYYY-MM-DD"
    :param end_date: "YYYY-MM-DD"
    :return: 如 "近1个月" 或 "2026年1月到2026年4月"
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (end_dt - start_dt).days

    if delta_days <= 35:
        return "近1个月"
    elif delta_days <= 95:
        return "近3个月"
    elif delta_days <= 185:
        return "近6个月"
    elif delta_days <= 370:
        return "近1年"
    else:
        return f"{start_dt.year}年{start_dt.month}月到{end_dt.year}年{end_dt.month}月"


class MxDataProvider(DailyDataProvider):
    """基于东方财富妙想 API 的日线数据源"""

    BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MX_APIKEY")
        if not self.api_key:
            raise ValueError(
                "MX_APIKEY 未设置，请设置环境变量：export MX_APIKEY=your_key"
            )

    def _get_stock_names(self, codes: List[str]) -> Dict[str, str]:
        """从 StockBasic 表批量查股票名称"""
        from a_stock_db.database import db, StockBasic
        session = db.get_session()
        try:
            basics = session.query(StockBasic).filter(
                StockBasic.code.in_(codes)
            ).all()
            return {b.code: b.股票简称 for b in basics if b.股票简称}
        finally:
            session.close()

    def _build_query(self, stock_names: List[str], start_date: str, end_date: str) -> str:
        """构造自然语言查询"""
        time_desc = _compute_month_range(start_date, end_date)
        names_str = " ".join(stock_names)
        return f"{names_str}{time_desc}每个交易日的开盘价收盘价最高价最低价成交量成交额"

    def _call_api(self, query: str) -> dict:
        """调用妙想 API"""
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key,
        }
        data = {"toolQuery": query}
        resp = requests.post(self.BASE_URL, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _parse_response(self, result: dict) -> Dict[str, List[dict]]:
        """
        解析 API 响应，按股票代码分组返回标准化数据
        :return: {code: [{date, open, close, high, low, volume, amount}]}
        """
        status = result.get("status")
        if status != 0:
            return {}

        inner = result.get("data", {}).get("data", {}).get("searchDataResultDTO", {})
        dto_list = inner.get("dataTableDTOList", [])
        if not dto_list:
            return {}

        parsed = {}
        for dto in dto_list:
            if not isinstance(dto, dict):
                continue

            # 从 entityTagDTO 获取股票代码
            tag = dto.get("entityTagDTO") or {}
            code = tag.get("secuCode", "")
            if not code:
                continue

            table = dto.get("table", {})
            name_map = dto.get("nameMap", {})
            if not table or not isinstance(table, dict):
                continue

            dates = table.get("headName", [])
            if not dates:
                continue

            # 提取指标数据
            records = []
            for i, raw_date in enumerate(dates):
                date = _parse_date(str(raw_date))
                if not date:
                    continue

                record = {'date': date}
                for key, label in name_map.items():
                    if key == 'headNameSub':
                        continue
                    values = table.get(key, [])
                    if i >= len(values):
                        continue
                    raw_val = str(values[i]) if values[i] is not None else ""

                    if label == '开盘价':
                        record['open'] = _parse_numeric(raw_val)
                    elif label in ('最新价', '收盘价'):
                        record['close'] = _parse_numeric(raw_val)
                    elif label == '最高价':
                        record['high'] = _parse_numeric(raw_val)
                    elif label == '最低价':
                        record['low'] = _parse_numeric(raw_val)
                    elif label == '成交量':
                        record['volume'] = _parse_numeric(raw_val)
                    elif label == '成交额':
                        record['amount'] = _parse_numeric(raw_val)

                # 至少有日期和一个价格字段才记录
                if any(k in record for k in ('open', 'close', 'high', 'low')):
                    records.append(record)

            if records:
                parsed[code] = records

        return parsed

    def fetch_daily(self, code: str, start_date: str, end_date: str) -> List[dict]:
        """
        获取单只股票日线数据
        :param code: 股票代码（如 "600519"）
        :param start_date: "YYYY-MM-DD"
        :param end_date: "YYYY-MM-DD"
        :return: 标准化记录列表
        """
        names = self._get_stock_names([code])
        stock_name = names.get(code, code)
        query = self._build_query([stock_name], start_date, end_date)

        try:
            result = self._call_api(query)
            parsed = self._parse_response(result)
            return parsed.get(code, [])
        except Exception as e:
            print(f"  妙想 API 错误 ({code}): {e}")
            return []

    def supports_batch(self) -> bool:
        return True

    def fetch_daily_batch(self, codes: List[str], start_date: str, end_date: str) -> Dict[str, List[dict]]:
        """
        批量获取多只股票日线数据
        分批调用，每批 _BATCH_SIZE 只股票合一次 API 请求
        :return: {code: [records]}
        """
        if not codes:
            return {}

        names = self._get_stock_names(codes)
        all_parsed = {}

        # 分批
        for batch_start in range(0, len(codes), _BATCH_SIZE):
            batch_codes = codes[batch_start:batch_start + _BATCH_SIZE]
            batch_names = [names.get(c, c) for c in batch_codes]
            query = self._build_query(batch_names, start_date, end_date)

            try:
                result = self._call_api(query)
                parsed = self._parse_response(result)
                all_parsed.update(parsed)
            except Exception as e:
                batch_str = ", ".join(batch_codes)
                print(f"  妙想 API 批量错误 ({batch_str}): {e}")

        return all_parsed

    def name(self) -> str:
        return "mxdata"

    def source_desc(self) -> str:
        return "妙想模拟组合数据"
