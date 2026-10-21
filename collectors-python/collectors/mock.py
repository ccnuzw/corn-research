"""
Mock测试采集器 - 用于测试系统功能
生成模拟数据，确保采集流程正常工作
"""
from datetime import datetime, timedelta
import random
from typing import List

from .base import BaseCollector, RawDataRecord


class MockCollector(BaseCollector):
    """Mock采集器 - 生成测试数据"""
    
    @property
    def collector_id(self) -> str:
        return "mock_test"
    
    @property
    def site_name(self) -> str:
        return "Mock测试数据源"
    
    @property
    def site_url(self) -> str:
        return "https://mock.example.com"
    
    @property
    def source_type(self) -> str:
        return "commercial_primary"
    
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        生成模拟采集数据
        """
        print(f"[{self.collector_id}] 生成Mock测试数据...")
        
        records = []
        base_date = datetime.now()
        
        # 生成最近5天的山东到车数据
        for i in range(5):
            date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            value = random.randint(450, 650)  # 450-650台
            
            record = RawDataRecord(
                business_date=date,
                collected_at=datetime.now(),
                published_at=None,
                data_type="arrivals",
                indicator="山东深加工到车量",
                value=float(value),
                unit="台",
                region="山东",
                source_url=self.site_url,
                original_text=f"模拟数据: {date}山东到车{value}台",
                metadata={
                    "is_mock": True,
                    "collector_id": self.collector_id
                }
            )
            records.append(record)
        
        # 生成5个区域的现货报价
        regions = ["山东深加工", "东北产区", "华北黄淮", "南方销区", "北方港口"]
        for region in regions:
            price = random.randint(2350, 2550)
            change = random.randint(-30, 30)
            
            record = RawDataRecord(
                business_date=base_date.strftime('%Y-%m-%d'),
                collected_at=datetime.now(),
                published_at=None,
                data_type="spot_price",
                indicator=f"玉米现货价格_{region}",
                value=float(price),
                unit="元/吨",
                region=region,
                source_url=self.site_url,
                original_text=f"模拟数据: {region}报价{price}元/吨,{'+' if change > 0 else ''}{change}",
                metadata={
                    "is_mock": True,
                    "change": change,
                    "collector_id": self.collector_id
                }
            )
            records.append(record)
        
        print(f"[{self.collector_id}] ✓ 生成 {len(records)} 条Mock数据")
        print(f"[{self.collector_id}]   - {len([r for r in records if r.data_type == 'arrivals'])} 条到车量")
        print(f"[{self.collector_id}]   - {len([r for r in records if r.data_type == 'spot_price'])} 条现货报价")
        
        return records


# 测试代码
if __name__ == "__main__":
    collector = MockCollector()
    
    print("\n" + "="*60)
    print("Mock采集器测试")
    print("="*60 + "\n")
    
    records = collector.collect()
    
    if records:
        print(f"\n✓ 生成 {len(records)} 条记录\n")
        
        # 显示到车量数据
        arrivals = [r for r in records if r.data_type == 'arrivals']
        if arrivals:
            print("山东到车量:")
            for r in arrivals:
                print(f"  {r.business_date}: {r.value:.0f} {r.unit}")
        
        # 显示现货报价
        prices = [r for r in records if r.data_type == 'spot_price']
        if prices:
            print(f"\n现货报价 ({prices[0].business_date}):")
            for r in prices:
                change = r.metadata.get('change', 0)
                change_str = f"{'↑' if change > 0 else '↓' if change < 0 else '→'}{abs(change)}"
                print(f"  {r.region:10}: {r.value:.0f} {r.unit} {change_str}")
    else:
        print("\n✗ 生成失败")
