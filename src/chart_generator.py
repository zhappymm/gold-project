import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import pandas as pd
import matplotlib.pyplot as plt
# 设置中文字体，兼容Windows/Mac/Linux服务器
plt.rcParams['font.sans-serif'] = [
    'Microsoft YaHei',
    'PingFang SC',
    'WenQuanYi Micro Hei',
    'Noto Sans CJK SC',
    'SimHei'
]
plt.rcParams['axes.unicode_minus'] = False
import sqlite3
import os

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 自动计算项目内的正确路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "gold_analysis.db")
RETURN_CSV = os.path.join(BASE_DIR, "data", "return_compare.csv")
CHART1 = os.path.join(BASE_DIR, "charts", "chart1_gold_trend.png")
CHART2 = os.path.join(BASE_DIR, "charts", "chart2_return_compare.png")
CHART3 = os.path.join(BASE_DIR, "charts", "chart3_cross_market.png")
CHART4 = os.path.join(BASE_DIR, "charts", "chart4_arbitrage_nav.png")

# 从data文件夹读取数据
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql("SELECT * FROM gold_monthly_data", conn)
cross_df = pd.read_sql("SELECT * FROM gold_cross_market", conn)
conn.close()
df["交易日期"] = pd.to_datetime(df["交易日期"])
cross_df["交易日期"] = pd.to_datetime(cross_df["交易日期"])
compare_df = pd.read_csv(RETURN_CSV, encoding="utf-8-sig")

# 图1：十年金价走势（自动存charts）
plt.figure(figsize=(10, 5), dpi=300)
plt.plot(df["交易日期"], df["国内收盘价_元每克"], color="#CC5500", linewidth=2)
plt.title("2016-2026年国内黄金价格走势", fontsize=14, fontweight="bold")
plt.xlabel("年份", fontsize=11)
plt.ylabel("收盘价（元/克）", fontsize=11)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(CHART1, dpi=300)
plt.close()

# 图2：定投与银行收益对比
x = range(len(compare_df))
width = 0.35
plt.figure(figsize=(9, 5), dpi=300)
plt.bar([i - width/2 for i in x], compare_df["囤金最终价值"], width=width, label="每月囤金", color="#CC5500")
plt.bar([i + width/2 for i in x], compare_df["银行最终价值"], width=width, label="银行定期", color="#9A8878")
plt.xticks(x, compare_df["持有年限"])
plt.title("不同持有周期 囤金vs银行定期 最终价值对比", fontsize=14, fontweight="bold")
plt.xlabel("持有年限", fontsize=11)
plt.ylabel("最终价值（元）", fontsize=11)
plt.legend()
plt.grid(axis="y", alpha=0.3)
for i, v in enumerate(compare_df["囤金最终价值"]):
    plt.text(i - width/2, v + 500, str(int(v)), ha="center", fontsize=9)
for i, v in enumerate(compare_df["银行最终价值"]):
    plt.text(i + width/2, v + 500, str(int(v)), ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(CHART2, dpi=300)
plt.close()

# 图3：内外盘价格对比
plt.figure(figsize=(10, 5), dpi=300)
plt.plot(cross_df["交易日期"], cross_df["国内收盘价_元每克"], label="国内黄金期货", color="#CC5500", linewidth=2)
plt.plot(cross_df["交易日期"], cross_df["外盘收盘价_元每克"], label="纽约COMEX黄金", color="#2558A0", linewidth=2)
plt.title("2016-2026年内外盘黄金价格走势对比", fontsize=14, fontweight="bold")
plt.xlabel("年份", fontsize=11)
plt.ylabel("价格（元/克）", fontsize=11)
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(CHART3, dpi=300)
plt.close()

# 图4：套利策略净值对比
data = cross_df.copy()
data["价差比例"] = (data["国内收盘价_元每克"] - data["外盘收盘价_元每克"]) / data["外盘收盘价_元每克"]
spread_mean = data["价差比例"].mean()
spread_std = data["价差比例"].std()
data["信号"] = 0
data.loc[data["价差比例"] > spread_mean + 2.0 * spread_std, "信号"] = -1
data.loc[data["价差比例"] < spread_mean - 2.0 * spread_std, "信号"] = 1
data["信号"] = data["信号"].shift(1).fillna(0)
data["国内收益率"] = data["国内收盘价_元每克"].pct_change()
data["外盘收益率"] = data["外盘收盘价_元每克"].pct_change()
data["策略收益率"] = data["信号"] * (data["国内收益率"] - data["外盘收益率"])
data["策略收益率"] = data.apply(lambda x: x["策略收益率"] - 0.0005 if x["信号"] != 0 else x["策略收益率"], axis=1)
data = data.dropna()
data["策略净值"] = (1 + data["策略收益率"]).cumprod()
data["基准净值"] = (1 + data["国内收益率"]).cumprod()

plt.figure(figsize=(10, 5), dpi=300)
plt.plot(data["交易日期"], data["策略净值"], label="跨市场套利策略", color="#1E7A4A", linewidth=2)
plt.plot(data["交易日期"], data["基准净值"], label="单边持有国内黄金（基准）", color="#9A8878", linewidth=2, linestyle="--")
plt.axhline(y=1, color="#333", linestyle=":", label="初始净值")
plt.title("跨市场套利策略 vs 单边持有 净值曲线对比", fontsize=14, fontweight="bold")
plt.xlabel("年份", fontsize=11)
plt.ylabel("净值（初始1.0）", fontsize=11)
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(CHART4, dpi=300)
plt.close()

print("===== 图表生成完成 =====")
print("所有图片已自动存入 charts 文件夹")