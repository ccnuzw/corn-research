"""
DCE期货采集器 - 大连商品交易所玉米期货数据
数据源: http://www.dce.com.cn/
"""
import requests
from datetime import datetime
from typing import List

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base import BaseCollector, RawDataRecord


class DCEFuturesCollector(BaseCollector):
    """DCE玉米期货采集器 - A级数据源"""
    
    @property
    def collector_id(self) -> str:
        return "futures_dce"
    
    @property
    def site_name(self) -> str:
        return "大连商品交易所"
    
    @property
    def site_url(self) -> str:
        return "http://www.dce.com.cn"
    
    @property
    def source_type(self) -> str:
        return "official_exchange"
    
    def __init__(self):
        self.base_url = "http://www.dce.com.cn"
        self.quote_url = f"{self.base_url}/publicweb/quotesdata/dayQuotesCh.html"
        
    def collect(self, **kwargs) -> List[RawDataRecord]:
        """
        采集DCE玉米期货行情数据
        
        返回:
            List[RawDataRecord]: 原始采集记录列表
        """
        print(f"[{self.collector_id}] 开始采集DCE期货数据...")
        print(f"[{self.collector_id}] 目标URL: {self.quote_url}")
        
        try:
            # 1. 请求页面（使用完整的浏览器头）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 使用session保持会话
            session = requests.Session()
            response = session.get(self.quote_url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"[{self.collector_id}] ✗ HTTP错误: {response.status_code}")
                return []
            
            html = response.text
            
            # 2. 提取发布时间（简化处理）
            business_date = datetime.now().strftime('%Y-%m-%d')
            
            # 3. 提取期货合约价格（简化版）
            records = []
            if BeautifulSoup:
                soup = BeautifulSoup(html, 'lxml')
                # 查找所有包含玉米合约的行
                lines = soup.get_text().split('\n')
                for line in lines:
                    if line.strip().startswith('c') or line.strip().startswith('C'):
                        # 简单提取：合约名开头的行
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                contract = parts[0]
                                close_price = float(parts[4].replace(',', ''))
                                
                                record = RawDataRecord(
                                    business_date=business_date,
                                    collected_at=datetime.now(),
                                    published_at=None,
                                    data_type="futures",
                                    indicator=f"DCE玉米期货_{contract}",
                                    value=close_price,
                                    unit="元/吨",
                                    region="全国",
                                    source_url=self.quote_url,
                                    original_text=line.strip(),
                                    metadata={
                                        "exchange": "DCE",
                                        "contract": contract,
                                        "collector_id": self.collector_id
                                    }
                                )
                                records.append(record)
                            except (ValueError, IndexError):
                                continue
            
            if records:
                print(f"[{self.collector_id}] ✓ 采集成功: {len(records)} 条合约数据")
                for i, r in enumerate(records[:3]):
                    print(f"[{self.collector_id}]   [{i+1}] {r.indicator}: {r.value} {r.unit}")
            else:
                print(f"[{self.collector_id}] ⚠ 未提取到数据，保存HTML供分析")
                # 即使未提取到结构化数据，也保存原始HTML
                record = RawDataRecord(
                    business_date=business_date,
                    collected_at=datetime.now(),
                    published_at=None,
                    data_type="futures",
                    indicator="DCE玉米期货",
                    value=0.0,
                    unit="元/吨",
                    region="全国",
                    source_url=self.quote_url,
                    original_text=html[:500],  # 保存前500字符
                    metadata={
                        "exchange": "DCE",
                        "html_length": len(html),
                        "collector_id": self.collector_id
                    }
                )
                records = [record]
            
            return records
            
        except requests.RequestException as e:
            print(f"[{self.collector_id}] ✗ 网络错误: {e}")
            return []
        except Exception as e:
            print(f"[{self.collector_id}] ✗ 未知错误: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    collector = DCEFuturesCollector()
    
    print("\n" + "="*60)
    print("DCE期货采集器测试")
    print("="*60 + "\n")
    
    # 执行采集
    records = collector.collect()
    
    if records:
        print(f"\n✓ 采集到 {len(records)} 条记录")
        for i, r in enumerate(records[:5]):
            print(f"  [{i+1}] {r.indicator}: {r.value} {r.unit} (业务日期: {r.business_date})")
    else:
        print("\n✗ 采集失败")
