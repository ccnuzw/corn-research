"""
测试Python调用Rust DDD核心
"""
try:
    import corn_rs
    print("✅ corn_rs模块加载成功")
    
    # 测试质量分数计算
    score = corn_rs.calculate_quality_score(0.9, 1.0, 0.95)
    print(f"✅ 质量分数计算: {score}")
    
    # 测试数据处理
    raw_data = [
        {'value': 1040.0, 'indicator': '山东深加工到车量'},
        {'value': 2850.0, 'indicator': '山东现货价格'},
    ]
    
    result = corn_rs.process_raw_data(raw_data)
    print(f"✅ 数据处理: success={result.success}, count={result.processed_count}")
    
except ImportError as e:
    print(f"❌ corn_rs模块未安装: {e}")
    print("提示: cd core-rust/corn-python && maturin develop --release")
