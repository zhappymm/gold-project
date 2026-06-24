# 黄金跨市场价差套利策略与定投收益分析系统

<div align="center">
  <img src="https://img.shields.io/badge/量化策略-均值回归-blue" alt="量化策略">
  <img src="https://img.shields.io/badge/数据-akshare-orange" alt="数据来源">
  <img src="https://img.shields.io/badge/可视化-Streamlit-green" alt="可视化">
  <img src="https://img.shields.io/badge/课程设计-财经数据分析-red" alt="课程设计">
</div>

## 项目简介
本项目基于2016-2026年国内沪金期货与纽约COMEX黄金期货的历史行情数据，完成两大核心研究：
1.  黄金定投收益回测与风险评估，对比银行定期理财的收益差异
2.  基于均值回归理论的内外盘跨市场套利策略验证，通过参数敏感性分析测试策略稳健性

项目最终落地为Streamlit交互仪表盘，支持自定义参数实时回测。

## 数据来源
| 数据集 | 来源 | 时间跨度 | 数据频率 |
|--------|------|----------|----------|
| 国内沪金期货主力合约 | akshare 新浪期货接口 | 2016-2026 | 月度 |
| 纽约COMEX黄金期货 | akshare 外盘期货接口 | 2016-2026 | 月度 |
| 美元兑人民币汇率 | 中国银行外汇牌价接口 | 2016-2026 | 月度 |

## 环境依赖
```bash
pip install -r requirements.txt

运行步骤
一键复现完整流程
# 1. 数据获取与入库（约1分钟）
python src/data_loader.py

# 2. 策略回测与指标计算（秒级）
python src/analysis.py

# 3. 生成静态分析图表（秒级）
python src/chart_generator.py

# 4. 启动交互仪表盘
streamlit run src/dashboard.py
浏览器访问 http://localhost:8501 即可使用

项目结构
gold-project/
├── README.md                    # 项目说明
├── requirements.txt             # 依赖清单
├── data/                        # 数据集与结果表
├── src/                         # 源代码
│   ├── data_loader.py           # 数据获取与入库
│   ├── analysis.py              # 策略回测与指标计算
│   ├── chart_generator.py       # 静态图表生成
│   └── dashboard.py             # Streamlit交互看板
├── charts/                      # 分析图表
├── report/                      # 项目报告
└── ppt/                         # 答辩PPT

核心结论
长期定投黄金的收益显著优于银行定期理财，持有周期越长收益稳定性越强
基于均值回归的跨市场价差套利策略，在 10 年回测期内实现稳定正收益，风险收益比优于单边持有
套利策略在 1.5-2.5 倍标准差阈值区间具备稳健性，默认选取 2 倍标准差为基准参数
免责声明
本项目仅作课程设计学习使用，所有回测结果基于历史数据，不构成任何投资建议