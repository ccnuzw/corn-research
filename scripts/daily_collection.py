#!/usr/bin/env python3
"""
每日采集脚本 - 玉米研究系统V2
执行所有已配置的采集器，保存原始数据到文件
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# 添加collectors-python到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'collectors-python'))

from collectors.mock import MockCollector
from collectors.boyar_v2 import BoyarCollectorV2
from collectors.sina_v2 import SinaCollectorV2
# from collectors.dce import DCEFuturesCollector
# from collectors.boyar import BoyarCollector
# from collectors.cft import CFTSpotCollector


def ensure_dirs():
    """确保必要的目录存在"""
    dirs = [
        'data/raw',
        'data/structured',
        'logs'
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def save_records(collector_id: str, records: list):
    """保存采集记录到文件"""
    if not records:
        return None, None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # 保存到data/raw/
    raw_file = f"data/raw/{collector_id}_{timestamp}.json"
    
    # 转换为可序列化格式
    serializable_records = []
    for r in records:
        serializable_records.append({
            'business_date': r.business_date,
            'collected_at': r.collected_at.isoformat(),
            'published_at': r.published_at.isoformat() if r.published_at else None,
            'data_type': r.data_type,
            'indicator': r.indicator,
            'value': r.value,
            'unit': r.unit,
            'region': r.region,
            'source_url': r.source_url,
            'original_text': r.original_text,
            'metadata': r.metadata
        })
    
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump({
            'collector_id': collector_id,
            'collected_at': timestamp,
            'date': date_str,
            'count': len(records),
            'records': serializable_records
        }, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 已保存: {raw_file}")
    
    return raw_file, len(records)


def run_collector(collector, name: str) -> dict:
    """运行单个采集器"""
    print(f"\n{'='*60}")
    print(f"运行采集器: {name}")
    print(f"{'='*60}")
    
    start_time = datetime.now()
    
    try:
        # 执行采集
        records = collector.collect()
        
        # 保存数据
        if records:
            raw_file, count = save_records(collector.collector_id, records)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'collector': name,
                'collector_id': collector.collector_id,
                'success': True,
                'count': count,
                'raw_file': raw_file,
                'duration': duration
            }
        else:
            print(f"  ⚠ 未采集到数据")
            return {
                'collector': name,
                'collector_id': collector.collector_id,
                'success': False,
                'error': 'No data collected'
            }
            
    except Exception as e:
        print(f"  ✗ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'collector': name,
            'collector_id': collector.collector_id,
            'success': False,
            'error': str(e)
        }


def main():
    """主函数"""
    print("\n" + "="*60)
    print("玉米研究系统V2 - 每日采集任务")
    print("="*60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 确保目录存在
    ensure_dirs()
    
    # 配置采集器
    collectors = [
        (MockCollector(), "Mock测试数据"),
        (BoyarCollectorV2(), "博亚和讯V2"),
        (SinaCollectorV2(), "新浪财经V2"),
        # (CFTSpotCollector(), "CFT现货报价"),  # URL 404
        # (DCEFuturesCollector(), "DCE期货"),  # 412错误
    ]
    
    results = []
    
    # 依次运行采集器
    for collector, name in collectors:
        result = run_collector(collector, name)
        results.append(result)
    
    # 生成汇总报告
    print(f"\n{'='*60}")
    print("采集完成汇总")
    print(f"{'='*60}")
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    total_records = sum(r.get('count', 0) for r in results if r['success'])
    
    print(f"采集器: {success_count}/{total_count} 成功")
    print(f"总记录数: {total_records}")
    print(f"\n详细结果:")
    
    for r in results:
        status = "✓" if r['success'] else "✗"
        if r['success']:
            print(f"  {status} {r['collector']:15} | {r['count']:4} 条 | {r.get('duration', 0):.2f}秒 | {r.get('raw_file', '')}")
        else:
            print(f"  {status} {r['collector']:15} | 失败: {r.get('error', 'Unknown')}")
    
    # 保存执行日志
    log_file = f"logs/collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'success_count': success_count,
            'total_count': total_count,
            'total_records': total_records,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 执行日志: {log_file}")
    print("="*60 + "\n")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    exit(main())
