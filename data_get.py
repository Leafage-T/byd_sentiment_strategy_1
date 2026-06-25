# -*- coding: utf-8 -*-
"""
data_get.py
项目：比亚迪（002594）A股多因子择时研究 · 数据采集清洗
依赖安装：pip install akshare pandas numpy requests beautifulsoup4 snownlp
功能：
1. 采集2020-01-01~2026-06-30四类原始数据并导出CSV
2. 统一日期、清洗广告新闻、SnowNLP情感打分、停牌填充
3. 清洗数据存入SQLite三张数据表并建立日期索引
4. 合并行情/估值/舆情生成总因子表，计算MA5/MA20/MACD/RSI
"""
import os
import re
import time
import sqlite3
import datetime as dt
from pathlib import Path
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# ----------------------- 基础配置 -----------------------
VERBOSE = True  # 打印开关，False仅输出关键信息
STOCK_CODE = "002594"
SINA_SYMBOL = "sz002594"
STOCK_NAME = "比亚迪"
START_DATE = "20200101"
END_DATE = "20260630"
START_DATE_STD = "2020-01-01"
END_DATE_STD = "2026-06-30"

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "byd_stock.db"
RAW_DAILY_CSV = HERE / "raw_daily_quote.csv"
RAW_VALUATION_CSV = HERE / "raw_valuation.csv"
RAW_NEWS_EM_CSV = HERE / "raw_news_em.csv"
RAW_NEWS_SINA_CSV = HERE / "raw_news_sina.csv"
TOTAL_FACTOR_CSV = HERE / "total_factor_df.csv"

NEUTRAL_SENTIMENT = 0.5
# 广告、荐股无关关键词过滤
AD_KEYWORDS = [
    '广告', '推广', '赞助', '点击查看', '了解更多', '立即购买',
    '优惠券', '折扣', '限时', '秒杀', '包邮', '客服',
    '加微信', '扫码', '二维码', '免费领', '红包',
    '股票开户', '配资', '杠杆', '荐股', '牛股', '内幕',
    '代客理财', '稳赚', '包赚', '日赚', '月赚',
]

# ----------------------- 通用工具函数 -----------------------
def log(msg):
    """统一控制控制台输出"""
    if VERBOSE:
        print(msg)

def safe_request(url, headers, timeout=15):
    """容错请求，解决网页解析/超时/404报错"""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as err:
        log(f"请求异常跳过：{str(err)}")
        return None

def safe_date(s):
    """统一转为YYYY-MM-DD标准日期"""
    if pd.isna(s) or s == "" or s is None:
        return None
    if isinstance(s, (dt.date, dt.datetime)):
        return pd.Timestamp(s).strftime("%Y-%m-%d")
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y年%m月%d日"):
        try:
            return pd.Timestamp(dt.datetime.strptime(s, fmt)).strftime("%Y-%m-%d")
        except Exception:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    try:
        return pd.Timestamp(s).strftime("%Y-%m-%d")
    except Exception:
        return None

def is_ad_or_irrelevant(title):
    """过滤广告、短无效新闻"""
    if not title or len(str(title).strip()) < 4:
        return True
    title = str(title)
    for kw in AD_KEYWORDS:
        if kw in title:
            return True
    return False

def calc_ma(series, n):
    """简单移动平均"""
    return series.rolling(window=n, min_periods=n).mean()

def calc_ema(series, span):
    """指数移动平均"""
    return series.ewm(span=span, adjust=False).mean()

def calc_macd(close, fast=12, slow=26, signal=9):
    """MACD指标 DIF DEA HIST"""
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    dif = ema_fast - ema_slow
    dea = calc_ema(dif, signal)
    hist = (dif - dea) * 2
    return dif, dea, hist

def calc_rsi(close, period=14):
    """Wilder标准RSI14"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

# ============================================================
# 一、原始数据采集模块
# ============================================================
def fetch_raw_daily_quotes():
    log("[1/4] 采集日线行情")
    import akshare as ak
    df = ak.stock_zh_a_daily(symbol=SINA_SYMBOL, start_date=START_DATE, end_date=END_DATE, adjust="qfq")
    log(f"数据规模：{df.shape}")
    df.to_csv(RAW_DAILY_CSV, index=False, encoding="utf-8-sig")
    log(f"✅ 保存 {RAW_DAILY_CSV.name}")
    return df

def fetch_raw_valuation():
    log("[2/4] 采集PE/PB估值")
    import akshare as ak
    pe_df = ak.stock_zh_valuation_baidu(symbol=STOCK_CODE, indicator="市盈率(TTM)", period="全部")
    pb_df = ak.stock_zh_valuation_baidu(symbol=STOCK_CODE, indicator="市净率", period="全部")
    # 修复变量名错误
    log(f"PE:{pe_df.shape} PB:{pb_df.shape}")
    # 合并原始估值表
    pe_renamed = pe_df.rename(columns={c: f"pe_{c}" if c != "date" else c for c in pe_df.columns})
    pb_renamed = pb_df.rename(columns={c: f"pb_{c}" if c != "date" else c for c in pb_df.columns})
    raw_val = pe_renamed.merge(pb_renamed, on="date", how="outer")
    raw_val.to_csv(RAW_VALUATION_CSV, index=False, encoding="utf-8-sig")
    log(f"✅ 保存 {RAW_VALUATION_CSV.name}")
    return pe_df, pb_df

def fetch_raw_news_em():
    log("[3/4] 采集东方财富新闻")
    import akshare as ak
    all_news = []
    seen_titles = set()
    # 接口基础新闻
    try:
        df = ak.stock_news_em(symbol=STOCK_CODE)
        log(f"接口获取{len(df)}条")
        for _, row in df.iterrows():
            title = str(row.get("新闻标题", "")).strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                all_news.append({
                    "新闻标题": title, "新闻内容": row.get("新闻内容", ""),
                    "发布时间": row.get("发布时间", ""), "文章来源": row.get("文章来源", ""),
                    "新闻链接": row.get("新闻链接", "")
                })
    except Exception as e:
        log(f"接口获取失败：{e}")
    # API分页抓取
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://so.eastmoney.com/"}
    import urllib.parse as _up
    keyword = _up.quote("比亚迪")
    for page in range(1, 101):
        url = (
            f"https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{keyword}%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C%22sort%22%3A%22default%22%2C%22pageIndex%22%3A{page}%2C%22pageSize%22%3A10%2C%22preTag%22%3A%22%22%2C%22postTag%22%3A%22%22%7D%7D%7D"
        )
        resp = safe_request(url, headers)
        if not resp:
            continue
        m = re.search(r"jQuery\((.*)\)", resp.text)
        if not m:
            log(f"P{page}无返回数据，跳过")
            continue
        import json as _json
        data = _json.loads(m.group(1))
        articles = data.get("result", {}).get("cmsArticleWebOld", [])
        if not articles:
            break
        for a in articles:
            title = re.sub(r"<[^>]+>", "", str(a.get("title", "")).strip())
            if title and title not in seen_titles:
                seen_titles.add(title)
                all_news.append({
                    "新闻标题": title, "新闻内容": str(a.get("content", ""))[:200],
                    "发布时间": a.get("date", ""), "文章来源": a.get("source", ""),
                    "新闻链接": a.get("url", "")
                })
        if page % 20 == 0:
            log(f"P{page} 累计{len(all_news)}条")
        time.sleep(0.3)
    raw_df = pd.DataFrame(all_news)
    log(f"总新闻{raw_df.shape}")
    raw_df.to_csv(RAW_NEWS_EM_CSV, index=False, encoding="utf-8-sig")
    log(f"✅ 保存 {RAW_NEWS_EM_CSV.name}")
    return raw_df

def fetch_raw_news_sina():
    log("[4/4] 采集新浪新闻")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    all_news = []
    for page in range(1, 30):
        url = f"https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllNewsStock.php?symbol={SINA_SYMBOL}&Page={page}"
        resp = safe_request(url, headers)
        if not resp:
            continue
        if resp.status_code != 200:
            log(f"P{page}访问异常，跳过")
            continue
        resp.encoding = resp.apparent_encoding or "gb2312"
        soup = BeautifulSoup(resp.text, "html.parser")
        datelist = soup.find("div", class_="datelist")
        if not datelist:
            log(f"P{page}无新闻区块，跳过")
            continue
        links = datelist.find_all("a", href=True)
        page_count = 0
        for a in links:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if len(title) < 5:
                continue
            parent_text = a.parent.get_text() if a.parent else ""
            date_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", parent_text)
            pub_time = date_match.group(1) if date_match else ""
            all_news.append({"新闻标题": title, "发布时间": pub_time, "新闻链接": href})
            page_count += 1
        log(f"P{page} 获取{page_count}条")
        time.sleep(0.5)
    raw_df = pd.DataFrame(all_news)
    log(f"总新闻{raw_df.shape}")
    raw_df.to_csv(RAW_NEWS_SINA_CSV, index=False, encoding="utf-8-sig")
    log(f"✅ 保存 {RAW_NEWS_SINA_CSV.name}")
    return raw_df

# ============================================================
# 二、数据清洗模块
# ============================================================
def clean_daily_quotes(raw_df):
    log("  清洗日线")
    df = raw_df.copy()
    df["date"] = df["date"].apply(safe_date)
    df = df.dropna(subset=["date"])
    rename_map = {
        "open": "open", "high": "high", "low": "low", "close": "close",
        "volume": "volume", "amount": "amount",
        "outstanding_share": "outstanding_share", "turnover": "turnover",
    }
    df = df.rename(columns=rename_map)
    df = df[(df["date"] >= START_DATE_STD) & (df["date"] <= END_DATE_STD)]
    df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    # 补齐停牌交易日
    full_dates = pd.bdate_range(START_DATE_STD, END_DATE_STD).strftime("%Y-%m-%d")
    df = df.set_index("date").reindex(full_dates).rename_axis("date").reset_index()
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = df[col].ffill()
    if "volume" in df.columns:
        df["volume"] = df["volume"].fillna(0)
    if "amount" in df.columns:
        df["amount"] = df["amount"].fillna(0)
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    log(f"清洗后规模{df.shape} {df['date'].min()} ~ {df['date'].max()}")
    return df[["date", "open", "high", "low", "close", "volume"] + (["amount"] if "amount" in df.columns else [])]

def clean_valuation(pe_df, pb_df):
    log("  清洗估值")
    # PE处理
    pe = pe_df.copy()
    pe["date"] = pe["date"].apply(safe_date)
    pe = pe.dropna(subset=["date"])
    pe_val_col = [c for c in pe.columns if c not in ["date", "symbol", "name", "indicator"]][0]
    pe = pe[["date", pe_val_col]].rename(columns={pe_val_col: "pe"})
    pe = pe.groupby("date")["pe"].last().reset_index()
    # PB处理
    pb = pb_df.copy()
    pb["date"] = pb["date"].apply(safe_date)
    pb = pb.dropna(subset=["date"])
    pb_val_col = [c for c in pb.columns if c not in ["date", "symbol", "name", "indicator"]][0]
    pb = pb[["date", pb_val_col]].rename(columns={pb_val_col: "pb"})
    pb = pb.groupby("date")["pb"].last().reset_index()
    # 合并并过滤负估值（无金融意义）
    val = pe.merge(pb, on="date", how="outer").sort_values("date").reset_index(drop=True)
    val = val[(val["date"] >= START_DATE_STD) & (val["date"] <= END_DATE_STD)]
    val["pe"] = val["pe"].ffill().bfill()
    val["pb"] = val["pb"].ffill().bfill()
    val = val[(val["pe"] > 0) & (val["pb"] > 0)]
    log(f"清洗后规模{val.shape} {val['date'].min()} ~ {val['date'].max()}")
    return val

def clean_news_and_score(em_df, sina_df):
    log("  清洗新闻+情感打分")
    from snownlp import SnowNLP
    records = []
    for _, row in em_df.iterrows():
        t = str(row.get("新闻标题", "")).strip()
        records.append({"title": t, "pub_time": row.get("发布时间", ""), "source": "eastmoney"})
    for _, row in sina_df.iterrows():
        t = str(row.get("新闻标题", "")).strip()
        records.append({"title": t, "pub_time": row.get("发布时间", ""), "source": "sina"})
    news = pd.DataFrame(records)
    log(f"合并新闻{len(news)}条")
    before = len(news)
    news = news[~news["title"].apply(is_ad_or_irrelevant)].reset_index(drop=True)
    log(f"过滤广告后{len(news)}条，剔除{before-len(news)}条")
    news["date"] = news["pub_time"].apply(safe_date)
    news = news.dropna(subset=["date"])
    news = news[(news["date"] >= START_DATE_STD) & (news["date"] <= END_DATE_STD)]
    # 情感打分
    sentiments = []
    for title in news["title"]:
        try:
            sentiments.append(SnowNLP(str(title)).sentiments)
        except:
            sentiments.append(NEUTRAL_SENTIMENT)
    news["sentiment"] = sentiments
    daily_sent = news.groupby("date")["sentiment"].mean().reset_index()
    log(f"有效情感交易日{len(daily_sent)}天")
    return daily_sent, news

def align_sentiment_to_trading_days(daily_sent, quotes):
    log("  情感对齐交易日")
    sent = quotes[["date"]].merge(daily_sent, on="date", how="left")
    sent["sentiment"] = sent["sentiment"].fillna(NEUTRAL_SENTIMENT)
    fill_cnt = (sent["sentiment"] == NEUTRAL_SENTIMENT).sum()
    log(f"中性填充天数{fill_cnt}")
    return sent

# ============================================================
# 三、入库 & 总因子表生成
# ============================================================
def save_to_sqlite(quotes, valuation, sentiment):
    log("[入库] 写入SQLite数据库")
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    try:
        quotes.to_sql("daily_quotes", conn, index=False, if_exists="replace")
        valuation.to_sql("valuation", conn, index=False, if_exists="replace")
        sentiment.to_sql("sentiment", conn, index=False)
        conn.execute("CREATE INDEX idx_quotes_date ON daily_quotes(date);")
        conn.execute("CREATE INDEX idx_valuation_date ON valuation(date);")
        conn.execute("CREATE INDEX idx_sentiment_date ON sentiment(date);")
        conn.commit()
        log("✅ 三张数据表写入完成")
    finally:
        conn.close()

def build_total_factor_and_indicators(quotes, valuation, sentiment):
    log("[总表] 合并因子+计算技术指标")
    df = quotes.merge(valuation, on="date", how="left").merge(sentiment, on="date", how="left")
    df["pe"] = df["pe"].ffill().bfill()
    df["pb"] = df["pb"].ffill().bfill()
    df["sentiment"] = df["sentiment"].fillna(NEUTRAL_SENTIMENT)
    df["ma5"] = calc_ma(df["close"], 5)
    df["ma20"] = calc_ma(df["close"], 20)
    df["macd_dif"], df["macd_dea"], df["macd_hist"] = calc_macd(df["close"])
    df["rsi14"] = calc_rsi(df["close"])
    df.to_csv(TOTAL_FACTOR_CSV, index=False, encoding="utf-8-sig")
    log(f"✅ 总表生成完毕，数据规模{df.shape}")
    return df

# ============================================================
# 主程序入口
# ============================================================
def main():
    log("===== 比亚迪数据采集清洗程序 =====")
    # 1 采集
    log("\n1. 开始采集数据")
    raw_daily = fetch_raw_daily_quotes()
    pe_df, pb_df = fetch_raw_valuation()
    raw_news_em = fetch_raw_news_em()
    raw_news_sina = fetch_raw_news_sina()
    # 2 清洗
    log("\n2. 数据清洗")
    quotes = clean_daily_quotes(raw_daily)
    valuation = clean_valuation(pe_df, pb_df)
    daily_sent, cleaned_news = clean_news_and_score(raw_news_em, raw_news_sina)
    sentiment = align_sentiment_to_trading_days(daily_sent, quotes)
    # 3 入库
    log("\n3. 存入SQLite")
    save_to_sqlite(quotes, valuation, sentiment)
    # 4 生成总因子表
    log("\n4. 生成总因子表")
    total_df = build_total_factor_and_indicators(quotes, valuation, sentiment)
    # 极简输出文件汇总
    log("\n===== 全部执行完成，输出文件 =====")
    output_list = [
        ("raw_daily_quote.csv", raw_daily.shape),
        ("raw_valuation.csv", f"{pe_df.shape}+{pb_df.shape}"),
        ("raw_news_em.csv", raw_news_em.shape),
        ("raw_news_sina.csv", raw_news_sina.shape),
        ("byd_stock.db", "数据库(3表+索引)"),
        ("total_factor_df.csv", total_df.shape)
    ]
    for name, info in output_list:
        log(f"- {name} | {info}")
    log("配套代码：data_get.py、strategy_backtest.py")

if __name__ == "__main__":
    main()