import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import akshare as ak
import pandas as pd
import sqlite3
import os

# 自动计算项目内的正确路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "gold_analysis.db")
CSV_PATH = os.path.join(BASE_DIR, "data", "gold_cross_market.csv")

# ========== 1. 获取国内黄金期货月度数据 ==========
gold_df = ak.futures_main_sina(symbol="AU0", start_date="20160101", end_date="20260630")
date_col = [c for c in gold_df.columns if "日期" in c or "date" in c.lower()][0]
close_col = [c for c in gold_df.columns if "收盘" in c or "close" in c.lower()][0]
volume_col = [c for c in gold_df.columns if "成交量" in c or "volume" in c.lower()][0]

gold_df[date_col] = pd.to_datetime(gold_df[date_col])
gold_df = gold_df.set_index(date_col).resample("ME").last().reset_index()
gold_df = gold_df[[date_col, close_col, volume_col]]
gold_df.columns = ["交易日期", "国内收盘价_元每克", "国内成交量"]

# ========== 2. 获取纽约COMEX黄金期货 + 汇率换算 ==========
ny_gold_df = ak.futures_foreign_hist(symbol="GC")
ny_date_col = [c for c in ny_gold_df.columns if "日期" in c or "date" in c.lower()][0]
ny_close_col = [c for c in ny_gold_df.columns if "收盘" in c or "close" in c.lower()][0]

ny_gold_df[ny_date_col] = pd.to_datetime(ny_gold_df[ny_date_col])
ny_gold_df = ny_gold_df.sort_values(ny_date_col)
ny_gold_df = ny_gold_df.set_index(ny_date_col).resample("ME").last().reset_index()
ny_gold_df = ny_gold_df[[ny_date_col, ny_close_col]]
ny_gold_df.columns = ["交易日期", "纽约金收盘价_美元每盎司"]

exchange_df = ak.currency_boc_sina(symbol="美元", start_date="20160101", end_date="20260630")
ex_date_col = [c for c in exchange_df.columns if "日期" in c or "date" in c.lower()][0]
ex_rate_col = [c for c in exchange_df.columns if "折算价" in c or "rate" in c.lower()][0]

exchange_df[ex_date_col] = pd.to_datetime(exchange_df[ex_date_col])
exchange_df = exchange_df.set_index(ex_date_col).resample("ME").last().reset_index()
exchange_df = exchange_df[[ex_date_col, ex_rate_col]]
exchange_df.columns = ["交易日期", "美元兑人民币汇率"]
exchange_df["美元兑人民币汇率"] = exchange_df["美元兑人民币汇率"] / 100

ny_gold_df = ny_gold_df.merge(exchange_df, on="交易日期", how="left")
ny_gold_df["外盘收盘价_元每克"] = ny_gold_df["纽约金收盘价_美元每盎司"] * ny_gold_df["美元兑人民币汇率"] / 31.1035
ny_gold_df = ny_gold_df[["交易日期", "外盘收盘价_元每克", "美元兑人民币汇率", "纽约金收盘价_美元每盎司"]]

# ========== 3. 双市场数据交易日对齐合并 ==========
merged_df = gold_df.merge(ny_gold_df, on="交易日期", how="inner")
merged_df = merged_df.dropna().reset_index(drop=True)

# ========== 4. 自动存入data文件夹 ==========
conn = sqlite3.connect(DB_PATH)
gold_df.to_sql("gold_monthly_data", conn, if_exists="replace", index=False)
merged_df.to_sql("gold_cross_market", conn, if_exists="replace", index=False)
conn.close()

merged_df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

print("===== 数据获取完成 =====")
print(f"国内黄金月度数据：{len(gold_df)} 条")
print(f"跨市场对齐数据：{len(merged_df)} 条")
print("数据库已自动存入 data 文件夹")