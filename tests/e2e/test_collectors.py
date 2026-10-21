#!/usr/bin/env python3
"""
采集器端到端测试
测试博亚和新浪采集器的完整流程
"""

import sys
import os
import asyncio
import redis
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../collectors-python'))

from collectors.boyar_production import BoyarProductionCollector
from collectors.sina_production import SinaProductionCollector


def test_boyar_collector():
    """测试博亚采集器完整流程"""
    print("\n🧪 测试1: 博亚采集器")
    
    # 连接Redis
    redis_client = redis.Redis(host='localhost', port=16380, db=0, decode_responses=True)
    
    # 清除测试游标
    test_collector_id = "boyar_test"
    redis_client.delete(f"collector:cursor:{test_collector_id}")
    
    collector = BoyarProductionCollector(
        collector_id=test_collector_id,
        redis_client=redis_client
    )
    
    print(f"  - 采集器ID: {test_collector_id}")
    print(f"  - 限速: {collector.rate_limit_seconds}秒/请求")
    print(f"  - 重试次数: {collector.max_retries}")
    
    # 测试采集（限制5条）
    results = asyncio.run(collector.collect(max_items=5))
    
    print(f"  ✅ 采集成功: {len(results)} 条记录")
    
    if results:
        sample = results[0]
        print(f"  - 样本标题: {sample.get('title', 'N/A')[:50]}...")
        print(f"  - HTML存档: {sample.get('metadata', {}).get('html_path', 'N/A')}")
    
    # 测试增量采集（游标管理）
    cursor = redis_client.get(f"collector:cursor:{test_collector_id}")
    print(f"  ✅ 游标已保存: {cursor}")
    
    # 测试断点续传
    results2 = asyncio.run(collector.collect(max_items=3))
    print(f"  ✅ 增量采集: {len(results2)} 条记录")
    
    return len(results) > 0


def test_sina_collector():
    """测试新浪采集器完整流程"""
    print("\n🧪 测试2: 新浪采集器")
    
    redis_client = redis.Redis(host='localhost', port=16380, db=0, decode_responses=True)
    
    test_collector_id = "sina_test"
    redis_client.delete(f"collector:cursor:{test_collector_id}")
    
    collector = SinaProductionCollector(
        collector_id=test_collector_id,
        redis_client=redis_client
    )
    
    print(f"  - 采集器ID: {test_collector_id}")
    print(f"  - 数据源策略: 东方财富 -> Mysteel -> Mock")
    
    # 测试采集
    results = asyncio.run(collector.collect(max_items=3))
    
    print(f"  ✅ 采集成功: {len(results)} 条记录")
    
    # 检查Mock标记
    mock_count = sum(1 for r in results if r.get('metadata', {}).get('is_mock'))
    print(f"  - Mock数据: {mock_count}/{len(results)} 条")
    
    if results:
        sample = results[0]
        print(f"  - 样本指标: {sample.get('indicator', 'N/A')}")
        print(f"  - 样本值: {sample.get('value', 'N/A')} {sample.get('unit', '')}")
    
    return len(results) > 0


def test_html_archive():
    """测试HTML存档功能"""
    print("\n🧪 测试3: HTML存档")
    
    data_dir = "data/raw/html"
    if not os.path.exists(data_dir):
        print(f"  ⚠️  存档目录不存在: {data_dir}")
        return False
    
    # 查找最近的HTML文件
    import glob
    html_files = glob.glob(f"{data_dir}/boyar/**/*.html.gz", recursive=True)
    
    print(f"  ✅ 找到 {len(html_files)} 个HTML存档文件")
    
    if html_files:
        import gzip
        sample_file = html_files[0]
        with gzip.open(sample_file, 'rt', encoding='utf-8') as f:
            content = f.read()
        print(f"  - 样本文件: {os.path.basename(sample_file)}")
        print(f"  - 文件大小: {os.path.getsize(sample_file)} 字节（压缩后）")
        print(f"  - 内容大小: {len(content)} 字符（解压后）")
    
    return len(html_files) > 0


def test_rate_limiting():
    """测试限速机制"""
    print("\n🧪 测试4: 限速机制")
    
    redis_client = redis.Redis(host='localhost', port=16380, db=0, decode_responses=True)
    collector = BoyarProductionCollector(collector_id="rate_test", redis_client=redis_client)
    
    import time
    start = time.time()
    
    # 采集2条数据，应该有1.5秒间隔
    asyncio.run(collector.collect(max_items=2))
    
    elapsed = time.time() - start
    print(f"  - 采集2条耗时: {elapsed:.2f}秒")
    
    if elapsed >= 1.5:
        print(f"  ✅ 限速机制正常（>1.5秒）")
        return True
    else:
        print(f"  ⚠️  限速可能未生效（<1.5秒）")
        return False


def main():
    """运行所有采集器测试"""
    print("=" * 60)
    print("🌽 采集器端到端测试")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("博亚采集器", test_boyar_collector()))
    except Exception as e:
        print(f"  ❌ 博亚采集器测试失败: {e}")
        results.append(("博亚采集器", False))
    
    try:
        results.append(("新浪采集器", test_sina_collector()))
    except Exception as e:
        print(f"  ❌ 新浪采集器测试失败: {e}")
        results.append(("新浪采集器", False))
    
    try:
        results.append(("HTML存档", test_html_archive()))
    except Exception as e:
        print(f"  ❌ HTML存档测试失败: {e}")
        results.append(("HTML存档", False))
    
    try:
        results.append(("限速机制", test_rate_limiting()))
    except Exception as e:
        print(f"  ❌ 限速机制测试失败: {e}")
        results.append(("限速机制", False))
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20s} {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\n总计: {passed_count}/{total_count} 通过 ({passed_count/total_count*100:.1f}%)")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
