#!/usr/bin/env python3
"""
玉米研究系统V2 - 控制台MVP

快速启动:
    python cli.py

功能:
    - 查看采集器状态
    - 运行数据采集
    - 查看最新数据
    - 查看系统统计
"""

import sys
import os
from datetime import datetime
from collections import defaultdict

# 添加collectors路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'collectors-python'))

try:
    from collectors.boyar import BoyarCollector
    from collectors.sina import SinaCollector
    RUST_AVAILABLE = False
    try:
        import corn_rs
        RUST_AVAILABLE = True
    except ImportError:
        pass
except ImportError as e:
    print(f"❌ 无法导入采集器: {e}")
    sys.exit(1)


class CornCLI:
    """玉米研究系统控制台"""
    
    def __init__(self):
        self.collectors = {
            'boyar': BoyarCollector(),
            'sina': SinaCollector(),
        }
        self.data_store = defaultdict(list)
    
    def show_banner(self):
        """显示欢迎横幅"""
        print("=" * 60)
        print("🌽 玉米研究系统 V2 - 控制台MVP")
        print("=" * 60)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Rust服务: {'✅ 可用' if RUST_AVAILABLE else '❌ 不可用'}")
        print(f"采集器数量: {len(self.collectors)}")
        print("=" * 60)
        print()
    
    def show_menu(self):
        """显示主菜单"""
        print("\n📋 主菜单")
        print("-" * 60)
        print("1. 查看采集器状态")
        print("2. 运行数据采集 (博亚和讯)")
        print("3. 运行数据采集 (新浪财经)")
        print("4. 查看最新数据")
        print("5. 系统统计")
        if RUST_AVAILABLE:
            print("6. 测试Rust服务")
        print("0. 退出")
        print("-" * 60)
    
    def show_collectors_status(self):
        """显示采集器状态"""
        print("\n📊 采集器状态")
        print("-" * 60)
        for name, collector in self.collectors.items():
            print(f"✅ {name.upper()}")
            print(f"   站点: {collector.site_name}")
            print(f"   URL: {collector.site_url}")
            print(f"   类型: {collector.source_type}")
            print()
    
    def run_boyar_collector(self):
        """运行博亚和讯采集"""
        print("\n🚀 开始采集 - 博亚和讯")
        print("-" * 60)
        
        collector = self.collectors['boyar']
        
        # 采集最近10篇文章
        print("采集范围: 最近10篇文章")
        print("正在采集...")
        
        try:
            records = collector.collect(start_id=1267650, end_id=1267660)
            
            print(f"\n✅ 采集完成！")
            print(f"   采集到 {len(records)} 条记录")
            
            # 存储数据
            self.data_store['boyar'].extend(records)
            
            # 显示前3条
            if records:
                print("\n📝 前3条数据预览:")
                for i, record in enumerate(records[:3], 1):
                    print(f"\n{i}. {record.business_date} - {record.indicator}")
                    print(f"   数值: {record.value} {record.unit}")
                    print(f"   地区: {record.region}")
                    print(f"   来源: {record.source_url}")
            
            return len(records)
        except Exception as e:
            print(f"❌ 采集失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def run_sina_collector(self):
        """运行新浪财经采集"""
        print("\n🚀 开始采集 - 新浪财经")
        print("-" * 60)
        print("⚠️  新浪采集器尚未实现")
        print("   预计功能: 北港库存、下海量数据")
        return 0
    
    def show_latest_data(self):
        """显示最新数据"""
        print("\n📈 最新数据")
        print("-" * 60)
        
        total = sum(len(records) for records in self.data_store.values())
        
        if total == 0:
            print("⚠️  暂无数据，请先运行数据采集")
            return
        
        print(f"总记录数: {total}")
        print()
        
        for source, records in self.data_store.items():
            if records:
                print(f"📁 {source.upper()} ({len(records)}条)")
                
                # 按指标分组
                by_indicator = defaultdict(list)
                for r in records:
                    by_indicator[r.indicator].append(r)
                
                for indicator, recs in by_indicator.items():
                    latest = max(recs, key=lambda x: x.business_date)
                    print(f"   {indicator}: {latest.value}{latest.unit} ({latest.business_date})")
                print()
    
    def show_statistics(self):
        """显示系统统计"""
        print("\n📊 系统统计")
        print("-" * 60)
        
        total_records = sum(len(records) for records in self.data_store.values())
        
        print(f"总记录数: {total_records}")
        print(f"采集器数量: {len(self.collectors)}")
        print(f"数据源数量: {len(self.data_store)}")
        
        if RUST_AVAILABLE:
            print(f"Rust服务: ✅ 已启用")
        else:
            print(f"Rust服务: ❌ 未安装")
        
        print()
        
        # 按采集器统计
        print("按来源统计:")
        for source, records in self.data_store.items():
            print(f"  {source}: {len(records)}条")
    
    def test_rust_service(self):
        """测试Rust服务"""
        if not RUST_AVAILABLE:
            print("\n❌ Rust服务不可用")
            print("请先编译corn_rs模块:")
            print("  cd core-rust/corn-python")
            print("  maturin develop --release")
            return
        
        print("\n🦀 测试Rust服务")
        print("-" * 60)
        
        # 测试质量分数计算
        try:
            score = corn_rs.calculate_quality_score(0.9, 1.0, 0.95)
            print(f"✅ 质量分数计算: {score:.3f}")
        except Exception as e:
            print(f"❌ 质量分数计算失败: {e}")
        
        # 测试数据处理
        try:
            test_data = [
                {'value': 1040.0, 'indicator': '测试指标'},
            ]
            result = corn_rs.process_raw_data(test_data)
            print(f"✅ 数据处理: 处理了{result.processed_count}条")
        except Exception as e:
            print(f"❌ 数据处理失败: {e}")
    
    def run(self):
        """运行控制台"""
        self.show_banner()
        
        while True:
            self.show_menu()
            
            try:
                choice = input("\n请选择操作 (0-6): ").strip()
                
                if choice == '0':
                    print("\n👋 再见！")
                    break
                elif choice == '1':
                    self.show_collectors_status()
                elif choice == '2':
                    self.run_boyar_collector()
                elif choice == '3':
                    self.run_sina_collector()
                elif choice == '4':
                    self.show_latest_data()
                elif choice == '5':
                    self.show_statistics()
                elif choice == '6' and RUST_AVAILABLE:
                    self.test_rust_service()
                else:
                    print("\n❌ 无效选择，请重试")
            
            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                import traceback
                traceback.print_exc()


if __name__ == '__main__':
    cli = CornCLI()
    cli.run()
