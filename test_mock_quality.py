#!/usr/bin/env python3
"""
测试Mock数据质量标记
验证Mock数据被正确标记为'M'等级
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-rust'))

import asyncio
import asyncpg
from datetime import datetime

async def test_mock_quality():
    """测试Mock数据质量评估"""
    
    # 连接数据库
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        user='corn_user',
        password='corn_pass',
        database='corn_research'
    )
    
    try:
        print("🧪 测试Mock数据质量标记")
        print("=" * 60)
        
        # 1. 查询Mock数据
        mock_records = await conn.fetch("""
            SELECT id, indicator_name, source_url, original_text, collector_id
            FROM raw_collection_records
            WHERE source_url LIKE '%mock.data%'
            ORDER BY created_at DESC
        """)
        
        print(f"\n📋 找到 {len(mock_records)} 条Mock记录:")
        for record in mock_records:
            print(f"  - {record['indicator_name']}")
            print(f"    source_url: {record['source_url']}")
            print(f"    collector: {record['collector_id']}")
            print()
        
        # 2. 检查STANDARD层数据
        standard_records = await conn.fetch("""
            SELECT s.id, s.indicator_name, s.quality_grade, s.quality_score, 
                   r.source_url
            FROM market_facts_standard s
            LEFT JOIN raw_collection_records r ON s.raw_record_id = r.id
            ORDER BY s.created_at DESC
        """)
        
        print(f"\n📊 STANDARD层记录: {len(standard_records)} 条")
        if standard_records:
            for record in standard_records:
                is_mock = 'mock.data' in (record['source_url'] or '')
                status = "✅" if (is_mock and record['quality_grade'] == 'M') else "❌"
                print(f"{status} {record['indicator_name']}: 质量={record['quality_grade']}, "
                      f"分数={record['quality_score']}, Mock={is_mock}")
        else:
            print("  (无数据 - 需要运行标准化)")
        
        # 3. 检查质量约束
        constraint_info = await conn.fetchrow("""
            SELECT check_clause 
            FROM information_schema.check_constraints 
            WHERE constraint_name = 'market_facts_standard_quality_grade_check'
        """)
        
        print(f"\n🔒 数据库约束:")
        print(f"  {constraint_info['check_clause']}")
        has_m = "'M'" in constraint_info['check_clause'] or '"M"' in constraint_info['check_clause']
        print(f"  包含'M'等级: {'✅' if has_m else '❌'}")
        
        # 4. 建议
        print("\n📝 后续步骤:")
        if len(mock_records) > 0 and len(standard_records) == 0:
            print("  1. Mock数据已存在于RAW层")
            print("  2. 需要运行标准化流程将Mock数据转换到STANDARD层")
            print("  3. 验证Mock数据被标记为'M'等级")
            print("\n  运行命令:")
            print("  curl -X POST http://localhost:8000/api/standardization/promote")
        elif len(standard_records) > 0:
            mock_in_standard = sum(1 for r in standard_records if 'mock.data' in (r['source_url'] or ''))
            if mock_in_standard > 0:
                print("  ✅ 检查STANDARD层中Mock数据的质量等级")
            else:
                print("  ℹ️ STANDARD层暂无Mock数据")
        
        print("\n" + "=" * 60)
        return True
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_mock_quality())
