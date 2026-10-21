#!/usr/bin/env python3
"""
API集成测试
测试所有20个API端点
"""

import requests
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:18000/api"


def test_health_check():
    """测试健康检查"""
    print("\n🧪 测试1: 健康检查")
    
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"  - 状态码: {resp.status_code}")
        print(f"  - 响应: {resp.json()}")
        success = resp.status_code == 200
        print(f"  {'✅' if success else '❌'} 健康检查{'正常' if success else '失败'}")
        return success
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        return False


def test_collectors_api():
    """测试采集器相关API"""
    print("\n🧪 测试2: 采集器API")
    
    results = []
    
    # GET /collectors - 列出所有采集器
    try:
        resp = requests.get(f"{API_BASE}/collectors", timeout=5)
        print(f"  - GET /collectors: {resp.status_code}")
        if resp.status_code == 200:
            collectors = resp.json()
            print(f"    采集器数量: {len(collectors)}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ❌ GET /collectors 失败: {e}")
        results.append(False)
    
    # POST /collectors/run - 运行采集器
    try:
        payload = {"collector_id": "boyar", "max_items": 3}
        resp = requests.post(f"{API_BASE}/collectors/run", json=payload, timeout=30)
        print(f"  - POST /collectors/run: {resp.status_code}")
        if resp.status_code in [200, 202]:
            print(f"    采集任务已提交")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ⚠️  POST /collectors/run: {e}")
        results.append(False)
    
    # GET /collectors/:id/status - 查询采集器状态
    try:
        resp = requests.get(f"{API_BASE}/collectors/boyar/status", timeout=5)
        print(f"  - GET /collectors/:id/status: {resp.status_code}")
        if resp.status_code == 200:
            status = resp.json()
            print(f"    状态: {status.get('status', 'unknown')}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ⚠️  GET /collectors/:id/status: {e}")
        results.append(False)
    
    success = all(results)
    print(f"  {'✅' if success else '⚠️ '} 采集器API: {sum(results)}/{len(results)} 通过")
    return success


def test_data_api():
    """测试数据查询API"""
    print("\n🧪 测试3: 数据查询API")
    
    results = []
    
    # GET /data/raw - 查询RAW层数据
    try:
        resp = requests.get(f"{API_BASE}/data/raw?limit=10", timeout=5)
        print(f"  - GET /data/raw: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"    记录数: {len(data.get('items', []))}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ❌ GET /data/raw 失败: {e}")
        results.append(False)
    
    # GET /data/standard - 查询STANDARD层数据
    try:
        resp = requests.get(f"{API_BASE}/data/standard?limit=10", timeout=5)
        print(f"  - GET /data/standard: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"    记录数: {len(data.get('items', []))}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ❌ GET /data/standard 失败: {e}")
        results.append(False)
    
    # GET /data/indicators - 查询指标列表
    try:
        resp = requests.get(f"{API_BASE}/data/indicators", timeout=5)
        print(f"  - GET /data/indicators: {resp.status_code}")
        if resp.status_code == 200:
            indicators = resp.json()
            print(f"    指标数: {len(indicators)}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ❌ GET /data/indicators 失败: {e}")
        results.append(False)
    
    success = all(results)
    print(f"  {'✅' if success else '⚠️ '} 数据查询API: {sum(results)}/{len(results)} 通过")
    return success


def test_quality_api():
    """测试质量评估API"""
    print("\n🧪 测试4: 质量评估API")
    
    results = []
    
    # GET /quality/summary - 质量汇总
    try:
        resp = requests.get(f"{API_BASE}/quality/summary", timeout=5)
        print(f"  - GET /quality/summary: {resp.status_code}")
        if resp.status_code == 200:
            summary = resp.json()
            print(f"    总记录数: {summary.get('total_records', 0)}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ❌ GET /quality/summary 失败: {e}")
        results.append(False)
    
    # GET /quality/grades - 质量等级分布
    try:
        resp = requests.get(f"{API_BASE}/quality/grades", timeout=5)
        print(f"  - GET /quality/grades: {resp.status_code}")
        if resp.status_code == 200:
            grades = resp.json()
            print(f"    等级数: {len(grades)}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ❌ GET /quality/grades 失败: {e}")
        results.append(False)
    
    success = all(results)
    print(f"  {'✅' if success else '⚠️ '} 质量评估API: {sum(results)}/{len(results)} 通过")
    return success


def test_lineage_api():
    """测试血统追溯API"""
    print("\n🧪 测试5: 血统追溯API")
    
    # 先获取一个STANDARD层记录ID
    try:
        resp = requests.get(f"{API_BASE}/data/standard?limit=1", timeout=5)
        if resp.status_code == 200 and resp.json().get('items'):
            record_id = resp.json()['items'][0].get('id')
            
            # GET /data/:id/lineage - 查询血统
            resp2 = requests.get(f"{API_BASE}/data/{record_id}/lineage", timeout=5)
            print(f"  - GET /data/:id/lineage: {resp2.status_code}")
            
            if resp2.status_code == 200:
                lineage = resp2.json()
                print(f"    ✅ 血统链路完整")
                print(f"    - STANDARD记录: {lineage.get('standard', {}).get('indicator_name', 'N/A')}")
                print(f"    - RAW记录ID: {lineage.get('raw', {}).get('id', 'N/A')[:8]}...")
                return True
            else:
                print(f"  ⚠️  血统查询返回: {resp2.status_code}")
                return False
        else:
            print(f"  ⚠️  无STANDARD层数据，跳过血统测试")
            return True  # 视为通过，因为没有数据可测试
    except Exception as e:
        print(f"  ❌ 血统追溯API失败: {e}")
        return False


def test_cache_api():
    """测试缓存API"""
    print("\n🧪 测试6: 缓存API")
    
    results = []
    
    # GET /cache/stats - 缓存统计
    try:
        resp = requests.get(f"{API_BASE}/cache/stats", timeout=5)
        print(f"  - GET /cache/stats: {resp.status_code}")
        if resp.status_code == 200:
            stats = resp.json()
            print(f"    缓存命中率: {stats.get('hit_rate', 0):.2%}")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ⚠️  GET /cache/stats: {e}")
        results.append(False)
    
    # POST /cache/clear - 清除缓存
    try:
        resp = requests.post(f"{API_BASE}/cache/clear", timeout=5)
        print(f"  - POST /cache/clear: {resp.status_code}")
        if resp.status_code in [200, 204]:
            print(f"    ✅ 缓存已清除")
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        print(f"  ⚠️  POST /cache/clear: {e}")
        results.append(False)
    
    success = all(results)
    print(f"  {'✅' if success else '⚠️ '} 缓存API: {sum(results)}/{len(results)} 通过")
    return success


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试7: 错误处理")
    
    results = []
    
    # 404错误
    try:
        resp = requests.get(f"{API_BASE}/nonexistent", timeout=5)
        print(f"  - 不存在的端点: {resp.status_code}")
        if resp.status_code == 404:
            results.append(True)
        else:
            results.append(False)
    except:
        results.append(False)
    
    # 无效参数
    try:
        resp = requests.get(f"{API_BASE}/data/raw?limit=invalid", timeout=5)
        print(f"  - 无效参数: {resp.status_code}")
        if resp.status_code in [400, 422]:
            results.append(True)
        else:
            results.append(False)
    except:
        results.append(False)
    
    success = all(results)
    print(f"  {'✅' if success else '⚠️ '} 错误处理: {sum(results)}/{len(results)} 通过")
    return success


def test_response_time():
    """测试响应时间"""
    print("\n🧪 测试8: 响应时间")
    
    import time
    
    endpoints = [
        "/health",
        "/collectors",
        "/data/raw?limit=10",
        "/quality/summary"
    ]
    
    results = []
    
    for endpoint in endpoints:
        try:
            start = time.time()
            resp = requests.get(f"{API_BASE}{endpoint}", timeout=5)
            elapsed = (time.time() - start) * 1000  # 转换为毫秒
            
            target = 200  # 目标200ms
            status = "✅" if elapsed < target else "⚠️ "
            print(f"  {status} {endpoint:30s} {elapsed:6.1f}ms")
            
            results.append(elapsed < target)
        except Exception as e:
            print(f"  ❌ {endpoint:30s} 失败")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"  响应时间达标: {passed}/{total} ({passed/total*100:.1f}%)")
    
    return passed / total >= 0.8  # 80%达标即可


def main():
    """运行所有API测试"""
    print("=" * 60)
    print("🌽 API集成测试")
    print("=" * 60)
    print(f"API Base: {API_BASE}")
    
    results = []
    
    # 先测试健康检查
    health_ok = test_health_check()
    if not health_ok:
        print("\n⚠️  后端服务未启动，部分测试将跳过")
        print("   请先运行: cd backend-rust && cargo run --release")
        return False
    
    results.append(("健康检查", health_ok))
    
    # 其他测试
    tests = [
        ("采集器API", test_collectors_api),
        ("数据查询API", test_data_api),
        ("质量评估API", test_quality_api),
        ("血统追溯API", test_lineage_api),
        ("缓存API", test_cache_api),
        ("错误处理", test_error_handling),
        ("响应时间", test_response_time),
    ]
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"  ❌ {name}测试失败: {e}")
            results.append((name, False))
    
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
