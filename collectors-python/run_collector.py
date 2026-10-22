#!/usr/bin/env python3
"""
采集器运行器 - 供Rust后端调用
输出JSON格式的采集结果
"""
import sys
import json
import argparse
import logging
from contextlib import redirect_stdout
from datetime import datetime
from typing import List, Dict, Any

# 采集器映射（延迟导入）
COLLECTORS = {
    'mock': 'collectors.mock.MockCollector',
    'boyar': 'collectors.boyar_production.BoyarProductionCollector',
    'boyar_production': 'collectors.boyar_production.BoyarProductionCollector',
    'sina': 'collectors.sina_production.SinaProductionCollector',
    'sina_production': 'collectors.sina_production.SinaProductionCollector',
    'dce': 'collectors.dce.DCEFuturesCollector',
    'cft': 'collectors.cft.CFTSpotCollector',
}


def get_collector_class(collector_id: str):
    """动态导入采集器类"""
    if collector_id not in COLLECTORS:
        return None
    
    module_path = COLLECTORS[collector_id]
    module_name, class_name = module_path.rsplit('.', 1)
    
    # 动态导入
    import importlib
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def serialize_record(record) -> Dict[str, Any]:
    """序列化记录为JSON格式"""
    # 处理 datetime 对象
    collected_at = record.collected_at
    if isinstance(collected_at, datetime):
        collected_at = collected_at.isoformat()
    
    published_at = record.published_at
    if isinstance(published_at, datetime):
        published_at = published_at.isoformat()
    
    return {
        'business_date': record.business_date,
        'data_type': record.data_type,
        'indicator': record.indicator,
        'value': float(record.value),
        'unit': record.unit,
        'region': record.region,
        'source_url': record.source_url,
        'original_text': record.original_text,
        'collected_at': collected_at,
        'published_at': published_at,
        'metadata': record.metadata,
    }


def run_collector(collector_id: str, max_items: int = 100) -> Dict[str, Any]:
    """运行指定的采集器"""
    try:
        # 获取采集器类
        collector_class = get_collector_class(collector_id)
        if collector_class is None:
            return {
                'success': False,
                'records': [],
                'error': f'Unknown collector: {collector_id}. Available: {list(COLLECTORS.keys())}'
            }
        
        # 实例化采集器
        collector = collector_class()
        
        # 执行采集
        print(f"[run_collector] Starting {collector_id}...", file=sys.stderr)
        # stdout is the Rust bridge's JSON protocol; collector logs belong on stderr.
        with redirect_stdout(sys.stderr):
            records = collector.collect(max_items=max_items)
        print(f"[run_collector] Collected {len(records)} records", file=sys.stderr)
        
        # 序列化结果
        serialized_records = [serialize_record(r) for r in records]
        
        return {
            'success': True,
            'records': serialized_records,
            'error': None
        }
    
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        traceback.print_exc(file=sys.stderr)
        return {
            'success': False,
            'records': [],
            'error': error_msg
        }


def list_collectors() -> List[str]:
    """列出所有可用的采集器"""
    return list(COLLECTORS.keys())


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description='Run data collector')
    parser.add_argument('--collector', type=str, help='Collector ID to run')
    parser.add_argument('--max-items', type=int, default=100, help='Maximum items to collect')
    parser.add_argument('--format', type=str, default='json', choices=['json'], help='Output format')
    parser.add_argument('--list', action='store_true', help='List available collectors')
    
    args = parser.parse_args()
    
    # 列出采集器
    if args.list:
        result = list_collectors()
        print(json.dumps(result, ensure_ascii=False))
        return
    
    # 运行采集器
    if not args.collector:
        print(json.dumps({
            'success': False,
            'records': [],
            'error': 'No collector specified. Use --collector <id>'
        }))
        sys.exit(1)
    
    result = run_collector(args.collector, args.max_items)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
