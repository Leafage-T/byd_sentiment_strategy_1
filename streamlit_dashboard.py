# -*- coding: utf-8 -*-
"""
streamlit_dashboard.py
================================================================
项目：比亚迪（002594）A股多因子择时研究
功能：
    1. 读取 backtest_result.csv，绘制 4 类图表：
       ① 策略净值 vs 基准净值曲线
       ② 股价均线、MACD、RSI 走势图
       ③ PE / PB 估值时序图
       ④ 每日舆情情感曲线 + 2026放大波动视图
    2. 表格展示训练集、样本外全套风险收益指标
    3. 本地运行：streamlit run streamlit_dashboard.py
================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# matplotlib 中文字体配置
import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# ----------------------- 字体配置 -----------------------
for fp in [
    "/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]:
    if Path(fp).exists():
        try:
            fm.fontManager.addfont(fp)
        except Exception:
            pass
plt.rcParams["font.sans-serif"] = ["Noto Sans SC", "DejaVu Sans", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ----------------------- 路径 -----------------------
HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "backtest_result.csv"
METRICS_PATH = HERE / "metrics_summary.csv"


# ----------------------- 数据加载 -----------------------
@st.cache_data(ttl=60)
def load_data():
    if not CSV_PATH.exists():
        return None, None
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    metrics = None
    if METRICS_PATH.exists():
        metrics = pd.read_csv(METRICS_PATH)
    return df, metrics


# ----------------------- 页面配置 -----------------------
st.set_page_config(
    page_title="比亚迪多因子择时 Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------- 侧边栏 -----------------------
st.sidebar.title("📊 比亚迪多因子择时")
st.sidebar.markdown("---")
st.sidebar.markdown("**项目信息**")
# 改为逐行换行显示，其余逻辑不变
st.sidebar.markdown("• 标的：比亚迪 002594")
st.sidebar.markdown("• 区间：2020-2026")
st.sidebar.markdown("• 策略：MA + MACD + RSI + 舆情")
st.sidebar.markdown("• 课程：财经数据分析")
st.sidebar.markdown("• 作者：王淑璐 · 赵梦婷")
st.sidebar.markdown("---")

df, metrics_df = load_data()

if df is None:
    st.error("未找到 backtest_result.csv，请先运行 strategy_backtest.py")
    st.stop()

# 时间范围筛选：默认截止2026-06-25
date_min, date_max = df["date"].min(), df["date"].max()
default_end = pd.Timestamp("2026-06-25").date()
sel_range = st.sidebar.date_input(
    "时间范围",
    value=(date_min.to_pydatetime().date(), default_end),
    min_value=date_min.to_pydatetime().date(),
    max_value=date_max.to_pydatetime().date(),
)
if isinstance(sel_range, tuple) and len(sel_range) == 2:
    mask = (df["date"].dt.date >= sel_range[0]) & (df["date"].dt.date <= sel_range[1])
    view = df[mask].copy()
else:
    view = df.copy()

# 过滤 2026-06-26 及以后日期，不再展示
view = view[view["date"] < pd.Timestamp("2026-06-26")].copy()

st.sidebar.markdown("---")
show_train = st.sidebar.checkbox("高亮训练集 / 样本外分界", value=True)


# ----------------------- 顶部 KPI -----------------------
st.title("📊 比亚迪 A 股多因子择时策略 Dashboard")
st.caption("MA5/MA20 + MACD + RSI14 + 舆情情感 复合信号 · 双边 0.05% 手续费 · 信号延后 1 日")

col1, col2, col3, col4 = st.columns(4)
last = view.iloc[-1]
col1.metric("最新收盘价", f"{last['close']:.2f}")
col2.metric("策略累计净值", f"{last['strategy_nav']:.3f}")
col3.metric("基准累计净值", f"{last['benchmark_nav']:.3f}")
col4.metric("超额净值", f"{last['strategy_nav'] - last['benchmark_nav']:.3f}")

st.markdown("---")


# ----------------------- 图 1：净值曲线 -----------------------
st.subheader("① 策略净值 vs 基准净值")
fig1, ax = plt.subplots(figsize=(11, 4.2), constrained_layout=True)
ax.plot(view["date"], view["strategy_nav"], label="策略净值",
        color="#C0392B", linewidth=1.8)
ax.plot(view["date"], view["benchmark_nav"], label="基准(买入持有)",
        color="#2E86C1", linewidth=1.4, alpha=0.85)
ax.fill_between(view["date"], view["strategy_nav"], view["benchmark_nav"],
                where=view["strategy_nav"] >= view["benchmark_nav"],
                color="#C0392B", alpha=0.10, label="超额为正")
ax.fill_between(view["date"], view["strategy_nav"], view["benchmark_nav"],
                where=view["strategy_nav"] < view["benchmark_nav"],
                color="#2E86C1", alpha=0.10, label="超额为负")
if show_train:
    split = pd.Timestamp("2025-12-31")
    if view["date"].min() <= split <= view["date"].max():
        ax.axvline(split, color="gray", linestyle="--", linewidth=1, alpha=0.7)
        ax.text(split, ax.get_ylim()[1] * 0.95, "  训练|样本外",
                fontsize=9, color="gray", va="top")
ax.set_xlabel("日期")
ax.set_ylabel("累计净值")
ax.set_title("策略净值 vs 基准净值")
ax.legend(loc="upper left", fontsize=9)
ax.grid(True, alpha=0.3)
st.pyplot(fig1)


# ----------------------- 图 2：技术指标 -----------------------
st.subheader("② 股价均线 / MACD / RSI 走势")
fig2, axes = plt.subplots(3, 1, figsize=(11, 8.5), constrained_layout=True,
                          sharex=True)

# 2-1 均线
ax = axes[0]
ax.plot(view["date"], view["close"], label="收盘价", color="#2C3E50", linewidth=1.2)
ax.plot(view["date"], view["ma5"], label="MA5", color="#E67E22", linewidth=1.0)
ax.plot(view["date"], view["ma20"], label="MA20", color="#27AE60", linewidth=1.0)
# 持仓区间高亮
pos = view["position"].values
in_pos = False
start_i = 0
for i in range(len(pos)):
    if pos[i] == 1 and not in_pos:
        in_pos = True
        start_i = i
    elif pos[i] == 0 and in_pos:
        in_pos = False
        ax.axvspan(view["date"].iloc[start_i], view["date"].iloc[i],
                   color="#F9E79F", alpha=0.35)
if in_pos:
    ax.axvspan(view["date"].iloc[start_i], view["date"].iloc[-1],
               color="#F9E79F", alpha=0.35)
ax.set_ylabel("价格 (元)")
ax.set_title("股价 + MA5 / MA20（黄色阴影 = 持仓区间）")
ax.legend(loc="upper left", fontsize=9, ncol=3)
ax.grid(True, alpha=0.3)

# 2-2 MACD
ax = axes[1]
ax.plot(view["date"], view["macd_dif"], label="DIF", color="#2980B9", linewidth=1.0)
ax.plot(view["date"], view["macd_dea"], label="DEA", color="#E74C3C", linewidth=1.0)
colors = ["#C0392B" if v >= 0 else "#27AE60" for v in view["macd_hist"]]
ax.bar(view["date"], view["macd_hist"], color=colors, width=1.0, alpha=0.6,
       label="MACD柱")
ax.axhline(0, color="gray", linewidth=0.6)
ax.set_ylabel("MACD")
ax.set_title("MACD 指标")
ax.legend(loc="upper left", fontsize=9, ncol=3)
ax.grid(True, alpha=0.3)

# 2-3 RSI
ax = axes[2]
ax.plot(view["date"], view["rsi14"], label="RSI14", color="#8E44AD", linewidth=1.1)
ax.axhline(75, color="#C0392B", linestyle="--", linewidth=0.8, label="超买 75")
ax.axhline(25, color="#27AE60", linestyle="--", linewidth=0.8, label="超卖 25")
ax.axhline(50, color="gray", linestyle=":", linewidth=0.6)
ax.fill_between(view["date"], 75, 100, color="#C0392B", alpha=0.08)
ax.fill_between(view["date"], 0, 25, color="#27AE60", alpha=0.08)
ax.set_ylabel("RSI")
ax.set_xlabel("日期")
ax.set_title("RSI 14")
ax.set_ylim(0, 100)
ax.legend(loc="upper left", fontsize=9, ncol=3)
ax.grid(True, alpha=0.3)

st.pyplot(fig2)


# ----------------------- 图 3：PE / PB 估值 -----------------------
st.subheader("③ PE / PB 估值时序")
fig3, ax_l = plt.subplots(figsize=(11, 4.0), constrained_layout=True)
ax_r = ax_l.twinx()

l1, = ax_l.plot(view["date"], view["pe"], color="#16A085",
                linewidth=1.4, label="PE (TTM)")
l2, = ax_r.plot(view["date"], view["pb"], color="#D35400",
                linewidth=1.4, label="PB")

# 分位数参考线
if len(view) > 30:
    pe_p50 = view["pe"].rolling(60, min_periods=10).median()
    ax_l.plot(view["date"], pe_p50, color="#16A085",
              linestyle="--", linewidth=0.8, alpha=0.6, label="PE 60日中位数")

ax_l.set_xlabel("日期")
ax_l.set_ylabel("PE (TTM)", color="#16A085")
ax_r.set_ylabel("PB", color="#D35400")
ax_l.tick_params(axis="y", labelcolor="#16A085")
ax_r.tick_params(axis="y", labelcolor="#D35400")
ax_l.set_title("比亚迪 PE / PB 估值时序")
lines = [l1, l2]
labels = [l.get_label() for l in lines]
ax_l.legend(lines, labels, loc="upper left", fontsize=9)
ax_l.grid(True, alpha=0.3)
st.pyplot(fig3)


# ----------------------- 图 4：舆情情感（全周期原图 + 2026放大图） -----------------------
st.subheader("④ 每日舆情情感曲线")
# 全周期原图
fig4, ax = plt.subplots(figsize=(11, 3.8), constrained_layout=True)
ax.plot(view["date"], view["sentiment"], color="#34495E",
        linewidth=0.9, alpha=0.55, label="日情感分")
# 20 日均线
if len(view) > 20:
    sent_ma = view["sentiment"].rolling(20, min_periods=5).mean()
    ax.plot(view["date"], sent_ma, color="#E74C3C",
            linewidth=1.8, label="情感 20 日均线")
ax.axhline(0.55, color="#C0392B", linestyle="--", linewidth=0.8,
           label="开仓阈值 0.55")
ax.axhline(0.5, color="gray", linestyle=":", linewidth=0.6, label="中性 0.5")
ax.fill_between(view["date"], 0.55, view["sentiment"],
                where=view["sentiment"] > 0.55,
                color="#C0392B", alpha=0.12)
ax.fill_between(view["date"], 0.5, view["sentiment"],
                where=view["sentiment"] < 0.5,
                color="#2E86C1", alpha=0.12)
ax.set_ylim(0, 1)
ax.set_xlabel("日期")
ax.set_ylabel("情感分 [0, 1]")
ax.set_title("财经新闻情感指数（SnowNLP）全周期视图")
ax.legend(loc="upper left", fontsize=9, ncol=4)
ax.grid(True, alpha=0.3)
st.pyplot(fig4)

# 新增：2026年放大波动视图
st.markdown("##### 2026年样本外舆情情感放大视图（波动区间）")
df_2026 = view[view["date"] >= pd.Timestamp("2026-01-01")].copy()
if len(df_2026) > 0:
    fig4_sub, ax_sub = plt.subplots(figsize=(11, 3.5), constrained_layout=True)
    ax_sub.plot(df_2026["date"], df_2026["sentiment"], color="#34495E",
                linewidth=1.0, alpha=0.6, label="日情感分")
    if len(df_2026) > 20:
        sent_ma_2026 = df_2026["sentiment"].rolling(20, min_periods=5).mean()
        ax_sub.plot(df_2026["date"], sent_ma_2026, color="#E74C3C",
                    linewidth=1.8, label="情感 20 日均线")
    ax_sub.axhline(0.55, color="#C0392B", linestyle="--", linewidth=0.8, label="开仓阈值 0.55")
    ax_sub.axhline(0.5, color="gray", linestyle=":", linewidth=0.6, label="中性 0.5")
    ax_sub.fill_between(df_2026["date"], 0.55, df_2026["sentiment"],
                        where=df_2026["sentiment"] > 0.55,
                        color="#C0392B", alpha=0.12)
    ax_sub.fill_between(df_2026["date"], 0.5, df_2026["sentiment"],
                        where=df_2026["sentiment"] < 0.5,
                        color="#2E86C1", alpha=0.12)
    ax_sub.set_ylim(0, 1)
    ax_sub.set_xlabel("日期")
    ax_sub.set_ylabel("情感分 [0, 1]")
    ax_sub.set_title("2026年舆情情感放大（新闻量充足，波动明显）")
    ax_sub.legend(loc="upper left", fontsize=9, ncol=4)
    ax_sub.grid(True, alpha=0.3)
    st.pyplot(fig4_sub)
else:
    st.info("当前筛选时间不含2026年，无放大视图可展示")


# ----------------------- 指标表格 -----------------------
st.markdown("---")
st.subheader("📋 风险收益指标汇总")
if metrics_df is not None:
    # 拆成训练集 / 样本外两张表
    train_df = metrics_df[metrics_df["分组"].str.contains("训练集")].copy()
    sample_df = metrics_df[metrics_df["分组"].str.contains("样本外")].copy()
    full_df = metrics_df[metrics_df["分组"].str.contains("全样本")].copy()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**训练集（2020-2025）**")
        st.dataframe(train_df, hide_index=True, use_container_width=True)
    with c2:
        st.markdown("**样本外（2026）**")
        st.dataframe(sample_df, hide_index=True, use_container_width=True)

    st.markdown("**全样本（2020-2026）**")
    st.dataframe(full_df, hide_index=True, use_container_width=True)
else:
    st.info("未找到 metrics_summary.csv，请先运行 strategy_backtest.py")


# ----------------------- 数据明细 -----------------------
st.markdown("---")
st.subheader("🔍 回测明细数据")
show_cols = st.multiselect(
    "选择展示列",
    options=view.columns.tolist(),
    default=["date", "close", "ma5", "ma20", "macd_hist", "rsi14",
             "sentiment", "position", "strategy_nav", "benchmark_nav"],
)
st.dataframe(view[show_cols], hide_index=True, use_container_width=True)

st.caption("© 财经数据分析课程设计 · 王淑璐 · 赵梦婷")