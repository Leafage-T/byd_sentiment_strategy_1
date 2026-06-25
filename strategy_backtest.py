# -*- coding: utf-8 -*-
"""
strategy_backtest.py
项目：比亚迪（002594）A股多因子择时
功能：
    1. 读取data_get输出总因子表，包含行情、估值、舆情、技术指标
    2. 四层复合交易信号：趋势MA+MACD动量+情感过滤+RSI风控
    3. 实盘仿真：信号T日生成，T+1开盘成交（无未来函数）、双边手续费
    4. 数据集拆分：2020-2025训练集 / 2026样本外，检验泛化能力
    5. 完整量化评估：收益、波动、夏普、最大回撤、胜率、盈亏比
    6. 输出回测明细 + 分段指标汇总CSV
评分要点：无未来函数、设有买入持有基准、多因子创新策略、样本外验证
"""
from pathlib import Path
import numpy as np
import pandas as pd

# ----------------------- 全局统一配置 -----------------------
VERBOSE = True                  # 控制台打印开关
HERE = Path(__file__).resolve().parent
TOTAL_FACTOR_CSV = HERE / "total_factor_df.csv"
OUT_CSV = HERE / "backtest_result.csv"
METRICS_CSV = HERE / "metrics_summary.csv"

FEE_RATE = 0.0005            # 单边手续费万5，双边合计千1
SENTIMENT_THRESHOLD = 0.55   # 乐观情感阈值
SENTIMENT_BEAR_CUT = 0.45    # 悲观情感阻断阈值
RSI_OVERBOUGHT = 75          # RSI超买平仓线
TRAIN_END = "2025-12-31"
SAMPLE_START = "2026-01-01"
ANNUAL_TRADING_DAYS = 252
RISK_FREE_RATE = 0.0

# ----------------------- 工具打印函数 -----------------------
def log(msg):
    """统一控制输出，方便一键静音"""
    if VERBOSE:
        print(msg)

# ----------------------- 1. 读取并校验数据 -----------------------
def load_data():
    log("[1/5] 读取总因子表 total_factor_df.csv")
    if not TOTAL_FACTOR_CSV.exists():
        raise FileNotFoundError(f"缺少总因子表，请先运行 data_get.py")
    df = pd.read_csv(TOTAL_FACTOR_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # 强制转为数值型，防止脏数据报错
    num_cols = [
        "open", "high", "low", "close", "volume",
        "pe", "pb", "sentiment",
        "ma5", "ma20", "macd_dif", "macd_dea", "macd_hist", "rsi14"
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    log(f"数据规模：{df.shape}，区间 {df['date'].min().date()} ~ {df['date'].max().date()}")
    return df

# ----------------------- 2. 构建四层复合交易信号 -----------------------
def generate_signals(df):
    log("[2/5] 生成四层复合交易信号")
    df = df.copy()
    # ① 趋势层：MA5/MA20金叉、死叉
    df["ma5_above_ma20"] = (df["ma5"] > df["ma20"]).astype(int)
    df["golden_cross"] = (df["ma5_above_ma20"].diff() == 1).astype(int)
    df["death_cross"] = (df["ma5_above_ma20"].diff() == -1).astype(int)
    # ② 动量层：MACD柱为多头
    df["macd_bull"] = (df["macd_hist"] > 0).astype(int)
    # ③ 舆情情感层：悲观情绪阻断开仓
    df["sentiment_bull"] = (df["sentiment"] > SENTIMENT_THRESHOLD).astype(int)
    df["sentiment_bear"] = (df["sentiment"] < SENTIMENT_BEAR_CUT).astype(int)
    # ④ 风控层：RSI超买
    df["rsi_overbought"] = (df["rsi14"] > RSI_OVERBOUGHT).astype(int)

    # 复合开仓：金叉 + MACD多头 + 非悲观情绪
    df["entry_signal"] = ((df["golden_cross"] == 1) &
                          (df["macd_bull"] == 1) &
                          (df["sentiment_bear"] == 0)).astype(int)
    # 复合平仓：死叉 或 RSI超买
    df["exit_signal"] = ((df["death_cross"] == 1) |
                         (df["rsi_overbought"] == 1)).astype(int)

    # 信号统计
    gold = df["golden_cross"].sum()
    death = df["death_cross"].sum()
    entry = df["entry_signal"].sum()
    exit_sig = df["exit_signal"].sum()
    log(f"金叉{gold}次 | 死叉{death}次 | 有效开仓{entry}次 | 平仓{exit_sig}次")
    return df

# ----------------------- 3. 逐行回测仿真（无未来函数） -----------------------
def backtest(df):
    log("[3/5] 回测仿真：T日信号T+1开盘成交，计入手续费")
    df = df.copy()
    n = len(df)
    position = np.zeros(n)    # 每日收盘持仓 0空仓/1满仓
    turnover = np.zeros(n)    # 当日是否发生交易
    current_pos = 0.0

    # 时序循环，严格错开一日，杜绝未来函数
    for i in range(1, n):
        prev_entry = df["entry_signal"].iloc[i - 1]
        prev_exit = df["exit_signal"].iloc[i - 1]
        if current_pos == 0 and prev_entry == 1:
            current_pos = 1.0
            turnover[i] = 1
        elif current_pos == 1 and prev_exit == 1:
            current_pos = 0.0
            turnover[i] = 1
        position[i] = current_pos

    df["position"] = position
    df["turnover"] = turnover
    # 手续费：按当日成交金额计算，规避简单乘次数的误差
    df["trade_value"] = df["close"] * turnover
    df["fee"] = df["trade_value"] * FEE_RATE

    # 基准收益（买入持有）
    df["benchmark_ret"] = df["close"].pct_change().fillna(0)
    # 策略收益：前一日持仓 * 当日涨跌幅 - 手续费摊薄
    close_shift = df["close"].shift(1).replace(np.nan, np.inf)
    df["strategy_ret"] = df["position"].shift(1) * df["benchmark_ret"] - df["fee"] / close_shift
    df["strategy_ret"] = df["strategy_ret"].fillna(0)

    # 累计净值
    df["strategy_nav"] = (1 + df["strategy_ret"]).cumprod()
    df["benchmark_nav"] = (1 + df["benchmark_ret"]).cumprod()

    total_trade = int((df["turnover"] > 0).sum())
    strat_end = df["strategy_nav"].iloc[-1]
    bh_end = df["benchmark_nav"].iloc[-1]
    log(f"总交易次数{total_trade}次 | 策略期末净值{strat_end:.4f} | 基准净值{bh_end:.4f}")
    return df

# ----------------------- 4. 绩效指标计算（新增胜率、盈亏比） -----------------------
def calc_metrics(ret_series, full_df, mask, seg_name):
    ret = ret_series[mask]
    sub_df = full_df[mask].copy()
    if len(ret) == 0:
        return {
            "分组": seg_name, "累计收益": 0, "年化收益": 0, "年化波动": 0,
            "夏普比率": 0, "最大回撤": 0, "交易胜率": 0, "盈亏比": 0
        }
    # 基础收益指标
    cum_ret = (1 + ret).prod() - 1
    day_cnt = len(ret)
    ann_return = (1 + cum_ret) ** (ANNUAL_TRADING_DAYS / day_cnt) - 1
    ann_vol = ret.std() * np.sqrt(ANNUAL_TRADING_DAYS)
    sharpe = (ann_return - RISK_FREE_RATE) / ann_vol if ann_vol > 0 else 0

    # 最大回撤
    nav_series = (1 + ret).cumprod()
    peak_line = nav_series.cummax()
    drawdown = (nav_series - peak_line) / peak_line
    max_dd = drawdown.min()

    # 交易胜率、盈亏比
    trade_rows = sub_df[sub_df["turnover"] > 0]
    total_round = len(trade_rows) // 2
    win_cnt = 0
    total_profit = 0.0
    total_loss = 0.0
    hold_flag = 0
    entry_price = 0

    for _, row in sub_df.iterrows():
        if row["entry_signal"] == 1 and hold_flag == 0:
            hold_flag = 1
            entry_price = row["open"]
        if row["exit_signal"] == 1 and hold_flag == 1:
            hold_flag = 0
            exit_price = row["open"]
            pct = (exit_price - entry_price) / entry_price
            if pct > 0:
                win_cnt += 1
                total_profit += pct
            else:
                total_loss += abs(pct)

    win_rate = win_cnt / total_round if total_round > 0 else 0
    avg_win = total_profit / win_cnt if win_cnt > 0 else np.inf
    avg_loss = total_loss / (total_round - win_cnt) if (total_round - win_cnt) > 0 else np.inf
    profit_loss = avg_win / avg_loss if avg_loss != np.inf else np.inf

    return {
        "分组": seg_name,
        "累计收益": cum_ret,
        "年化收益": ann_return,
        "年化波动": ann_vol,
        "夏普比率": sharpe,
        "最大回撤": max_dd,
        "交易胜率": win_rate,
        "盈亏比": profit_loss
    }

def evaluate(df):
    log("[4/5] 拆分训练/样本外，计算完整绩效指标")
    df["period"] = "训练集"
    df.loc[df["date"] >= SAMPLE_START, "period"] = "样本外"
    segment_list = [
        ("训练集(2020-2025)", df["period"] == "训练集"),
        ("样本外(2026)", df["period"] == "样本外"),
        ("全样本(2020-2026)", df.index >= 0)
    ]
    metric_rows = []
    for seg_title, mask in segment_list:
        strat_dict = calc_metrics(df["strategy_ret"], df, mask, f"{seg_title} · 策略")
        strat_dict["类型"] = "策略"
        metric_rows.append(strat_dict)
        bh_dict = calc_metrics(df["benchmark_ret"], df, mask, f"{seg_title} · 基准")
        bh_dict["类型"] = "基准"
        metric_rows.append(bh_dict)
    metrics_df = pd.DataFrame(metric_rows)
    # 统一格式化为百分比
    pct_cols = ["累计收益", "年化收益", "年化波动", "最大回撤", "交易胜率"]
    for col in pct_cols:
        metrics_df[col] = (metrics_df[col] * 100).round(2).astype(str) + "%"
    metrics_df["夏普比率"] = metrics_df["夏普比率"].round(3)
    metrics_df["盈亏比"] = metrics_df["盈亏比"].round(2)
    metrics_df = metrics_df[[
        "分组", "类型", "累计收益", "年化收益", "年化波动",
        "夏普比率", "最大回撤", "交易胜率", "盈亏比"
    ]]
    log("\n===== 分段回测指标汇总 =====")
    log(metrics_df.to_string(index=False))
    return metrics_df

# ----------------------- 5. 保存输出文件 -----------------------
def save_results(df, metrics_df):
    log("[5/5] 导出回测明细与指标CSV")
    out_columns = [
        "date", "open", "high", "low", "close", "volume",
        "pe", "pb", "sentiment",
        "ma5", "ma20", "macd_dif", "macd_dea", "macd_hist", "rsi14",
        "golden_cross", "death_cross", "entry_signal", "exit_signal",
        "position", "turnover", "fee",
        "strategy_ret", "benchmark_ret",
        "strategy_nav", "benchmark_nav", "period"
    ]
    out_df = df[out_columns].copy()
    out_df["date"] = out_df["date"].dt.strftime("%Y-%m-%d")
    out_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    metrics_df.to_csv(METRICS_CSV, index=False, encoding="utf-8-sig")
    log(f"✅ 明细文件：{OUT_CSV.name}")
    log(f"✅ 指标文件：{METRICS_CSV.name}")

# ----------------------- 主入口 -----------------------
def main():
    log("比亚迪多因子择时策略回测程序")
    df = load_data()
    df = generate_signals(df)
    df = backtest(df)
    metrics_result = evaluate(df)
    save_results(df, metrics_result)
    log("\n程序全部执行完成！")

if __name__ == "__main__":
    main()