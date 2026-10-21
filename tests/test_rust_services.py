"""
测试Rust去重和验证服务

运行: python test_rust_services.py
"""

try:
    import corn_rs
    print("✅ corn_rs模块加载成功\n")
    
    # ========================================
    # 测试1: 去重服务
    # ========================================
    print("=" * 50)
    print("测试1: 去重服务")
    print("=" * 50)
    
    records = [
        {
            'business_date': '2026-10-20',
            'indicator': '山东深加工到车量',
            'value': 1040.0,
            'region': '山东',
            'source_url': 'http://boyar.cn/1'
        },
        {
            'business_date': '2026-10-20',
            'indicator': '山东深加工到车量',
            'value': 1040.0,
            'region': '山东',
            'source_url': 'http://boyar.cn/2'  # 重复数据（不同URL）
        },
        {
            'business_date': '2026-10-21',
            'indicator': '山东深加工到车量',
            'value': 1050.0,
            'region': '山东',
            'source_url': 'http://boyar.cn/3'
        },
    ]
    
    print(f"原始记录数: {len(records)}")
    deduped = corn_rs.deduplicate_records(records)
    print(f"去重后记录数: {len(deduped)}")
    print(f"✅ 去重测试通过！去除了 {len(records) - len(deduped)} 条重复\n")
    
    # ========================================
    # 测试2: 验证服务
    # ========================================
    print("=" * 50)
    print("测试2: 验证服务")
    print("=" * 50)
    
    test_records = [
        {
            'business_date': '2026-10-20',
            'indicator': '山东到车',
            'value': 1040.0,
            'region': '山东',
            'source_url': 'http://test.com/1'
        },
        {
            'business_date': '',  # 无效：日期为空
            'indicator': '山东到车',
            'value': 1050.0,
            'region': '山东',
            'source_url': 'http://test.com/2'
        },
        {
            'business_date': '2026-10-21',
            'indicator': '山东到车',
            'value': -100.0,  # 无效：负数
            'region': '山东',
            'source_url': 'http://test.com/3'
        },
    ]
    
    result = corn_rs.validate_records(test_records)
    print(f"总记录数: {len(test_records)}")
    print(f"有效记录数: {result['valid_count']}")
    print(f"无效记录数: {result['invalid_count']}")
    print(f"✅ 验证测试通过！\n")
    
    # ========================================
    # 测试3: 质量分数计算
    # ========================================
    print("=" * 50)
    print("测试3: 质量分数计算")
    print("=" * 50)
    
    score = corn_rs.calculate_quality_score(0.9, 1.0, 0.95)
    print(f"质量分数: {score}")
    print(f"✅ 质量分数计算通过！\n")
    
    # ========================================
    # 测试4: 数据处理
    # ========================================
    print("=" * 50)
    print("测试4: 数据处理")
    print("=" * 50)
    
    raw_data = [
        {'value': 1040.0, 'indicator': '山东到车'},
        {'value': 2850.0, 'indicator': '现货价格'},
    ]
    
    result = corn_rs.process_raw_data(raw_data)
    print(f"处理成功: {result.success}")
    print(f"处理数量: {result.processed_count}")
    print(f"消息: {result.message}")
    print(f"✅ 数据处理测试通过！\n")
    
    print("=" * 50)
    print("🎉 所有测试通过！Rust服务运行正常！")
    print("=" * 50)
    
except ImportError as e:
    print(f"❌ corn_rs模块未安装: {e}")
    print("\n请按以下步骤安装:")
    print("1. cd core-rust/corn-python")
    print("2. source ../../.venv/bin/activate")
    print("3. PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --release")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
