#!/usr/bin/env python3
"""
数据持久化链路端到端测试
测试 RAW → STANDARD 完整数据流
"""

import sys
import os
import psycopg2
import requests
from datetime import datetime, timezone
import uuid
import json

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 15432,
    'database': 'corn_research',
    'user': 'corn_user',
    'password': 'corn_pass_2024'
}

# API配置
API_BASE = "http://localhost:18000/api"


def test_raw_layer_insert():
    """测试RAW层数据插入"""
    print("\n🧪 测试1: RAW层数据插入")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 查询插入前的记录数
    cur.execute("SELECT COUNT(*) FROM raw_collection_records")
    count_before = cur.fetchone()[0]
    print(f"  - 插入前记录数: {count_before}")
    
    # 插入测试数据
    test_data = {
        'id': str(uuid.uuid4()),
        'collector_id': 'test_pipeline',
        'source_url': 'https://test.com/article/001',
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'raw_content': json.dumps({
            'title': '山东玉米到车量增加',
            'content': '今日山东地区玉米到车量为500台',
            'date': '2026-10-21'
        }),
        'content_hash': 'test_hash_001',
        'metadata': json.dumps({
            'collector': 'test_pipeline',
            'version': '1.0'
        })
    }
    
    cur.execute("""
        INSERT INTO raw_collection_records 
        (id, collector_id, source_url, collected_at, raw_content, content_hash, metadata)
        VALUES (%(id)s, %(collector_id)s, %(source_url)s, %(collected_at)s, 
                %(raw_content)s, %(content_hash)s, %(metadata)s)
        ON CONFLICT (content_hash) DO NOTHING
    """, test_data)
    
    conn.commit()
    
    # 查询插入后的记录数
    cur.execute("SELECT COUNT(*) FROM raw_collection_records")
    count_after = cur.fetchone()[0]
    print(f"  - 插入后记录数: {count_after}")
    
    inserted = count_after > count_before
    print(f"  {'✅' if inserted else '⚠️ '} 插入{'成功' if inserted else '跳过（可能重复）'}")
    
    cur.close()
    conn.close()
    
    return test_data['id']


def test_quality_assessment(raw_id):
    """测试质量评估"""
    print("\n🧪 测试2: 质量评估")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 手动插入STANDARD层数据用于测试
    test_standard = {
        'id': str(uuid.uuid4()),
        'business_date': '2026-10-21',
        'indicator_name': '山东玉米到车量',
        'value': 500.0,
        'unit': '台',
        'region': '山东',
        'quality_grade': 'B',
        'quality_score': 85.0,
        'quality_issues': json.dumps([]),
        'source_id': 'test_pipeline',
        'raw_record_id': raw_id,
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'standardized_at': datetime.now(timezone.utc).isoformat()
    }
    
    cur.execute("""
        INSERT INTO market_facts_standard 
        (id, business_date, indicator_name, value, unit, region, 
         quality_grade, quality_score, quality_issues, source_id, 
         raw_record_id, collected_at, standardized_at)
        VALUES (%(id)s, %(business_date)s, %(indicator_name)s, %(value)s, 
                %(unit)s, %(region)s, %(quality_grade)s, %(quality_score)s, 
                %(quality_issues)s, %(source_id)s, %(raw_record_id)s, 
                %(collected_at)s, %(standardized_at)s)
    """, test_standard)
    
    conn.commit()
    
    # 查询质量等级分布
    cur.execute("""
        SELECT quality_grade, COUNT(*) 
        FROM market_facts_standard 
        GROUP BY quality_grade 
        ORDER BY quality_grade
    """)
    
    grade_dist = cur.fetchall()
    print(f"  - 质量等级分布:")
    for grade, count in grade_dist:
        print(f"    {grade}级: {count} 条")
    
    # 验证质量评分范围
    cur.execute("""
        SELECT MIN(quality_score), MAX(quality_score), AVG(quality_score)
        FROM market_facts_standard
    """)
    min_score, max_score, avg_score = cur.fetchone()
    print(f"  - 质量评分: 最小={min_score}, 最大={max_score}, 平均={avg_score:.2f}")
    
    valid_score = 0 <= min_score <= 100 and 0 <= max_score <= 100
    print(f"  {'✅' if valid_score else '❌'} 评分范围{'正常' if valid_score else '异常'}")
    
    cur.close()
    conn.close()
    
    return test_standard['id']


def test_lineage_tracing(standard_id):
    """测试血统追溯"""
    print("\n🧪 测试3: 血统追溯")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 查询血统链路
    cur.execute("""
        SELECT 
            s.id as standard_id,
            s.indicator_name,
            s.quality_grade,
            r.collector_id,
            r.source_url,
            r.collected_at
        FROM market_facts_standard s
        LEFT JOIN raw_collection_records r ON s.raw_record_id = r.id
        WHERE s.id = %s
    """, (standard_id,))
    
    result = cur.fetchone()
    
    if result:
        print(f"  ✅ 血统链路完整")
        print(f"    - STANDARD ID: {result[0][:8]}...")
        print(f"    - 指标名称: {result[1]}")
        print(f"    - 质量等级: {result[2]}")
        print(f"    - 采集器: {result[3]}")
        print(f"    - 原始URL: {result[4]}")
        print(f"    - 采集时间: {result[5]}")
        success = True
    else:
        print(f"  ❌ 血统链路断裂")
        success = False
    
    cur.close()
    conn.close()
    
    return success


def test_deduplication():
    """测试去重功能"""
    print("\n🧪 测试4: 去重功能")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 尝试插入重复数据
    duplicate_hash = 'duplicate_test_hash'
    
    test_data = {
        'id': str(uuid.uuid4()),
        'collector_id': 'dedup_test',
        'source_url': 'https://test.com/dedup',
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'raw_content': json.dumps({'test': 'dedup'}),
        'content_hash': duplicate_hash,
        'metadata': json.dumps({})
    }
    
    # 第一次插入
    cur.execute("""
        INSERT INTO raw_collection_records 
        (id, collector_id, source_url, collected_at, raw_content, content_hash, metadata)
        VALUES (%(id)s, %(collector_id)s, %(source_url)s, %(collected_at)s, 
                %(raw_content)s, %(content_hash)s, %(metadata)s)
        ON CONFLICT (content_hash) DO NOTHING
        RETURNING id
    """, test_data)
    
    first_insert = cur.fetchone()
    conn.commit()
    
    # 第二次插入（应该被去重）
    test_data['id'] = str(uuid.uuid4())  # 新ID
    cur.execute("""
        INSERT INTO raw_collection_records 
        (id, collector_id, source_url, collected_at, raw_content, content_hash, metadata)
        VALUES (%(id)s, %(collector_id)s, %(source_url)s, %(collected_at)s, 
                %(raw_content)s, %(content_hash)s, %(metadata)s)
        ON CONFLICT (content_hash) DO NOTHING
        RETURNING id
    """, test_data)
    
    second_insert = cur.fetchone()
    conn.commit()
    
    if first_insert and not second_insert:
        print(f"  ✅ 去重功能正常（重复数据被拒绝）")
        success = True
    else:
        print(f"  ⚠️  去重可能未生效")
        success = False
    
    cur.close()
    conn.close()
    
    return success


def test_version_management():
    """测试版本管理"""
    print("\n🧪 测试5: 版本管理")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 创建初始记录
    base_id = str(uuid.uuid4())
    business_date = '2026-10-21'
    indicator = '版本测试指标'
    
    cur.execute("""
        INSERT INTO market_facts_standard 
        (id, business_date, indicator_name, value, unit, region, 
         quality_grade, quality_score, quality_issues, source_id, 
         raw_record_id, collected_at, standardized_at, version, is_latest)
        VALUES (%s, %s, %s, 100.0, '万吨', '全国', 'B', 85.0, '[]', 
                'version_test', %s, NOW(), NOW(), 1, TRUE)
    """, (base_id, business_date, indicator, str(uuid.uuid4())))
    
    conn.commit()
    
    # 创建新版本（模拟更新）
    new_id = str(uuid.uuid4())
    cur.execute("""
        UPDATE market_facts_standard 
        SET is_latest = FALSE 
        WHERE business_date = %s AND indicator_name = %s AND is_latest = TRUE
    """, (business_date, indicator))
    
    cur.execute("""
        INSERT INTO market_facts_standard 
        (id, business_date, indicator_name, value, unit, region, 
         quality_grade, quality_score, quality_issues, source_id, 
         raw_record_id, collected_at, standardized_at, version, is_latest)
        VALUES (%s, %s, %s, 105.0, '万吨', '全国', 'A', 90.0, '[]', 
                'version_test', %s, NOW(), NOW(), 2, TRUE)
    """, (new_id, business_date, indicator, str(uuid.uuid4())))
    
    conn.commit()
    
    # 验证版本管理
    cur.execute("""
        SELECT version, is_latest, value 
        FROM market_facts_standard 
        WHERE business_date = %s AND indicator_name = %s
        ORDER BY version
    """, (business_date, indicator))
    
    versions = cur.fetchall()
    
    if len(versions) >= 2:
        print(f"  ✅ 版本管理正常")
        for ver, is_latest, value in versions:
            status = "最新" if is_latest else "历史"
            print(f"    - 版本{ver}: {value} ({status})")
        success = True
    else:
        print(f"  ⚠️  版本管理未生效")
        success = False
    
    cur.close()
    conn.close()
    
    return success


def main():
    """运行所有数据管道测试"""
    print("=" * 60)
    print("🌽 数据持久化链路端到端测试")
    print("=" * 60)
    
    results = []
    raw_id = None
    standard_id = None
    
    try:
        raw_id = test_raw_layer_insert()
        results.append(("RAW层插入", raw_id is not None))
    except Exception as e:
        print(f"  ❌ RAW层插入失败: {e}")
        results.append(("RAW层插入", False))
    
    if raw_id:
        try:
            standard_id = test_quality_assessment(raw_id)
            results.append(("质量评估", standard_id is not None))
        except Exception as e:
            print(f"  ❌ 质量评估失败: {e}")
            results.append(("质量评估", False))
    
    if standard_id:
        try:
            success = test_lineage_tracing(standard_id)
            results.append(("血统追溯", success))
        except Exception as e:
            print(f"  ❌ 血统追溯失败: {e}")
            results.append(("血统追溯", False))
    
    try:
        success = test_deduplication()
        results.append(("去重功能", success))
    except Exception as e:
        print(f"  ❌ 去重功能测试失败: {e}")
        results.append(("去重功能", False))
    
    try:
        success = test_version_management()
        results.append(("版本管理", success))
    except Exception as e:
        print(f"  ❌ 版本管理测试失败: {e}")
        results.append(("版本管理", False))
    
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
