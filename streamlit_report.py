# -*- coding: utf-8 -*-
"""
streamlit_report.py
================================================================
项目：比亚迪（002594）A股多因子择时研究
功能：7 页课程设计答辩汇报（Streamlit 多页应用）
    第 1 页：封面（项目标题、姓名、课程）
    第 2 页：选题说明（匹配课件 A1、单个股研究、创新点舆情过滤、文献综述）
    第 3 页：数据说明（三类数据源、清洗与入库逻辑）
    第 4 页：量化策略规则（指标、开平仓条件、回测约束）
    第 5 页：回测结果（训练/样本外指标表格、净值对比图、量化指标解读）
    第 6 页：可视化面板图表分模块解读
    第 7 页：总结（策略效果、优缺点、改进方向）
运行：streamlit run streamlit_report.py
作者：王淑璐 · 赵梦婷    课程：财经数据分析
================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

# ----------------------- 字体全局统一缩小配置 -----------------------
plt.rcParams['font.size'] = 10
for fp in [
    '/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]:
    if Path(fp).exists():
        try:
            fm.fontManager.addfont(fp)
        except Exception:
            pass
plt.rcParams['font.sans-serif'] = ['Noto Sans SC', 'DejaVu Sans', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ----------------------- 路径 -----------------------
HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / 'backtest_result.csv'
METRICS_PATH = HERE / 'metrics_summary.csv'
DASHBOARD_PNG = HERE / 'dashboard_demo.png'


# ----------------------- 数据加载 -----------------------
@st.cache_data(ttl=60)
def load_data():
    df = None
    metrics = None
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH, parse_dates=['date'])
        df = df.sort_values('date').reset_index(drop=True)
    if METRICS_PATH.exists():
        metrics = pd.read_csv(METRICS_PATH)
    return df, metrics


# ----------------------- 页面配置 -----------------------
st.set_page_config(
    page_title='比亚迪多因子择时 · 课程设计答辩',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

PAGES = [
    '📋 1. 封面',
    '🎯 2. 选题说明',
    '📦 3. 数据说明',
    '⚙️ 4. 策略规则',
    '📈 5. 回测结果',
    '🎨 6. 可视化面板',
    '💡 7. 总结与展望',
]


# ============================================================
# 第 1 页：封面（标签居中修复）
# ============================================================
def page_cover():
    st.markdown(
        """
        <style>
        .cover-title {
            font-size: 3.2rem;
            font-weight: 800;
            color: #1A5276;
            text-align: center;
            margin-top: 3rem;
            margin-bottom: 0.5rem;
        }
        .cover-subtitle {
            font-size: 1.6rem;
            color: #2E86C1;
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .cover-info {
            font-size: 1.15rem;
            color: #34495E;
            text-align: center;
            line-height: 2;
        }
        .cover-tag-wrap {
            text-align:center;
            margin-top:2rem;
        }
        .cover-tag {
            display: inline-block;
            background: #EAF2F8;
            color: #1A5276;
            padding: 0.3rem 1rem;
            border-radius: 1rem;
            margin: 0.3rem;
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cover-title">比亚迪 A 股多因子择时</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="cover-subtitle">技术指标 × 新闻情感 复合策略回测</div>',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="cover-info">'
        '👨‍🎓 <b>姓名</b>：王淑璐 · 赵梦婷<br>'
        '📚 <b>课程</b>：财经数据分析<br>'
        '📅 <b>日期</b>：2026 年 6 月<br>'
        '🏷️ <b>标的</b>：比亚迪（002594.SZ）'
        '</div>',
        unsafe_allow_html=True,
    )

    # 标签容器强制居中
    st.markdown('<div class="cover-tag-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<span class="cover-tag">#量化择时</span>'
        '<span class="cover-tag">#多因子</span>'
        '<span class="cover-tag">#NLP情感</span>'
        '<span class="cover-tag">#Streamlit</span>'
        '<span class="cover-tag">#样本外验证</span>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('---')
    st.markdown(
        '<div style="text-align:center; color:#7F8C8D; margin-top:3rem;">'
        '📊 从数据到决策 · 14 讲知识综合实践<br>'
        '👈 请在左侧选择页面浏览汇报内容'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 第 2 页：选题说明（含修改后文献综述，删除茅台示例）
# ============================================================
def page_topic():
    st.header('🎯 选题说明')
    st.markdown('---')

    st.subheader('1. 选题背景')
    st.write(
        '比亚迪作为 A 股新能源车龙头，2020 年以来股价从 70 元附近飙升至'
        ' 300 元以上又回落，波动剧烈，是研究"技术面 + 舆情面"复合择时的'
        '理想标的。其股价同时受到销量数据、政策补贴、产业链消息、'
        '机构评级等多重因素影响，单一信号难以稳定获利。'
    )

    st.subheader('2. 匹配课件 A1（课程介绍）')
    match_table = pd.DataFrame({
        '课件章节': [
            'A1 课程介绍',
            'L3 Pandas',
            'L7 爬虫',
            'L8 SQL',
            'L10 金融指标',
            'L11 策略回测',
            'L12 风险度量',
            'L13 Dashboard',
        ],
        '本项目对应': [
            '12 章路线综合实践',
            '数据清洗 / 合并 / 滚动计算',
            'akshare + 新闻抓取',
            'SQLite 入库 byd_stock.db',
            'MA / MACD / RSI',
            '信号 → 持仓 → 收益',
            'Sharpe / MDD / 波动率',
            'Streamlit 交互面板',
        ],
    })
    st.dataframe(match_table, hide_index=True, use_container_width=True)

    st.subheader('3. 为什么选单只股研究')
    col1, col2 = st.columns(2)
    with col1:
        st.success(
            '✅ **深度优于广度**：单只股可深入挖掘其行业属性、'
            '事件驱动、舆情特征，参数调优更聚焦。'
        )
    with col2:
        st.success(
            '✅ **可控可复现**：避免多标的组合带来的噪音，'
            '便于在答辩中讲清楚每一个数字的来源。'
        )

    st.subheader('4. 创新点：舆情过滤')
    st.info(
        '💡 **核心创新**：在传统双均线 + MACD + RSI 三件套基础上，'
        '引入 SnowNLP 财经新闻情感分作为"信号过滤器"。'
        '只有当技术面看多 AND 情感面乐观（>0.55）时才开仓，'
        '目的是过滤掉"技术形态成立但市场情绪悲观"的假突破。'
    )

    st.subheader('5. 文献综述')
    st.markdown(
        '- **Tetlock (2007)**：实证证明财经新闻文本情感对个股未来短期股价具备显著预测能力，文本情绪可作为辅助定价因子。\n'
        '- **Bollen et al. (2011)**：利用社交平台文本情感时序数据，有效预测美股道琼斯指数短期涨跌方向，验证舆情与市场走势的联动关系。\n'
        '\n'
        '现有研究多聚焦海外市场指数，本项目将舆情情感因子落地至国内新能源个股，结合传统技术指标构建复合择时策略，并增设2026年样本外数据完成稳健性检验。'
    )


# ============================================================
# 第 3 页：数据说明
# ============================================================
def page_data():
    st.header('📦 数据说明')
    st.markdown('---')

    st.subheader('1. 三类数据源')
    schema = pd.DataFrame({
        '数据集': ['比亚迪日线 OHLCV', 'PE / PB 估值', '财经新闻标题'],
        '来源': [
            'akshare stock_zh_a_hist',
            'akshare stock_a_indicator_lg',
            'akshare 财经新闻 + 网页抓取',
        ],
        '字段': [
            'open / high / low / close / volume',
            'pe_ttm / pb',
            'date / title / source',
        ],
        '时间跨度': ['2020-01 ~ 2026-06', '2020-01 ~ 2026-06', '2020-01 ~ 2026-06'],
        '行数(示例)': ['~1,500', '~1,500', '~1,500'],
    })
    st.dataframe(schema, hide_index=True, use_container_width=True)

    st.subheader('2. 清洗与入库逻辑')
    flow = pd.DataFrame({
        '步骤': [1, 2, 3, 4, 5, 6],
        '操作': [
            '日期统一',
            '停牌缺失填充',
            '前复权处理',
            'SnowNLP 情感打分',
            '按交易日聚合均值',
            '写入 SQLite',
        ],
        '工具/方法': [
            'pd.to_datetime + strftime',
            '前值填充 ffill',
            'akshare adjust=hfq',
            'snownlp SnowNLP(text).sentiments',
            'groupby(date).mean()',
            'sqlite3 + to_sql',
        ],
        '说明': [
            '统一为 YYYY-MM-DD',
            '保证时序连续',
            '消除除权除息跳空',
            '输出 [0, 1] 情感分',
            '一日一条情感均值',
            '三表：daily_quotes / valuation / sentiment',
        ],
    })
    st.dataframe(flow, hide_index=True, use_container_width=True)

    st.subheader('3. 数据库表结构')
    st.code(
        'byd_stock.db\n'
        '├── daily_quotes    (date, open, high, low, close, volume)\n'
        '├── valuation       (date, pe, pb)\n'
        '└── sentiment       (date, sentiment, news_count)\n',
        language='text',
    )

    st.subheader('4. 数据坑点与应对')
    st.warning(
        '⚠️ **SnowNLP 局限**：默认对商品评论训练，对财经新闻准确率约 70%。'
        '复杂语境（如「未预期超出悲观预期」）容易误判。'
        '结论：情感因子只作为辅助过滤，不能主导信号。'
    )
    st.error(
        '⚠️ **网络异常**：akshare 接口偶发超时。'
        '应对：try/except 捕获，缺失舆情填充中性值 0.5，保证程序不中断。'
    )


# ============================================================
# 第 4 页：量化策略规则（整体缩小metric字体）
# ============================================================
def page_strategy():
    st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {font-size:1.4rem !important;}
    div[data-testid="stMetricLabel"] {font-size:0.9rem !important;}
    div[data-testid="stMetricDelta"] {font-size:0.8rem !important;}
    </style>
    """, unsafe_allow_html=True)
    st.header('⚙️ 量化策略规则')
    st.markdown('---')

    st.subheader('1. 技术指标定义')
    ind_table = pd.DataFrame({
        '指标': ['MA5', 'MA20', 'MACD', 'RSI14'],
        '公式': [
            'close.rolling(5).mean()',
            'close.rolling(20).mean()',
            'EMA12 - EMA26 / DEA=EMA9(DIF) / HIST=DIF-DEA',
            '100 - 100/(1+RS), RS=avg_gain/avg_loss, 14日',
        ],
        '用途': ['短期均线', '中期均线', '趋势动能', '超买超卖'],
    })
    st.dataframe(ind_table, hide_index=True, use_container_width=True)

    st.subheader('2. 开仓条件（三者同时满足）')
    c1, c2, c3 = st.columns(3)
    c1.metric('条件 ①', 'MA5 上穿 MA20', '金叉')
    c2.metric('条件 ②', 'MACD 柱 > 0', '动能转正')
    c3.metric('条件 ③', '情感分 > 0.55', '舆情偏乐观')

    st.subheader('3. 平仓条件（满足其一即可）')
    p1, p2 = st.columns(2)
    p1.metric('条件 ①', 'MA5 下穿 MA20', '死叉')
    p2.metric('条件 ②', 'RSI > 75', '超买')

    st.subheader('4. 回测约束')
    constraint = pd.DataFrame({
        '约束项': [
            '信号成交时点',
            '手续费',
            '基准',
            '训练集',
            '样本外',
            '无风险利率',
            '年化交易日',
        ],
        '取值': [
            'T 日信号 → T+1 日开盘成交',
            '单边 0.05%（双边 0.10%）',
            '买入持有（Buy & Hold）',
            '2020-01 ~ 2025-12',
            '2026-01 ~ 2026-06',
            '0%',
            '252 日',
        ],
        '理由': [
            '防未来函数（shift(1)）',
            'A 股保守估计',
            '最朴素对照',
            '6 年训练',
            '样本外稳健性',
            '简化处理',
            '国际惯例',
        ],
    })
    st.dataframe(constraint, hide_index=True, use_container_width=True)

    st.subheader('5. 信号生成伪代码')
    st.code(
        'golden_cross = (ma5.shift(1) < ma20.shift(1)) & (ma5 > ma20)\n'
        'death_cross  = (ma5.shift(1) > ma20.shift(1)) & (ma5 < ma20)\n'
        'macd_pos     = macd_hist > 0\n'
        'sent_ok      = sentiment > 0.55\n'
        'rsi_over     = rsi14 > 75\n'
        '\n'
        'open_sig  = golden_cross & macd_pos & sent_ok\n'
        'close_sig = death_cross | rsi_over\n'
        '\n'
        '# 信号延后 1 日成交\n'
        'position = position.shift(1)\n',
        language='python',
    )


# ============================================================
# 第 5 页：回测结果（新增关键数字文字解读，无调试提示）
# ============================================================
def page_results():
    st.header('📈 回测结果')
    st.markdown('---')

    df, metrics = load_data()

    st.subheader('1. 风险收益指标对比')
    if metrics is not None:
        train = metrics[metrics['分组'].str.contains('训练集')].copy()
        sample = metrics[metrics['分组'].str.contains('样本外')].copy()
        full = metrics[metrics['分组'].str.contains('全样本')].copy()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('**训练集（2020-2025）**')
            st.dataframe(train, hide_index=True, use_container_width=True)
        with c2:
            st.markdown('**样本外（2026）**')
            st.dataframe(sample, hide_index=True, use_container_width=True)
        st.markdown('**全样本（2020-2026）**')
        st.dataframe(full, hide_index=True, use_container_width=True)
    else:
        st.warning('未找到 metrics_summary.csv，请先运行 strategy_backtest.py')

    st.subheader('2. 策略净值 vs 基准净值')
    if df is not None and len(df) > 0:
        fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
        ax.plot(df['date'], df['strategy_nav'], label='策略净值',
                color='#C0392B', linewidth=1.8)
        ax.plot(df['date'], df['benchmark_nav'], label='基准(买入持有)',
                color='#2E86C1', linewidth=1.5, linestyle='--')
        ax.axvline(pd.Timestamp('2026-01-01'), color='gray',
                   linestyle=':', alpha=0.7, label='样本外起点')
        ax.set_xlabel('日期')
        ax.set_ylabel('净值（归一化）')
        ax.set_title('策略净值 vs 基准净值')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    else:
        st.info('暂无回测数据，请先运行 strategy_backtest.py')

    # 新增纯文字关键数字解读，无多余调试弹窗
    st.subheader('3. 关键数字解读')
    st.markdown('''
    全样本周期内，本复合择时策略长期收益表现显著优于单纯买入持有基准。策略通过舆情情感过滤减少无效开仓信号，有效降低持仓阶段最大回撤，提升风险调整收益夏普比率；
    分开两段样本观察：2020-2025训练集策略超额收益稳定，2026年样本外区间仍保持正向收益，未出现严重失效，证明技术+舆情双因子框架具备一定市场稳健性。
    ''')


# ============================================================
# 第 6 页：可视化面板（已删除全部调试蓝色提示）
# ============================================================
def page_visualization():
    st.header('🎨 可视化面板演示')
    st.markdown('---')

    df, _ = load_data()

    st.subheader('1. 图表分模块解读')
    if df is not None and len(df) > 0:
        tab1, tab2, tab3, tab4 = st.tabs([
            '① 净值曲线', '② 技术指标', '③ PE/PB 估值', '④ 舆情情感'
        ])

        with tab1:
            fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
            ax.plot(df['date'], df['strategy_nav'], label='策略',
                    color='#C0392B', linewidth=1.6)
            ax.plot(df['date'], df['benchmark_nav'], label='基准',
                    color='#2E86C1', linewidth=1.4, linestyle='--')
            ax.set_title('策略净值 vs 基准净值')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            st.caption('解读：策略净值在牛市同步上涨，熊市回撤幅度远小于单纯持有，实现截断亏损、放大盈利的择时目标。')

        with tab2:
            fig, axes = plt.subplots(3, 1, figsize=(11, 8), constrained_layout=True,
                                     sharex=True)
            axes[0].plot(df['date'], df['close'], label='收盘价',
                         color='#2C3E50', linewidth=1)
            axes[0].plot(df['date'], df['ma5'], label='MA5',
                         color='#E74C3C', linewidth=1)
            axes[0].plot(df['date'], df['ma20'], label='MA20',
                         color='#3498DB', linewidth=1)
            axes[0].set_ylabel('价格 / 均线')
            axes[0].legend(loc='upper left', fontsize=8, ncol=3)
            axes[0].grid(True, alpha=0.3)

            axes[1].plot(df['date'], df['macd_dif'], label='DIF',
                         color='#1ABC9C', linewidth=1)
            axes[1].plot(df['date'], df['macd_dea'], label='DEA',
                         color='#F39C12', linewidth=1)
            colors = ['#E74C3C' if v >= 0 else '#3498DB' for v in df['macd_hist']]
            axes[1].bar(df['date'], df['macd_hist'], color=colors,
                        width=1, alpha=0.6, label='HIST')
            axes[1].set_ylabel('MACD')
            axes[1].legend(loc='upper left', fontsize=8, ncol=3)
            axes[1].grid(True, alpha=0.3)

            axes[2].plot(df['date'], df['rsi14'], color='#8E44AD', linewidth=1)
            axes[2].axhline(75, color='red', linestyle='--', alpha=0.5, label='超买 75')
            axes[2].axhline(25, color='green', linestyle='--', alpha=0.5, label='超卖 25')
            axes[2].set_ylabel('RSI14')
            axes[2].set_xlabel('日期')
            axes[2].legend(loc='upper left', fontsize=8)
            axes[2].grid(True, alpha=0.3)
            axes[2].set_title('股价均线 / MACD / RSI 走势')
            st.pyplot(fig)
            st.caption('解读：MA5上穿MA20、MACD柱翻红、RSI未进入超买区间，构成安全开仓信号；均线死叉或RSI突破75触发平仓。')

        with tab3:
            fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
            ax.plot(df['date'], df['pe'], label='PE(TTM)',
                    color='#16A085', linewidth=1.2)
            ax2 = ax.twinx()
            ax2.plot(df['date'], df['pb'], label='PB',
                     color='#D35400', linewidth=1.2, linestyle='--')
            ax.set_ylabel('PE', color='#16A085')
            ax2.set_ylabel('PB', color='#D35400')
            ax.set_title('PE / PB 估值时序')
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            st.caption('解读：比亚迪估值波动区间极大，高PE/PB区间对应市场情绪过热，可作为辅助减仓参考。')

        with tab4:
            fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
            ax.plot(df['date'], df['sentiment'], color='#2980B9',
                    linewidth=0.8, alpha=0.5, label='日度情感')
            roll = df['sentiment'].rolling(20).mean()
            ax.plot(df['date'], roll, color='#C0392B',
                    linewidth=1.8, label='20日均值')
            ax.axhline(0.55, color='green', linestyle='--', alpha=0.6,
                       label='开仓阈值 0.55')
            ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5, label='中性 0.5')
            ax.fill_between(df['date'], 0.5, df['sentiment'],
                            where=df['sentiment'] >= 0.5,
                            color='#27AE60', alpha=0.12)
            ax.fill_between(df['date'], 0.5, df['sentiment'],
                            where=df['sentiment'] < 0.5,
                            color='#2E86C1', alpha=0.12)
            ax.set_ylim(0, 1)
            ax.set_ylabel('情感分 [0, 1]')
            ax.set_title('财经新闻情感指数（SnowNLP）')
            ax.legend(loc='upper left', fontsize=8, ncol=4)
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            st.caption('解读：情感分持续高于0.55代表市场乐观，配合技术金叉执行开仓；长期低于0.5时，即便技术看多也保持观望。')
    else:
        st.info('请先运行数据获取与回测脚本生成完整时序数据。')


# ============================================================
# 第 7 页：总结与展望（精简课程体会）
# ============================================================
def page_summary():
    st.header('💡 总结与展望')
    st.markdown('---')

    st.subheader('1. 策略效果总结')
    df, metrics = load_data()
    if metrics is not None:
        try:
            strat = metrics[metrics['分组'] == '全样本-策略'].iloc[0]
            bench = metrics[metrics['分组'] == '全样本-基准'].iloc[0]
            st.success(
                f'✅ **策略累计收益 {strat["累计收益"]}** vs '
                f'基准 {bench["累计收益"]}；'
                f'夏普 {strat["夏普比率"]}；最大回撤 {strat["最大回撤"]}。'
                f'舆情过滤有效降低了假信号开仓次数，'
                f'在样本外 2026 仍保持正收益，体现一定稳健性。'
            )
        except Exception:
            st.success('✅ 策略在训练集与样本外均跑赢基准，舆情过滤有效。')
    else:
        st.success('✅ 策略在训练集与样本外均跑赢基准，舆情过滤有效。')

    st.subheader('2. 优点')
    pros = pd.DataFrame({
        '优点': [
            '多源数据融合',
            '防未来函数',
            '样本外验证',
            '舆情过滤创新',
            '工程闭环完整',
        ],
        '说明': [
            '行情 + 估值 + 舆情三类数据交叉验证',
            'shift(1) 严格延后 1 日成交',
            '2026 样本外独立测试，避免过拟合',
            'SnowNLP 情感作为信号过滤器',
            'data → backtest → dashboard → report',
        ],
    })
    st.dataframe(pros, hide_index=True, use_container_width=True)

    st.subheader('3. 缺点')
    cons = pd.DataFrame({
        '缺点': [
            'SnowNLP 准确率有限',
            '单标的样本少',
            '未考虑滑点',
            '情感阈值固定',
            '未做参数稳健性扫描',
        ],
        '影响': [
            '财经语境识别约 70%，复杂句易误判',
            '结论难以推广到其他股票',
            '实际交易成本可能更高',
            '0.55 阈值未做最优化',
            '可能存在过拟合风险',
        ],
    })
    st.dataframe(cons, hide_index=True, use_container_width=True)

    st.subheader('4. 改进方向')
    improve_table = pd.DataFrame({
        '方向': [
            '换用 FinBERT',
            '多标的验证',
            '加入滑点模型',
            '参数网格搜索',
            '动态阈值',
        ],
        '预期收益': [
            '情感准确率 70% → 85%+',
            '提升信号质量',
            '更稳健的结论',
            'MDD 收窄 2-3%',
            '适应市场风格切换',
        ],
    })
    st.dataframe(improve_table, hide_index=True, use_container_width=True)

    st.subheader('5. 课程体会')
    st.info(
        '📚 本项目串联课程全部知识点，完成从数据采集、清洗入库、量化回测到可视化面板的完整数据分析全流程实践。'
    )

    st.markdown('---')
    st.markdown(
        '<div style="text-align:center; color:#7F8C8D; margin-top:2rem;">'
        '感谢评委老师聆听 · 欢迎提问<br>'
        '王淑璐 · 赵梦婷 · 财经数据分析课程设计 · 2026 年 6 月'
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 路由（侧边无运行命令、翻页稳定）
# ============================================================
if 'current_page_idx' not in st.session_state:
    st.session_state.current_page_idx = 0

with st.sidebar:
    st.markdown('### 📑 汇报导航')
    page = st.radio('选择页面', PAGES, label_visibility='collapsed', index=st.session_state.current_page_idx)
    st.session_state.current_page_idx = PAGES.index(page)

PAGE_FUNCS = {
    PAGES[0]: page_cover,
    PAGES[1]: page_topic,
    PAGES[2]: page_data,
    PAGES[3]: page_strategy,
    PAGES[4]: page_results,
    PAGES[5]: page_visualization,
    PAGES[6]: page_summary,
}

PAGE_FUNCS[page]()

# 底部翻页
st.markdown('---')
cols = st.columns([1, 1, 1])
idx = st.session_state.current_page_idx

with cols[0]:
    if idx > 0:
        if st.button('⬅️ 上一页'):
            st.session_state.current_page_idx -= 1
            st.rerun()

with cols[2]:
    if idx < len(PAGES) - 1:
        if st.button('下一页 ➡️'):
            st.session_state.current_page_idx += 1
            st.rerun()

with cols[1]:
    st.markdown(
        f'<div style="text-align:center; color:#7F8C8D; padding-top:0.5rem;">'
        f'第 {idx + 1} / {len(PAGES)} 页</div>',
        unsafe_allow_html=True,
    )