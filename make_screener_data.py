#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상대강도 스크리너 — 데이터 수집 스크립트 (1단계)
  노션 종목명단 DB 읽기 → pykrx로 일봉 종가 수집 → data.json 생성

[처음 한 번 설치]
  pip install pykrx requests

[실행]
  1) 아래 SETTINGS의 NOTION_TOKEN, NOTION_DATA_SOURCE_ID 채우기 (또는 환경변수)
  2) python make_screener_data.py
  → 같은 폴더에 data.json 생성됨 (index.html이 읽음)

키는 코드에 직접 박지 말고 환경변수 권장 (PC→클라우드 이사 대비):
  Windows:  set NOTION_TOKEN=ntn_xxx
  Mac/Linux: export NOTION_TOKEN=ntn_xxx
"""
import os, json, sys
from datetime import datetime, timedelta

# ───────── SETTINGS ─────────
def _load_token():
    # 1순위: 환경변수, 2순위: 같은 폴더의 token.txt 파일
    t = os.environ.get("NOTION_TOKEN", "").strip()
    if t:
        return t
    here = os.path.dirname(os.path.abspath(__file__))
    tf = os.path.join(here, "token.txt")
    if os.path.exists(tf):
        with open(tf, encoding="utf-8") as f:
            return f.read().strip()
    return ""

NOTION_TOKEN = _load_token()                                # ← 환경변수 또는 token.txt
NOTION_DATA_SOURCE_ID = os.environ.get(
    "NOTION_DATA_SOURCE_ID",
    "636b315e-5cc4-4c3e-84c1-daeb5b585079"                 # ← 종목명단 DB의 data source id (이미 채워둠)
)
LOOKBACK_DAYS = 250          # 수집할 일수 (약 1년 거래일). 더 길게 보려면 키우기
OUTPUT = "data.json"
# 시장 → 지수 티커 (pykrx 지수코드: 코스피 1001, 코스닥 2001)
INDEX_CODE = {"코스피": "1001", "코스닥": "2001"}
INDEX_NAME = {"코스피": "코스피 지수", "코스닥": "코스닥 지수"}
# ────────────────────────────

# 지수 폴백: KRX 지수 엔드포인트가 막힐 때 사용 (수동 갱신). 날짜: (코스피, 코스닥)
INDEX_FALLBACK = {
"2026-06-16":(8726.60,1018.68),"2026-06-15":(8545.98,1034.03),"2026-06-12":(8123.62,1029.05),
"2026-06-11":(7763.95,996.93),"2026-06-10":(7730.82,951.63),"2026-06-09":(8096.93,967.81),
"2026-06-08":(7484.41,911.39),"2026-06-05":(8160.59,1002.44),"2026-06-04":(8639.41,1049.73),
"2026-06-02":(8801.49,1026.03),"2026-06-01":(8788.38,1050.03),"2026-05-29":(8476.15,1074.80),
"2026-05-28":(8185.29,1104.36),"2026-05-27":(8228.70,1133.13),"2026-05-26":(8047.51,1172.52),
"2026-05-22":(7847.71,1161.13),"2026-05-21":(7815.59,1105.97),"2026-05-20":(7208.95,1056.07),
"2026-05-19":(7271.66,1084.36),"2026-05-18":(7516.04,1111.09),"2026-05-15":(7632.40,1129.82),
"2026-05-14":(7481.50,1191.09),"2026-05-13":(7390.10,1176.93),"2026-05-12":(7552.30,1179.29),
"2026-05-11":(7680.15,1207.34),"2026-04-30":(6850.20,1225.40),"2026-04-29":(6710.80,1210.15),
"2026-04-28":(6745.50,1205.60),"2026-04-27":(6690.30,1195.40),"2026-04-24":(6712.00,1200.50),
"2026-04-23":(6685.20,1185.30),"2026-04-22":(6590.80,1172.10),"2026-04-21":(6520.40,1165.80),
"2026-04-20":(6435.10,1180.20),"2026-04-17":(6490.50,1192.40),"2026-04-16":(6410.20,1175.60),
"2026-04-15":(6450.80,1162.30),"2026-04-14":(6320.15,1185.90),"2026-04-13":(6150.40,1152.40),
"2026-04-10":(6290.70,1170.15),"2026-04-09":(6250.30,1184.20),"2026-04-08":(6380.10,1190.50),
"2026-04-07":(6120.45,1165.30),"2026-04-06":(5950.20,1138.40),"2026-04-03":(5820.50,1150.10),
"2026-04-02":(5940.80,1182.60),"2026-04-01":(5720.10,1195.40),"2026-03-31":(5590.40,1170.80),
"2026-03-30":(5610.25,1192.30),"2026-03-27":(5635.80,1160.50),"2026-03-26":(5850.10,1198.40),
"2026-03-25":(5980.40,1215.20),"2026-03-24":(6020.15,1202.60),"2026-03-23":(5910.30,1180.45),
"2026-03-20":(6130.50,1235.10),"2026-03-19":(6080.20,1220.40),"2026-03-18":(6110.45,1248.60),
"2026-03-17":(6050.10,1225.30),"2026-03-16":(5780.40,1192.50),
}
INDEX_COL = {"코스피": 0, "코스닥": 1}  # 폴백 튜플 인덱스



def fetch_universe_from_notion():
    """노션 종목명단 DB에서 사용=체크된 종목들을 읽어온다."""
    import requests
    url = f"https://api.notion.com/v1/data_sources/{NOTION_DATA_SOURCE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2025-09-03",
        "Content-Type": "application/json",
    }
    items, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        for pg in data.get("results", []):
            p = pg["properties"]
            def txt(prop):
                v = p.get(prop, {})
                if v.get("type") == "title":
                    return "".join(t["plain_text"] for t in v.get("title", []))
                if v.get("type") == "rich_text":
                    return "".join(t["plain_text"] for t in v.get("rich_text", []))
                if v.get("type") == "select":
                    return (v.get("select") or {}).get("name", "")
                if v.get("type") == "checkbox":
                    return v.get("checkbox", False)
                return ""
            if not txt("사용"):           # 사용=체크된 것만
                continue
            items.append({
                "ticker": txt("티커").strip(),
                "name":   txt("이름").strip(),
                "asset":  txt("자산종류").strip(),
                "market": txt("시장").strip(),
                "sector": txt("섹터").strip(),
            })
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return items


def fetch_index_naver(market, need_days=70):
    """네이버 금융에서 지수 일별 종가 수집. {YYYY-MM-DD: close}
       market: '코스피' -> KOSPI, '코스닥' -> KOSDAQ"""
    import requests, re, time
    code = {"코스피": "KOSPI", "코스닥": "KOSDAQ"}[market]
    headers = {"User-Agent": "Mozilla/5.0"}
    out = {}
    page = 1
    while len(out) < need_days and page <= 40:
        url = f"https://finance.naver.com/sise/sise_index_day.naver?code={code}&page={page}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
        except Exception as ex:
            print(f"     네이버 {code} p{page} 실패: {ex}")
            break
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", r.text, re.S)
        added = 0
        for row in rows:
            dm = re.search(r'class="date"[^>]*>\s*([\d.]+)', row)
            if not dm:
                continue
            date = dm.group(1).strip().rstrip(".").replace(".", "-")
            nums = re.findall(r'class="number_1"[^>]*>\s*([\d,]+\.?\d*)', row)
            if not nums:
                continue
            out[date] = float(nums[0].replace(",", ""))
            added += 1
        if added == 0:
            break
        page += 1
        time.sleep(0.3)
    return out


def _fetch_with_retry(fn, s, e, code, tries=5, wait=1.5):
    """KRX가 가끔 빈 응답을 줘서 재시도. 종가 컬럼 있는 df를 받을 때까지."""
    import time
    last = None
    for i in range(tries):
        try:
            df = fn(s, e, code)
            if df is not None and len(df) > 0 and "종가" in df.columns:
                return df
            last = "빈 응답"
        except Exception as ex:
            last = ex
        time.sleep(wait)
    raise RuntimeError(f"{tries}회 시도 실패: {last}")


def fetch_prices_pykrx(tickers, markets_needed):
    """pykrx로 종목·지수 일봉 종가 수집. {ticker: {YYYY-MM-DD: close}}"""
    from pykrx import stock
    end = datetime.today()
    start = end - timedelta(days=LOOKBACK_DAYS * 2)   # 거래일 여유분
    s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    prices = {}

    def to_series(df):
        out = {}
        for idx, row in df.iterrows():
            d = idx.strftime("%Y-%m-%d")
            out[d] = float(row["종가"])
        return out

    # 종목
    for t in tickers:
        try:
            df = _fetch_with_retry(stock.get_market_ohlcv, s, e, t)
            prices[t] = to_series(df)
            print(f"  ✓ {t}  ({len(prices[t])}일)")
        except Exception as ex:
            print(f"  ✗ {t}  수집 실패: {ex}")
    # 지수 — 네이버에서 수집 (pykrx 지수 엔드포인트가 막혀서)
    for mk in markets_needed:
        try:
            idx = fetch_index_naver(mk, need_days=LOOKBACK_DAYS)
            if idx:
                prices[mk] = idx
                print(f"  ✓ {INDEX_NAME[mk]}  ({len(idx)}일, 네이버)")
            else:
                raise RuntimeError("빈 응답")
        except Exception as ex:
            # 최후의 보루: 폴백
            col = INDEX_COL[mk]
            prices[mk] = {d: float(v[col]) for d, v in INDEX_FALLBACK.items()}
            print(f"  ⚠ {INDEX_NAME[mk]}  네이버 실패({ex}) → 폴백 사용 ({len(prices[mk])}일)")
    return prices


def build(universe, prices):
    markets = sorted({u["market"] for u in universe if u["asset"] == "주식"})
    market_map = {"코스피": "KOSPI", "코스닥": "KOSDAQ"}
    uni_out, bench_out = [], []
    for u in universe:
        uni_out.append({
            "ticker": u["ticker"], "name": u["name"],
            "asset": "stock" if u["asset"] == "주식" else "crypto",
            "market": market_map.get(u["market"], u["market"]),
            "sector": u["sector"],
        })
    price_out = {}
    for u in universe:
        if u["ticker"] in prices:
            price_out[u["ticker"]] = prices[u["ticker"]]
    for mk in markets:
        key = market_map.get(mk, mk)
        if mk in prices:
            price_out[key] = prices[mk]
            bench_out.append({"ticker": key, "name": INDEX_NAME[mk], "market": key})
    return {
        "meta": {"generated": datetime.today().strftime("%Y-%m-%d"), "source": "notion+pykrx"},
        "universe": uni_out, "benchmarks": bench_out, "prices": price_out,
    }


def main():
    if not NOTION_TOKEN:
        print("✗ NOTION_TOKEN이 비어있습니다. 환경변수로 설정하세요.")
        sys.exit(1)
    print("1) 노션에서 종목 명단 읽는 중…")
    universe = fetch_universe_from_notion()
    print(f"   → {len(universe)}종목: " + ", ".join(u["name"] for u in universe))
    if not universe:
        print("✗ 사용=체크된 종목이 없습니다."); sys.exit(1)
    markets_needed = sorted({u["market"] for u in universe if u["asset"] == "주식"})
    print("2) pykrx로 시세 수집 중…")
    prices = fetch_prices_pykrx([u["ticker"] for u in universe if u["asset"] == "주식"], markets_needed)
    print("3) data.json 생성 중…")
    data = build(universe, prices)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    pts = sum(len(v) for v in data["prices"].values())
    print(f"✓ 완료: {OUTPUT}  ({len(data['universe'])}종목, {pts}개 가격점)")


if __name__ == "__main__":
    main()
