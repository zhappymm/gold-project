import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import os
import streamlit as st
import pandas as pd
import sqlite3
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
import numpy as np

st.set_page_config(page_title="黄金跨市场价差套利策略与定投收益分析系统", layout="wide")
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 自动计算项目内的正确路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "gold_analysis.db")

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM gold_monthly_data", conn)
    cross_df = pd.read_sql("SELECT * FROM gold_cross_market", conn)
    conn.close()
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    cross_df["交易日期"] = pd.to_datetime(cross_df["交易日期"])
    return df, cross_df

df, cross_df = load_data()
current_price = df["国内收盘价_元每克"].iloc[-1]
min_date = df["交易日期"].min()
max_date = df["交易日期"].max()

page = st.sidebar.radio("功能模块", ["定投收益分析", "跨市场套利分析"])

# ========== 页面1：定投收益分析 ==========
if page == "定投收益分析":
    st.title("黄金定投收益分析")
    st.markdown("---")

    with st.sidebar:
        monthly_input = st.number_input("每月投入金额（元）", min_value=100, max_value=2000, value=500, step=100)
        bank_rate = st.number_input("银行定期年利率", min_value=0.01, max_value=0.05, value=0.025, step=0.005, format="%.3f")
        st.divider()
        start_dt = st.date_input("回测起始日期", value=min_date, min_value=min_date, max_value=max_date)
        end_dt = st.date_input("回测结束日期", value=max_date, min_value=min_date, max_value=max_date)

    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    total_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)

    def calc_gold(monthly_input, start_date, end_date):
        period_df = df.copy()
        period_df = period_df[(period_df["交易日期"] >= start_date) & (period_df["交易日期"] <= end_date)]
        period_df = period_df.reset_index(drop=True)
        total_gram = 0
        net_value_list = []
        for i in range(1, len(period_df)):
            buy_price = period_df["国内收盘价_元每克"].iloc[i - 1]
            total_gram += monthly_input / buy_price
            net_value_list.append(total_gram * period_df["国内收盘价_元每克"].iloc[i])
        final_value = total_gram * period_df["国内收盘价_元每克"].iloc[-1]
        total_cost = monthly_input * (len(period_df) - 1)
        total_profit = final_value - total_cost
        profit_rate = round(total_profit / total_cost * 100, 2)
        net_series = pd.Series(net_value_list)
        monthly_return = net_series.pct_change().dropna()
        peak = net_series.cummax()
        drawdown = (net_series - peak) / peak
        max_drawdown = round(drawdown.min() * 100, 2)
        sharpe = round((monthly_return.mean() - 0.02 / 12) / monthly_return.std() * np.sqrt(12), 2)
        hold_months = len(period_df) - 1
        hold_years = round(hold_months / 12, 2)
        return total_cost, round(final_value, 2), round(total_profit, 2), profit_rate, max_drawdown, sharpe, hold_years, hold_months

    def calc_bank(monthly_input, hold_months, year_rate):
        month_rate = year_rate / 12
        final_value = monthly_input * (((1 + month_rate) ** hold_months - 1) / month_rate)
        total_cost = monthly_input * hold_months
        total_profit = final_value - total_cost
        return total_cost, round(final_value, 2), round(total_profit, 2), round(total_profit / total_cost * 100, 2)

    gold_cost, gold_final, gold_profit, gold_rate, max_dd, sharpe, hold_y, hold_m = calc_gold(monthly_input, start_dt, end_dt)
    bank_cost, bank_final, bank_profit, bank_rate = calc_bank(monthly_input, total_months, bank_rate)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("当前金价", f"{round(current_price, 2)} 元/克")
    col2.metric("总投入本金", f"{gold_cost} 元")
    col3.metric("囤金最终价值", f"{gold_final} 元", f"+{gold_profit}元")
    col4.metric("银行定期最终价值", f"{bank_final} 元", f"+{bank_profit}元")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("总收益率", f"{gold_rate}%")
    col_b.metric("最大回撤", f"{max_dd}%")
    col_c.metric("夏普比率", sharpe)
    col_d.metric("持有周期", f"{hold_y}年（{hold_m}个月）")

    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("黄金价格走势")
        fig1, ax1 = plt.subplots(figsize=(7, 4), dpi=150)
        ax1.plot(df["交易日期"], df["国内收盘价_元每克"], color="#CC5500", linewidth=2)
        ax1.set_xlabel("年份")
        ax1.set_ylabel("价格（元/克）")
        ax1.grid(alpha=0.3)
        st.pyplot(fig1)
    with col_right:
        st.subheader("囤金 vs 银行收益对比")
        fig2, ax2 = plt.subplots(figsize=(7, 4), dpi=150)
        ax2.bar(["每月囤金", "银行定期"], [gold_final, bank_final], color=["#CC5500", "#9A8878"], width=0.5)
        ax2.set_ylabel("最终价值（元）")
        ax2.grid(axis="y", alpha=0.3)
        for i, v in enumerate([gold_final, bank_final]):
            ax2.text(i, v + 500, str(int(v)), ha="center")
        st.pyplot(fig2)

# ========== 页面2：跨市场套利分析 ==========
else:
    st.title("国内黄金-纽约金跨市场套利分析")
    st.markdown("---")

    with st.sidebar:
        spread_threshold = st.slider("套利偏离阈值（倍标准差）", min_value=0.5, max_value=3.0, value=2.0, step=0.1)
        st.caption("阈值越高，触发套利次数越少，胜率通常越高")

    data = cross_df.copy()
    data["价差比例"] = (data["国内收盘价_元每克"] - data["外盘收盘价_元每克"]) / data["外盘收盘价_元每克"]
    spread_mean = data["价差比例"].mean()
    spread_std = data["价差比例"].std()

    data["信号"] = 0
    data.loc[data["价差比例"] > spread_mean + spread_threshold * spread_std, "信号"] = -1
    data.loc[data["价差比例"] < spread_mean - spread_threshold * spread_std, "信号"] = 1
    data["信号"] = data["信号"].shift(1).fillna(0)

    data["国内收益率"] = data["国内收盘价_元每克"].pct_change()
    data["外盘收益率"] = data["外盘收盘价_元每克"].pct_change()
    data["策略收益率"] = data["信号"] * (data["国内收益率"] - data["外盘收益率"])
    data["策略收益率"] = data.apply(lambda x: x["策略收益率"] - 0.0005 if x["信号"] != 0 else x["策略收益率"], axis=1)
    data = data.dropna()
    data["策略净值"] = (1 + data["策略收益率"]).cumprod()
    data["基准净值"] = (1 + data["国内收益率"]).cumprod()

    total_return = round((data["策略净值"].iloc[-1] - 1) * 100, 2)
    annual_ret = round((data["策略收益率"].mean() * 12) * 100, 2)
    peak = data["策略净值"].cummax()
    dd = (data["策略净值"] - peak) / peak
    max_dd = round(dd.min() * 100, 2)
    sharpe = round((data["策略收益率"].mean() - 0.02 / 12) / data["策略收益率"].std() * np.sqrt(12), 2)
    win_rate = round(len(data[data["策略收益率"] > 0]) / len(data) * 100, 2)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("累计策略收益", f"{total_return}%")
    col2.metric("年化收益", f"{annual_ret}%")
    col3.metric("最大回撤", f"{max_dd}%")
    col4.metric("夏普比率", sharpe)

    col_a, col_b, _, _ = st.columns(4)
    col_a.metric("策略胜率", f"{win_rate}%")
    col_b.metric("平均价差", f"{round(spread_mean * 100, 2)}%")

    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("双市场价格走势对比")
        fig1, ax1 = plt.subplots(figsize=(7, 4), dpi=150)
        ax1.plot(data["交易日期"], data["国内收盘价_元每克"], label="国内黄金期货", color="#CC5500", linewidth=2)
        ax1.plot(data["交易日期"], data["外盘收盘价_元每克"], label="纽约COMEX黄金", color="#2558A0", linewidth=2)
        ax1.set_xlabel("日期")
        ax1.set_ylabel("价格（元/克）")
        ax1.legend()
        ax1.grid(alpha=0.3)
        st.pyplot(fig1)

    with col_right:
        st.subheader("套利策略净值曲线")
        fig2, ax2 = plt.subplots(figsize=(7, 4), dpi=150)
        ax2.plot(data["交易日期"], data["策略净值"], color="#1E7A4A", linewidth=2, label="套利策略净值")
        ax2.plot(data["交易日期"], data["基准净值"], color="#9A8878", linewidth=2, linestyle="--", label="单边持有基准")
        ax2.axhline(y=1, color="#999", linestyle=":", label="初始净值")
        ax2.set_xlabel("日期")
        ax2.set_ylabel("净值")
        ax2.legend()
        ax2.grid(alpha=0.3)
        st.pyplot(fig2)

    st.markdown("---")
    st.subheader("历史价差分布与套利轨道")
    fig3, ax3 = plt.subplots(figsize=(14, 4), dpi=150)
    ax3.plot(data["交易日期"], data["价差比例"] * 100, color="#CC5500", linewidth=1.5, label="实际价差")
    ax3.axhline(y=spread_mean * 100, color="#1C1410", linestyle="--", label="价差均值")
    ax3.axhline(y=(spread_mean + spread_threshold * spread_std) * 100, color="#B83020", linestyle=":", label="上轨（做空国内）")
    ax3.axhline(y=(spread_mean - spread_threshold * spread_std) * 100, color="#1E7A4A", linestyle=":", label="下轨（做多国内）")
    ax3.set_xlabel("日期")
    ax3.set_ylabel("价差比例（%）")
    ax3.legend()
    ax3.grid(alpha=0.3)
    st.pyplot(fig3)

st.markdown("---")
st.caption("数据来源：上海期货交易所、纽约COMEX交易所 | 历史回测不代表未来收益，仅作课程设计演示")