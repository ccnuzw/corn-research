#!/usr/bin/env python3
"""
查看采集结果脚本
读取最新的采集数据并显示汇总
"""
import json
from pathlib import Path
from datetime import datetime


def view_latest_collection():
    """查看最新的采集结果"""
    
    # 查找最新的采集文件
    raw_dir = Path('data/raw')
    if not raw_dir.exists():
        print("✗ data/raw/ 目录不存在")
        return
    
    files = sorted(raw_dir.glob('*.json'), key=lambda f: f.stat().st_mtime, reverse=True)
    
    if not files:
        print("✗ 未找到采集数据")
        return
    
    print("\n" + "="*60)
    print("最近的采集结果")
    print("="*60 + "\n")
    
    # 显示最近5个文件
    for i, file in enumerate(files[:5]):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"[{i+1}] {file.name}")
        print(f"    采集器: {data.get('collector_id', 'unknown')}")
        print(f"    时间: {data.get('collected_at', 'unknown')}")
        print(f"    记录数: {data.get('count', 0)}")
        
        # 显示前3条数据
        records = data.get('records', [])
        for j, record in enumerate(records[:3]):
            print(f"      [{j+1}] {record.get('indicator', '?')}: {record.get('value', '?')} {record.get('unit', '?')} ({record.get('business_date', '?')})")
        
        if len(records) > 3:
            print(f"      ... 还有 {len(records) - 3} 条")
        
        print()
    
    # 查看最新的日志
    log_dir = Path('logs')
    if log_dir.exists():
        log_files = sorted(log_dir.glob('collection_*.json'), key=lambda f: f.stat().st_mtime, reverse=True)
        
        if log_files:
            print("="*60)
            print("最新执行日志")
            print("="*60 + "\n")
            
            with open(log_files[0], 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            print(f"时间: {log_data.get('timestamp', 'unknown')}")
            print(f"成功: {log_data.get('success_count', 0)}/{log_data.get('total_count', 0)}")
            print(f"总记录: {log_data.get('total_records', 0)}")
            print()


if __name__ == "__main__":
    view_latest_collection()
