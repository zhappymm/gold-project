import pandas as pd
import sqlite3
import numpy as np
import os

# 自动计算项目内的正确路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "gold_analysis.db")
RETURN_CSV = os.path.join(BASE_DIR, "data", "return_compare.csv")
ARB_TXT = os.path.join(BASE_DIR, "data", "arbitrage_result.txt")
PRICE_TXT = os.path.join(BASE_DIR, "data", "price_percentile.txt")
SENS_CSV = os.path.join(BASE_DIR, "data", "threshold_sensitivity.csv")

# 从data文件夹读取数据库
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql("SELECT * FROM gold_monthly_data", conn)
cross_df = pd.read_sql("SELECT * FROM gold_cross_market", conn)
conn.close()
df["交易日期"] = pd.to_datetime(df["交易日期"])
cross_df["交易日期"] = pd.to_datetime(cross_df["交易日期"])

current_price = df["国内收盘价_元每克"].iloc[-1]

# ========== 1. 金价历史分位计算 ==========
price_percentile = round((df["国内收盘价_元每克"] < current_price).mean() * 100, 2)
if price_percentile < 20:
    level = "历史低价区，适合分批囤金"
elif 20 <= price_percentile <= 80:
    level = "历史合理区间，可正常定投"
else:
    level = "历史高价区，不建议追高"

# ========== 2. 定投收益 + 全套风险指标测算 ==========
def calc_gold_return(monthly_input, start_date=None, end_date=None):
    period_df = df.copy()
    if start_date:
        period_df = period_df[period_df["交易日期"] >= pd.to_datetime(start_date)]
    if end_date:
        period_df = period_df[period_df["交易日期"] <= pd.to_datetime(end_date)]
    period_df = period_df.reset_index(drop=True)

    total_gram = 0
    net_value_list = []
    for i in range(1, len(period_df)):
        buy_price = period_df["国内收盘价_元每克"].iloc[i - 1]
        total_gram += monthly_input / buy_price
        current_value = total_gram * period_df["国内收盘价_元每克"].iloc[i]
        net_value_list.append(current_value)

    final_value = total_gram * period_df["国内收盘价_元每克"].iloc[-1]
    total_cost = monthly_input * (len(period_df) - 1)
    total_profit = final_value - total_cost
    profit_rate = round(total_profit / total_cost * 100, 2)

    net_series = pd.Series(net_value_list)
    monthly_return = net_series.pct_change().dropna()
    peak = net_series.cummax()
    drawdown = (net_series - peak) / peak
    max_drawdown = round(drawdown.min() * 100, 2)
    annual_return = round((monthly_return.mean() * 12) * 100, 2)
    annual_volatility = round(monthly_return.std() * np.sqrt(12) * 100, 2)
    sharpe = round((monthly_return.mean() - 0.02 / 12) / monthly_return.std() * np.sqrt(12), 2)
    downside_return = monthly_return[monthly_return < 0]
    sortino = round((monthly_return.mean() - 0.02 / 12) / downside_return.std() * np.sqrt(12), 2) if len(downside_return) > 0 else 0
    calmar = round(annual_return / abs(max_drawdown), 2) if max_drawdown != 0 else 0

    hold_months = len(period_df) - 1
    hold_years = round(hold_months / 12, 2)

    return {
        "持有周期": f"{hold_years}年",
        "总投入": round(total_cost, 2),
        "最终价值": round(final_value, 2),
        "总收益": round(total_profit, 2),
        "收益率": profit_rate,
        "年化收益": annual_return,
        "最大回撤": max_drawdown,
        "年化波动率": annual_volatility,
        "夏普比率": sharpe,
        "索提诺比率": sortino,
        "卡玛比率": calmar
    }

# ========== 3. 银行定期收益测算 ==========
def calc_bank_return(monthly_input, hold_months, year_rate=0.025):
    month_rate = year_rate / 12
    final_value = monthly_input * (((1 + month_rate) ** hold_months - 1) / month_rate)
    total_cost = monthly_input * hold_months
    total_profit = final_value - total_cost
    return {
        "总投入": round(total_cost, 2),
        "最终价值": round(final_value, 2),
        "总收益": round(total_profit, 2),
        "收益率": round(total_profit / total_cost * 100, 2)
    }

# ========== 4. 跨市场价差统计 + 套利策略回测 ==========
def calc_arbitrage_strategy(spread_threshold=2.0, fee_rate=0.0005):
    data = cross_df.copy()
    data["价差"] = data["国内收盘价_元每克"] - data["外盘收盘价_元每克"]
    data["价差比例"] = data["价差"] / data["外盘收盘价_元每克"]
    spread_mean = data["价差比例"].mean()
    spread_std = data["价差比例"].std()

    data["信号"] = 0
    data.loc[data["价差比例"] > spread_mean + spread_threshold * spread_std, "信号"] = -1
    data.loc[data["价差比例"] < spread_mean - spread_threshold * spread_std, "信号"] = 1
    data["信号"] = data["信号"].shift(1).fillna(0)

    data["国内收益率"] = data["国内收盘价_元每克"].pct_change()
    data["外盘收益率"] = data["外盘收盘价_元每克"].pct_change()
    data["策略收益率"] = data["信号"] * (data["国内收益率"] - data["外盘收益率"])
    data["策略收益率"] = data.apply(lambda x: x["策略收益率"] - fee_rate if x["信号"] != 0 else x["策略收益率"], axis=1)
    data = data.dropna()
    data["净值"] = (1 + data["策略收益率"]).cumprod()
    data["基准净值"] = (1 + data["国内收益率"]).cumprod()

    total_return = round((data["净值"].iloc[-1] - 1) * 100, 2)
    annual_ret = round((data["策略收益率"].mean() * 12) * 100, 2)
    annual_vol = round(data["策略收益率"].std() * np.sqrt(12) * 100, 2)
    peak = data["净值"].cummax()
    dd = (data["净值"] - peak) / peak
    max_dd = round(dd.min() * 100, 2)
    sharpe = round((data["策略收益率"].mean() - 0.02 / 12) / data["策略收益率"].std() * np.sqrt(12), 2)
    downside = data["策略收益率"][data["策略收益率"] < 0]
    sortino = round((data["策略收益率"].mean() - 0.02 / 12) / downside.std() * np.sqrt(12), 2) if len(downside) > 0 else 0
    calmar = round(annual_ret / abs(max_dd), 2) if max_dd != 0 else 0
    win_rate = round(len(data[data["策略收益率"] > 0]) / len(data) * 100, 2)

    bench_return = round((data["基准净值"].iloc[-1] - 1) * 100, 2)
    bench_sharpe = round((data["国内收益率"].mean() - 0.02 / 12) / data["国内收益率"].std() * np.sqrt(12), 2)

    return {
        "价差均值(%)": round(spread_mean * 100, 2),
        "价差标准差(%)": round(spread_std * 100, 2),
        "累计收益(%)": total_return,
        "年化收益(%)": annual_ret,
        "最大回撤(%)": max_dd,
        "年化波动率(%)": annual_vol,
        "夏普比率": sharpe,
        "索提诺比率": sortino,
        "卡玛比率": calmar,
        "胜率(%)": win_rate,
        "基准累计收益(%)": bench_return,
        "基准夏普比率": bench_sharpe,
        "净值序列": data["净值"].values,
        "基准净值序列": data["基准净值"].values,
        "日期序列": data["交易日期"].values
    }

# ========== 5. 多周期定投对比结果（自动存data） ==========
year_list = [3, 5, 10]
monthly_money = 500
result_rows = []
for y in year_list:
    months = y * 12
    gold_res = calc_gold_return(monthly_money, start_date=df["交易日期"].iloc[-(months + 1)])
    bank_res = calc_bank_return(monthly_money, months)
    result_rows.append({
        "持有年限": f"{y}年",
        "每月投入": monthly_money,
        "囤金最终价值": gold_res["最终价值"],
        "银行最终价值": bank_res["最终价值"],
        "囤金收益率": f"{gold_res['收益率']}%",
        "银行收益率": f"{bank_res['收益率']}%",
        "最大回撤": f"{gold_res['最大回撤']}%",
        "夏普比率": gold_res["夏普比率"]
    })

result_df = pd.DataFrame(result_rows)
result_df.to_csv(RETURN_CSV, index=False, encoding="utf-8-sig")

# ========== 6. 套利策略结果输出（自动存data） ==========
arb_result = calc_arbitrage_strategy(2.0)
with open(ARB_TXT, "w", encoding="utf-8") as f:
    f.write("===== 国内黄金-纽约金跨市场套利策略回测结果（2倍标准差阈值） =====\n")
    f.write(f"价差均值：{arb_result['价差均值(%)']}%\n")
    f.write(f"价差标准差：{arb_result['价差标准差(%)']}%\n")
    f.write(f"策略累计收益：{arb_result['累计收益(%)']}%\n")
    f.write(f"策略年化收益：{arb_result['年化收益(%)']}%\n")
    f.write(f"策略最大回撤：{arb_result['最大回撤(%)']}%\n")
    f.write(f"策略夏普比率：{arb_result['夏普比率']}\n")
    f.write(f"策略索提诺比率：{arb_result['索提诺比率']}\n")
    f.write(f"策略卡玛比率：{arb_result['卡玛比率']}\n")
    f.write(f"策略胜率：{arb_result['胜率(%)']}%\n")
    f.write("\n===== 基准对比（单边持有国内黄金） =====\n")
    f.write(f"基准累计收益：{arb_result['基准累计收益(%)']}%\n")
    f.write(f"基准夏普比率：{arb_result['基准夏普比率']}\n")

with open(PRICE_TXT, "w", encoding="utf-8") as f:
    f.write(f"当前金价：{round(current_price, 2)} 元/克\n")
    f.write(f"十年历史分位：{price_percentile}%\n")
    f.write(f"价格档位：{level}\n")

# ========== 7. 参数敏感性分析表（自动存data） ==========
threshold_list = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
sens_rows = []
for t in threshold_list:
    res = calc_arbitrage_strategy(t)
    sens_rows.append({
        "阈值(倍标准差)": t,
        "累计收益(%)": res["累计收益(%)"],
        "年化收益(%)": res["年化收益(%)"],
        "最大回撤(%)": res["最大回撤(%)"],
        "夏普比率": res["夏普比率"],
        "胜率(%)": res["胜率(%)"]
    })
sens_df = pd.DataFrame(sens_rows)
sens_df.to_csv(SENS_CSV, index=False, encoding="utf-8-sig")

print("===== 分析计算完成 =====")
print("所有结果已自动存入 data 文件夹")