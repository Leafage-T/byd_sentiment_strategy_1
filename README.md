\# 比亚迪舆情+技术指标复合量化择时策略

\## 项目介绍

本项目以比亚迪个股为标的，融合日线行情、PE/PB估值、新浪+东方财富财经新闻，

通过SnowNLP文本情感打分构建舆情因子，搭配MA/MACD/RSI多重技术指标实现择时回测，

区分训练集(2020-2025)、样本外(2026)验证，附带完整Streamlit交互式答辩可视化页面。



\## 项目文件结构

├── data\_get.py          # 数据采集、清洗、情感计算、入库主程序

├── strategy\_backtest.py # 策略信号生成、回测、绩效指标计算

├── streamlit\_report.py  # 答辩专用7页交互式可视化页面

├── streamlit\_dashboard.py # 简易图表面板（备用）

├── raw\_\*.csv           # 爬虫原始未清洗数据

├── total\_factor\_df.csv # 清洗整合总因子表（回测输入）

├── backtest\_result.csv # 每日回测明细

├── metrics\_summary.csv # 分段绩效汇总指标

├── requirements.txt    # 一键依赖安装清单

├── README.md           # 项目说明文档

├── .gitignore          # Git缓存过滤配置



\## 环境部署

1\. 安装Python环境（3.9\~3.11推荐）

2\. 安装全部依赖库

```bash

pip install -r requirements.txt

