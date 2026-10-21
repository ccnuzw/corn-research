"""
CFT现货报价采集器 - 中国饲料行业信息网
数据源: https://www.cngrain.com
"""
import requests
from datetime import datetime
from typing import List
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base import BaseCollector, RawDataRecord


class CFTSpotCollector(BaseCollector):
    """CFT玉米现货报价采集器 - B级数据源"""
    
    @property
    def collector_id(self) -> str:
        return "spot_cft"
    
    @property
    def site_name(self) -> str:
        return "中国饲料行业信息网"
    
    @property
    def site_url(self) -> str:
        return "https://www.cngrain.com"
    
    @property
    def source_type(self) -> str:
        return "industry_portal"
    
    def __init__(self):
        self.base_url = "https://www.cngrain.com"
        self.price_url = f"{self.base_url}/publish/jgjc/corn.shtml"
    
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        采集CFT玉米现货报价
        
        返回:
            List[RawDataRecord]: 原始采集记录列表
        """
        print(f"[{self.collector_id}] 开始采集CFT现货报价...")
        print(f"[{self.collector_id}] 目标URL: {self.price_url}")
        
        try:
            # 1. 请求页面
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            
            response = requests.get(self.price_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"[{self.collector_id}] ✗ HTTP错误: {response.status_code}")
                return []
            
            # 设置正确的编码
            response.encoding = response.apparent_encoding or 'utf-8'
            html = response.text
            
            # 2. 提取业务日期和价格数据
            business_date = datetime.now().strftime('%Y-%m-%d')
            records = []
            
            if BeautifulSoup:
                soup = BeautifulSoup(html, 'lxml')
                
                # 提取发布日期
                date_text = soup.select_one('.date, .time, .publish-time')
                if date_text:
                    date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_text.get_text())
                    if date_match:
                        business_date = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
                
                # 查找价格表格
                table = soup.select_one('table.price-table, table')
                if table:
                    rows = table.select('tr')[1:]  # 跳过表头
                    
                    for row in rows:
                        cols = row.select('td')
                        if len(cols) >= 3:
                            try:
                                region_text = cols[0].get_text().strip()
                                price_text = cols[1].get_text().strip()
                                change_text = cols[2].get_text().strip() if len(cols) > 2 else ''
                                
                                # 提取价格数字
                                price_match = re.search(r'(\d+\.?\d*)', price_text)
                                if price_match and region_text:
                                    price = float(price_match.group(1))
                                    
                                    # 提取涨跌
                                    change = 0.0
                                    change_match = re.search(r'([+\-]?\d+\.?\d*)', change_text)
                                    if change_match:
                                        change = float(change_match.group(1))
                                    
                                    record = RawDataRecord(
                                        business_date=business_date,
                                        collected_at=datetime.now(),
                                        published_at=None,
                                        data_type="spot_price",
                                        indicator=f"玉米现货价格_{region_text}",
                                        value=price,
                                        unit="元/吨",
                                        region=region_text,
                                        source_url=self.price_url,
                                        original_text=f"{region_text} {price_text} {change_text}",
                                        metadata={
                                            "change": change,
                                            "collector_id": self.collector_id,
                                            "price_type": "现货报价"
                                        }
                                    )
                                    records.append(record)
                            except (ValueError, IndexError) as e:
                                continue
            
            if records:
                print(f"[{self.collector_id}] ✓ 采集成功: {len(records)} 条报价")
                for i, r in enumerate(records[:5]):
                    change_str = f"{'↑' if r.metadata.get('change', 0) > 0 else '↓' if r.metadata.get('change', 0) < 0 else '→'}{abs(r.metadata.get('change', 0))}"
                    print(f"[{self.collector_id}]   [{i+1}] {r.region}: {r.value} {r.unit} {change_str}")
                    
                if len(records) > 5:
                    print(f"[{self.collector_id}]   ... 还有 {len(records) - 5} 条")
            else:
                print(f"[{self.collector_id}] ⚠ 未提取到数据")
                # 保存HTML供调试
                record = RawDataRecord(
                    business_date=business_date,
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="spot_price",
                    indicator="CFT玉米现货",
                    value=0.0,
                    unit="元/吨",
                    region="全国",
                    source_url=self.price_url,
                    original_text=html[:1000],
                    metadata={
                        "html_length": len(html),
                        "collector_id": self.collector_id,
                        "status": "no_data_extracted"
                    }
                )
                records = [record]
            
            return records
            
        except requests.RequestException as e:
            print(f"[{self.collector_id}] ✗ 网络错误: {e}")
            return []
        except Exception as e:
            print(f"[{self.collector_id}] ✗ 未知错误: {e}")
            import traceback
            traceback.print_exc()
            return []


# 测试代码
if __name__ == "__main__":
    collector = CFTSpotCollector()
    
    print("\n" + "="*60)
    print("CFT现货报价采集器测试")
    print("="*60 + "\n")
    
    # 执行采集
    records = collector.collect()
    
    if records:
        print(f"\n✓ 采集到 {len(records)} 条记录")
        print(f"\n业务日期: {records[0].business_date}")
        print(f"\n前10条报价:")
        print("-"*60)
        for i, r in enumerate(records[:10]):
            change = r.metadata.get('change', 0)
            change_str = f"{'↑' if change > 0 else '↓' if change < 0 else '→'}{abs(change):>4.0f}"
            print(f"  {i+1:2}. {r.region:12} | {r.value:6.0f} {r.unit} | {change_str}")
    else:
        print("\n✗ 采集失败")
