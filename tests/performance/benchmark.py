#!/usr/bin/env python3
"""
性能基准测试和压力测试
测试API响应时间、缓存命中率、并发处理能力
"""

import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

API_BASE = "http://localhost:18000/api"


def benchmark_endpoint(endpoint, iterations=10):
    """测试单个端点的性能"""
    response_times = []
    errors = 0
    
    for i in range(iterations):
        try:
            start = time.time()
            resp = requests.get(f"{API_BASE}{endpoint}", timeout=10)
            elapsed = (time.time() - start) * 1000  # 毫秒
            
            if resp.status_code == 200:
                response_times.append(elapsed)
            else:
                errors += 1
        except Exception as e:
            errors += 1
    
    if response_times:
        return {
            'endpoint': endpoint,
            'iterations': iterations,
            'errors': errors,
            'min': min(response_times),
            'max': max(response_times),
            'mean': statistics.mean(response_times),
            'median': statistics.median(response_times),
            'stdev': statistics.stdev(response_times) if len(response_times) > 1 else 0
        }
    else:
        return None


def test_api_performance():
    """测试API响应时间"""
    print("\n🧪 测试1: API响应时间")
    print(f"  目标: <200ms")
    print()
    
    endpoints = [
        "/health",
        "/collectors",
        "/data/raw?limit=10",
        "/data/standard?limit=10",
        "/data/indicators",
        "/quality/summary",
        "/quality/grades",
        "/cache/stats"
    ]
    
    results = []
    
    for endpoint in endpoints:
        print(f"  测试 {endpoint:35s} ", end="", flush=True)
        result = benchmark_endpoint(endpoint, iterations=10)
        
        if result:
            mean_time = result['mean']
            status = "✅" if mean_time < 200 else "⚠️ " if mean_time < 500 else "❌"
            print(f"{status} {mean_time:6.1f}ms (中位: {result['median']:6.1f}ms)")
            results.append(result)
        else:
            print(f"❌ 失败")
    
    # 输出统计
    if results:
        print()
        print(f"  性能汇总:")
        fast = sum(1 for r in results if r['mean'] < 200)
        medium = sum(1 for r in results if 200 <= r['mean'] < 500)
        slow = sum(1 for r in results if r['mean'] >= 500)
        
        print(f"    快速 (<200ms): {fast}")
        print(f"    中等 (200-500ms): {medium}")
        print(f"    慢速 (>500ms): {slow}")
        
        success = fast >= len(results) * 0.8
        print(f"  {'✅' if success else '⚠️ '} 目标达成率: {fast/len(results)*100:.1f}%")
        return success
    
    return False


def test_cache_hit_rate():
    """测试缓存命中率"""
    print("\n🧪 测试2: 缓存命中率")
    print(f"  目标: >80%")
    
    try:
        # 清除缓存
        requests.post(f"{API_BASE}/cache/clear", timeout=5)
        time.sleep(1)
        
        # 第一次请求（缓存未命中）
        endpoint = "/data/indicators"
        for _ in range(5):
            requests.get(f"{API_BASE}{endpoint}", timeout=5)
        
        # 第二次请求（应该命中缓存）
        for _ in range(20):
            requests.get(f"{API_BASE}{endpoint}", timeout=5)
        
        # 查询缓存统计
        resp = requests.get(f"{API_BASE}/cache/stats", timeout=5)
        if resp.status_code == 200:
            stats = resp.json()
            hit_rate = stats.get('hit_rate', 0)
            print(f"  - 缓存命中率: {hit_rate:.2%}")
            
            success = hit_rate >= 0.8
            print(f"  {'✅' if success else '⚠️ '} 缓存命中率{'达标' if success else '未达标'}")
            return success
        else:
            print(f"  ⚠️  无法获取缓存统计")
            return False
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


def test_concurrent_requests(num_users=50, requests_per_user=5):
    """测试并发处理能力"""
    print(f"\n🧪 测试3: 并发处理能力")
    print(f"  并发用户: {num_users}")
    print(f"  每用户请求: {requests_per_user}")
    
    endpoints = [
        "/health",
        "/data/raw?limit=10",
        "/quality/summary"
    ]
    
    def make_request(user_id):
        """单个用户的请求序列"""
        results = []
        for i in range(requests_per_user):
            endpoint = endpoints[i % len(endpoints)]
            try:
                start = time.time()
                resp = requests.get(f"{API_BASE}{endpoint}", timeout=10)
                elapsed = time.time() - start
                
                results.append({
                    'success': resp.status_code == 200,
                    'time': elapsed
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'time': 0
                })
        return results
    
    # 并发执行
    start_time = time.time()
    all_results = []
    
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_users)]
        
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                pass
    
    total_time = time.time() - start_time
    
    # 统计结果
    total_requests = len(all_results)
    successful = sum(1 for r in all_results if r['success'])
    failed = total_requests - successful
    
    response_times = [r['time'] * 1000 for r in all_results if r['success']]
    
    print(f"\n  执行结果:")
    print(f"    总请求数: {total_requests}")
    print(f"    成功: {successful} ({successful/total_requests*100:.1f}%)")
    print(f"    失败: {failed}")
    print(f"    总耗时: {total_time:.2f}秒")
    print(f"    QPS: {total_requests/total_time:.1f} req/s")
    
    if response_times:
        print(f"\n  响应时间:")
        print(f"    平均: {statistics.mean(response_times):.1f}ms")
        print(f"    中位: {statistics.median(response_times):.1f}ms")
        print(f"    最大: {max(response_times):.1f}ms")
    
    success = successful / total_requests >= 0.95  # 95%成功率
    print(f"\n  {'✅' if success else '⚠️ '} 并发测试{'通过' if success else '未通过'}")
    
    return success


def test_database_query_performance():
    """测试数据库查询性能"""
    print(f"\n🧪 测试4: 数据库查询性能")
    
    import psycopg2
    
    DB_CONFIG = {
        'host': 'localhost',
        'port': 15432,
        'database': 'corn_research',
        'user': 'corn_user',
        'password': 'corn_pass_2024'
    }
    
    queries = [
        ("简单查询", "SELECT COUNT(*) FROM raw_collection_records"),
        ("分页查询", "SELECT * FROM raw_collection_records ORDER BY collected_at DESC LIMIT 10"),
        ("聚合查询", "SELECT collector_id, COUNT(*) FROM raw_collection_records GROUP BY collector_id"),
        ("关联查询", """
            SELECT s.*, r.source_url 
            FROM market_facts_standard s 
            LEFT JOIN raw_collection_records r ON s.raw_record_id = r.id 
            LIMIT 10
        """)
    ]
    
    results = []
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for name, query in queries:
            times = []
            for _ in range(5):
                start = time.time()
                cur.execute(query)
                cur.fetchall()
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            
            avg_time = statistics.mean(times)
            status = "✅" if avg_time < 100 else "⚠️ "
            print(f"  {status} {name:15s} {avg_time:6.1f}ms")
            results.append(avg_time < 100)
        
        cur.close()
        conn.close()
        
        success = sum(results) >= len(results) * 0.75
        print(f"\n  {'✅' if success else '⚠️ '} 数据库性能{'正常' if success else '需优化'}")
        return success
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


def test_long_running_stability(duration_seconds=60):
    """测试长时间运行稳定性"""
    print(f"\n🧪 测试5: 长时间稳定性")
    print(f"  持续时间: {duration_seconds}秒")
    
    start_time = time.time()
    request_count = 0
    error_count = 0
    
    endpoint = "/health"
    
    print(f"  开始测试...", end="", flush=True)
    
    while time.time() - start_time < duration_seconds:
        try:
            resp = requests.get(f"{API_BASE}{endpoint}", timeout=5)
            if resp.status_code == 200:
                request_count += 1
            else:
                error_count += 1
        except:
            error_count += 1
        
        time.sleep(0.5)  # 每0.5秒一次请求
    
    total_time = time.time() - start_time
    total_requests = request_count + error_count
    
    print(f" 完成")
    print(f"\n  结果:")
    print(f"    总请求: {total_requests}")
    print(f"    成功: {request_count}")
    print(f"    失败: {error_count}")
    print(f"    成功率: {request_count/total_requests*100:.1f}%")
    print(f"    平均QPS: {total_requests/total_time:.1f}")
    
    success = error_count == 0
    print(f"\n  {'✅' if success else '⚠️ '} 稳定性{'正常' if success else '存在问题'}")
    
    return success


def main():
    """运行所有性能测试"""
    print("=" * 60)
    print("🌽 性能基准测试和压力测试")
    print("=" * 60)
    print(f"API Base: {API_BASE}")
    
    # 检查服务是否运行
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code != 200:
            print("\n⚠️  后端服务未正常运行")
            return False
    except:
        print("\n⚠️  无法连接到后端服务")
        print("   请先运行: cd backend-rust && cargo run --release")
        return False
    
    results = []
    
    # 执行测试
    tests = [
        ("API响应时间", test_api_performance),
        ("缓存命中率", test_cache_hit_rate),
        ("并发处理", lambda: test_concurrent_requests(50, 5)),
        ("数据库性能", test_database_query_performance),
        ("稳定性测试", lambda: test_long_running_stability(30))  # 30秒快速测试
    ]
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n  ❌ {name}测试失败: {e}")
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
    
    # 性能评级
    if passed_count == total_count:
        grade = "A - 优秀"
    elif passed_count >= total_count * 0.8:
        grade = "B - 良好"
    elif passed_count >= total_count * 0.6:
        grade = "C - 及格"
    else:
        grade = "D - 需改进"
    
    print(f"\n性能评级: {grade}")
    
    return passed_count >= total_count * 0.8


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
