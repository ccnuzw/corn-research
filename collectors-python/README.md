# Collectors Python - 数据采集器

**语言**: Python 3.11+  
**原则**: 一站一器，灵活快速

## 目录结构

```
collectors/
├── base.py              # 采集器基类
├── boyar.py            # 博亚和讯
├── sina.py             # 新浪财经
├── dce.py              # 大商所
├── netease.py          # 网易订阅
└── __init__.py
```

## 快速开始

```bash
pip install -r requirements.txt
python -m collectors.boyar
```
