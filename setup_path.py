# 添加collectors-python到Python路径
import sys
from pathlib import Path

# 添加collectors-python目录
collectors_path = Path(__file__).parent / "collectors-python"
if str(collectors_path) not in sys.path:
    sys.path.insert(0, str(collectors_path))
