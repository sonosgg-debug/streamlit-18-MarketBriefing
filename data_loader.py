"""
data_loader.py
한국(KRX) 및 미국(US) 시장 데이터 수집 및 정제 모듈
- 네이버 금융 모바일 API (한국 지수, 수급, 시총 상위)
- yfinance (미국 지수, 글로벌 거시 지표, 환율, 과거 추이 차트용 데이터)
"""

import io
import requests
import yfinance as yf
import pandas as pd
import concurrent.futures
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo


def get_now_kst():
    """한국 표준시(KST, UTC+9) 반환 (서버 OS 타임존 무관)"""
    try:
        return datetime.now(ZoneInfo('Asia/Seoul'))
    except Exception:
        return datetime.now(timezone(timedelta(hours=9)))

def get_now_ny():
    """미국 뉴욕 동부 표준시(ET) 반환 (서버 OS 타임존 무관)"""
    try:
        return datetime.now(ZoneInfo('America/New_York'))
    except Exception:
        # 서머타임 고려 기본 오프셋 fallback
        return datetime.now(timezone(timedelta(hours=-4)))

# 한국거래소(KRX) 정규 휴장일 및 법정 공휴일 (2024~2027)
KRX_HOLIDAYS = {
    # 2024
    '20240101', '20240209', '20240212', '20240301', '20240410', '20240501', '20240506',
    '20240515', '20240606', '20240815', '20240916', '20240917', '20240918', '20241001',
    '20241003', '20241009', '20241225', '20241231',
    # 2025
    '20250101', '20250128', '20250129', '20250130', '20250303', '20250501', '20250505',
    '20250506', '20250606', '20250815', '20251003', '20251006', '20251007', '20251008',
    '20251009', '20251225', '20251231',
    # 2026
    '20260101', '20260216', '20260217', '20260218', '20260302', '20260501', '20260505',
    '20260525', '20260603', '20260606', '20260817', '20260924', '20260925', '20261005',
    '20261009', '20261225', '20261231',
    # 2027
    '20270101', '20270208', '20270209', '20270210', '20270301', '20270503', '20270505',
    '20270513', '20270607', '20270816', '20270914', '20270915', '20270916', '20271004',
    '20271011', '20271225', '20271231'
}

_CACHED_TRADING_DAYS = None

def get_krx_trading_days(count=120):
    """
    한국거래소(KRX)의 실제 거래일(개장일) 목록을 반환합니다.
    1. 네이버 증시 API를 통해 실시간 실제 거래일 리스트를 우선 확보
    2. 실패 시 사전 정의된 휴장일 캘린더 및 주말 제외 알고리즘으로 폴백
    """
    global _CACHED_TRADING_DAYS
    if _CACHED_TRADING_DAYS is not None and len(_CACHED_TRADING_DAYS) >= count:
        return _CACHED_TRADING_DAYS
        
    days = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    pages_needed = (count + 59) // 60
    for page in range(1, pages_needed + 1):
        try:
            url = f'https://m.stock.naver.com/api/stock/005930/price?pageSize=60&page={page}'
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code == 200:
                items = r.json()
                if items:
                    days.extend([item['localTradedAt'].replace('-', '') for item in items])
                else:
                    break
        except Exception:
            pass
            
    if days:
        _CACHED_TRADING_DAYS = sorted(list(set(days)))
        return _CACHED_TRADING_DAYS
        
    fallback_days = []
    now_kst = get_now_kst()
    d = now_kst
    for _ in range(count * 3):
        d_str = d.strftime('%Y%m%d')
        if d.weekday() < 5 and d_str not in KRX_HOLIDAYS:
            fallback_days.append(d_str)
            if len(fallback_days) >= count:
                break
        d -= timedelta(days=1)
        
    _CACHED_TRADING_DAYS = sorted(fallback_days)
    return _CACHED_TRADING_DAYS

def is_krx_trading_day(date_str):
    """주어진 날짜(YYYYMMDD 또는 YYYY-MM-DD)가 실제 거래일인지 판별합니다."""
    clean_date = str(date_str).replace('-', '')
    trading_days = get_krx_trading_days(120)
    if clean_date in trading_days:
        return True
    try:
        dt = datetime.strptime(clean_date, "%Y%m%d")
        return (dt.weekday() < 5) and (clean_date not in KRX_HOLIDAYS)
    except:
        return False

def get_latest_completed_trading_day():
    """가장 최근에 완료된 실제 마감 거래일 YYYYMMDD 반환"""
    trading_days = get_krx_trading_days(120)
    now_kst = get_now_kst()
    today_str = now_kst.strftime('%Y%m%d')
    if now_kst.hour >= 16 and today_str in trading_days:
        return today_str
    prior_days = [d for d in trading_days if d < today_str]
    if prior_days:
        return prior_days[-1]
    return trading_days[-1] if trading_days else (now_kst - timedelta(days=1)).strftime('%Y%m%d')

def get_market_status(market='KRX'):
    """
    서버 환경(로컬 PC 또는 UTC 기반 클라우드 서버)에 관계없이
    항상 한국 표준시(KST) 및 뉴욕 표준시(ET)를 기준으로 실시간 장중 여부 정확히 판정
    """
    if market == 'KRX':
        now_kst = get_now_kst()
        weekday = now_kst.weekday() # 0:월 ~ 4:금, 5:토, 6:일
        today_str = now_kst.strftime('%Y%m%d')
        
        # 1. 주말 휴장 판정
        if weekday >= 5:
            latest_bday = get_latest_completed_trading_day()
            latest_fmt = f"{latest_bday[:4]}-{latest_bday[4:6]}-{latest_bday[6:]}"
            return {
                'status': 'WEEKEND',
                'label': f'🏖️ 주말 휴장 (직전 거래일 {latest_fmt} 종가 기준)',
                'badge': '⚪ 주말 휴장',
                'is_live': False,
                'title_suffix': '마감 종합 브리핑',
                'time_str': f"{latest_fmt} (직전 정규장 마감)",
                'closing_word': '마감',
                'current_time_str': now_kst.strftime('%H:%M:%S KST')
            }
            
        # 2. 평일 공휴일/휴장일 판정
        if not is_krx_trading_day(today_str):
            latest_bday = get_latest_completed_trading_day()
            latest_fmt = f"{latest_bday[:4]}-{latest_bday[4:6]}-{latest_bday[6:]}"
            return {
                'status': 'HOLIDAY',
                'label': f'🏖️ 공휴일/증시 휴장 (직전 거래일 {latest_fmt} 종가 기준)',
                'badge': '⚪ 공휴일 휴장',
                'is_live': False,
                'title_suffix': '휴장일 마켓 브리핑',
                'time_str': f"{latest_fmt} (직전 정규장 마감)",
                'closing_word': '마감',
                'current_time_str': now_kst.strftime('%H:%M:%S KST')
            }
        
        cur_time = now_kst.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        if market_open <= cur_time <= market_close:
            return {
                'status': 'LIVE',
                'label': '🟢 실시간 정규장 진행 중 (Live)',
                'badge': '🟢 실시간 장중',
                'is_live': True,
                'title_suffix': '실시간 마켓 브리핑',
                'time_str': f"{now_kst.strftime('%Y-%m-%d %H:%M')} (실시간 장중)",
                'closing_word': '진행 중',
                'current_time_str': now_kst.strftime('%H:%M:%S KST')
            }
        elif cur_time < market_open:
            return {
                'status': 'PRE_MARKET',
                'label': '⏳ 장 개장 전 (직전 거래일 종가 기준)',
                'badge': '⏳ 개장 전',
                'is_live': False,
                'title_suffix': '개장 전 브리핑 (전일 마감 기준)',
                'time_str': f"{now_kst.strftime('%Y-%m-%d')} (직전 정규장 마감)",
                'closing_word': '마감',
                'current_time_str': now_kst.strftime('%H:%M:%S KST')
            }
        else:
            return {
                'status': 'CLOSED',
                'label': '🏁 당일 정규장 마감 완료',
                'badge': '✅ 정규장 마감',
                'is_live': False,
                'title_suffix': '마감 종합 브리핑',
                'time_str': f"{now_kst.strftime('%Y-%m-%d')} (정규장 마감)",
                'closing_word': '마감',
                'current_time_str': now_kst.strftime('%H:%M:%S KST')
            }
            
    else: # US
        now_ny = get_now_ny()
        weekday = now_ny.weekday()
        if weekday >= 5:
            return {
                'status': 'WEEKEND',
                'label': '🏖️ 주말 휴장 (직전 뉴욕 종가 기준)',
                'badge': '⚪ 뉴욕 휴장',
                'is_live': False,
                'title_suffix': '마감 종합 브리핑',
                'time_str': f"{now_ny.strftime('%Y-%m-%d')} ET (직전 거래일 마감)",
                'closing_word': '마감',
                'current_time_str': now_ny.strftime('%H:%M:%S ET')
            }
            
        cur_time = now_ny.time()
        market_open = datetime.strptime("09:30", "%H:%M").time()
        market_close = datetime.strptime("16:00", "%H:%M").time()
        
        if market_open <= cur_time <= market_close:
            return {
                'status': 'LIVE',
                'label': '🟢 뉴욕 정규장 실시간 진행 중 (Live)',
                'badge': '🟢 실시간 장중',
                'is_live': True,
                'title_suffix': '실시간 마켓 브리핑',
                'time_str': f"{now_ny.strftime('%Y-%m-%d %H:%M')} ET (실시간 장중)",
                'closing_word': '진행 중',
                'current_time_str': now_ny.strftime('%H:%M:%S ET')
            }
        else:
            return {
                'status': 'CLOSED',
                'label': '🏁 뉴욕 정규장 마감 완료',
                'badge': '✅ 정규장 마감',
                'is_live': False,
                'title_suffix': '마감 종합 브리핑',
                'time_str': f"{now_ny.strftime('%Y-%m-%d')} ET (정규장 마감)",
                'closing_word': '마감',
                'current_time_str': now_ny.strftime('%H:%M:%S ET')
            }


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_float(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).replace(',', '').replace('%', '').strip()
    try:
        return float(val_str)
    except:
        return 0.0

def _parse_trend_content_item(item):
    """
    네이버 신규 REST API(trend/daily, trend/time)의 netAmounts 데이터를
    투자 주체별 순매매액(단위: 억원)으로 파싱
    """
    Y = {
        "8000": "personal",
        "9000": "foreign",
        "9999": "institutional",
        "1000": "financial_invest",
        "2000": "insurance",
        "3000": "investment_trust",
        "4000": "bank",
        "5000": "other_finance",
        "6000": "pension",
        "7100": "other_corp"
    }

    bizdate = str(item.get('bizdate', ''))
    date_short = f"{bizdate[2:4]}.{bizdate[4:6]}.{bizdate[6:8]}" if len(bizdate) == 8 else bizdate
    bizdate_fmt = f"{bizdate[4:6]}/{bizdate[6:8]}" if len(bizdate) == 8 else bizdate

    res = {
        'date': date_short,
        'bizdate': bizdate,
        'bizdate_fmt': bizdate_fmt,
        'time': str(item.get('time', '')),
        'personal': 0.0,
        'foreign': 0.0,
        'institutional': 0.0,
        'financial_invest': 0.0,
        'insurance': 0.0,
        'investment_trust': 0.0,
        'bank': 0.0,
        'other_finance': 0.0,
        'pension': 0.0,
        'other_corp': 0.0
    }

    for na in item.get('netAmounts', []):
        gubun = str(na.get('investorGubun', ''))
        val = float(na.get('diffValue', 0)) / 1e8  # 원 -> 억원 변환

        if gubun == "3100":
            res['investment_trust'] += val
        elif gubun == "9001":
            res['foreign'] += val
        elif gubun == "7000":
            res['pension'] += val
        elif gubun in Y:
            res[Y[gubun]] += val

    # 기관계 합계 계산
    res['institutional'] = (
        res['financial_invest'] +
        res['insurance'] +
        res['investment_trust'] +
        res['bank'] +
        res['other_finance'] +
        res['pension']
    )
    return res

def get_investor_trend_history(sosok='01'):
    """
    네이버 증권 공식 REST API를 활용하여 일자별 투자자 매매동향 및 직전 마감 확정 수치 반환
    sosok: '01' / 'KOSPI', '02' / 'KOSDAQ'
    """
    market_type = 'KOSPI' if str(sosok) in ['01', 'KOSPI'] else 'KOSDAQ'
    try:
        url = f'https://stock.naver.com/api/domestic/market/trend/daily?tradeType=KRX&marketType={market_type}&pageSize=10'
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            content = r.json().get('content', [])
            if content:
                rows = [_parse_trend_content_item(it) for it in content]

                df_data = []
                for row in rows:
                    df_data.append({
                        '날짜': row['date'],
                        '개인': round(row['personal'], 1),
                        '외국인': round(row['foreign'], 1),
                        '기관계': round(row['institutional'], 1),
                        '금융투자': round(row['financial_invest'], 1),
                        '보험': round(row['insurance'], 1),
                        '투신': round(row['investment_trust'], 1),
                        '은행': round(row['bank'], 1),
                        '기타금융': round(row['other_finance'], 1),
                        '연기금': round(row['pension'], 1),
                        '기타법인': round(row['other_corp'], 1)
                    })
                df = pd.DataFrame(df_data)

                # 직전 정규장 마감 행 추출
                now_kst = get_now_kst()
                today_str = now_kst.strftime('%Y%m%d')

                # 첫 번째 행이 오늘 날짜(장중 잠정)이면 두 번째 행이 직전 마감, 아니면 첫 번째 행이 직전 마감
                if rows[0]['bizdate'] == today_str and len(rows) > 1:
                    prev_row = rows[1]
                else:
                    prev_row = rows[0]

                prev_data = {
                    'date': prev_row['date'],
                    'bizdate': prev_row['bizdate'],
                    'bizdate_fmt': prev_row['bizdate_fmt'],
                    'personal': round(prev_row['personal'], 1),
                    'foreign': round(prev_row['foreign'], 1),
                    'institutional': round(prev_row['institutional'], 1),
                    'financial_invest': round(prev_row['financial_invest'], 1),
                    'insurance': round(prev_row['insurance'], 1),
                    'investment_trust': round(prev_row['investment_trust'], 1),
                    'bank': round(prev_row['bank'], 1),
                    'other_finance': round(prev_row['other_finance'], 1),
                    'pension': round(prev_row['pension'], 1),
                    'other_corp': round(prev_row['other_corp'], 1)
                }

                return {
                    'prev': prev_data,
                    'history': df.head(6)
                }
    except Exception as e:
        print(f"Error fetching investor trend history for {market_type}: {e}")

    return {'prev': {}, 'history': pd.DataFrame()}

def fetch_index_price(index_code):
    """네이버 모바일 API로 지수 정보 수집 (KOSPI, KOSDAQ)"""
    name = '코스피 (KOSPI)' if index_code == 'KOSPI' else '코스닥 (KOSDAQ)'
    try:
        res = requests.get(f'https://m.stock.naver.com/api/index/{index_code}/price', headers=HEADERS, timeout=4)
        if res.status_code == 200:
            item = res.json()[0]
            return {
                'name': name,
                'price': clean_float(item.get('closePrice')),
                'change': clean_float(item.get('compareToPreviousClosePrice')),
                'ratio': clean_float(item.get('fluctuationsRatio')),
                'direction': 'UP' if item.get('compareToPreviousPrice', {}).get('code') in ['2', '1'] else 'DOWN',
                'date': item.get('localTradedAt', '')
            }
    except Exception as e:
        print(f"Error fetching {index_code} price: {e}")
    return {'name': name, 'price': 0.0, 'change': 0.0, 'ratio': 0.0, 'direction': 'FLAT', 'date': ''}


def fetch_live_investor_trend(index_code, cur_m_status, today_str):
    """
    KOSPI / KOSDAQ 실시간 잠정 수급 수집
    - 개장 전(PRE_MARKET)이거나 bizdate가 오늘이 아닐 경우 0으로 자동 처리
    """
    inv_live = {'personal': 0.0, 'foreign': 0.0, 'institutional': 0.0, 'bizdate': today_str, 'is_today': False}
    try:
        res = requests.get(f'https://m.stock.naver.com/api/index/{index_code}/trend', headers=HEADERS, timeout=4)
        if res.status_code == 200:
            trend = res.json()
            bdate = str(trend.get('bizdate', ''))
            is_pre_market = cur_m_status.get('status') == 'PRE_MARKET'
            is_today = bool(bdate == today_str and not is_pre_market)
            
            if is_today:
                inv_live = {
                    'personal': clean_float(trend.get('personalValue', 0)),
                    'foreign': clean_float(trend.get('foreignValue', 0)),
                    'institutional': clean_float(trend.get('institutionalValue', 0)),
                    'bizdate': bdate,
                    'is_today': True
                }
            else:
                inv_live = {
                    'personal': 0.0,
                    'foreign': 0.0,
                    'institutional': 0.0,
                    'bizdate': bdate if bdate else today_str,
                    'is_today': False
                }
    except Exception as e:
        print(f"Error fetching {index_code} trend: {e}")
    return inv_live


def fetch_program_trading(cur_m_status, today_str):
    """KOSPI 프로그램 매매 수집"""
    default_prog = {
        'name': '프로그램 비차익 순매매',
        'non_arbitrage': 0.0,
        'arbitrage': 0.0,
        'total': 0.0,
        'bizdate': '',
        'bizdate_fmt': '',
        'time_str': '',
        'is_live': False
    }
    try:
        # 1) 실시간 장중(TIME) 데이터 우선 호출
        res_prog = requests.get(
            'https://stock.naver.com/api/domestic/market/trendProgram',
            params={'tradeType': 'KRX', 'krxMarketType': 'KOSPI', 'bizdate': today_str, 'startIdx': '1', 'pageSize': '1', 'periodType': 'TIME'},
            headers=HEADERS,
            timeout=4
        )
        content = []
        is_time_type = False
        if res_prog.status_code == 200:
            content = res_prog.json().get('content', [])
            if content:
                is_time_type = True

        # 2) TIME 데이터가 없으면 일자별(DAY) 데이터 폴백
        if not content:
            res_prog = requests.get(
                'https://stock.naver.com/api/domestic/market/trendProgram',
                params={'tradeType': 'KRX', 'krxMarketType': 'KOSPI', 'bizdate': today_str, 'startIdx': '1', 'pageSize': '1', 'periodType': 'DAY'},
                headers=HEADERS,
                timeout=4
            )
            if res_prog.status_code == 200:
                content = res_prog.json().get('content', [])

        if content:
            latest = content[0]
            bi_diff = clean_float(latest.get('biDiffPureBuyAmt', 0)) / 100000000.0
            diff = clean_float(latest.get('diffPureBuyAmt', 0)) / 100000000.0
            tot_diff = clean_float(latest.get('totalDiffPureBuyAmt', 0)) / 100000000.0
            b_date = str(latest.get('bizdate', ''))
            t_val = str(latest.get('time', ''))
            time_fmt = f"{t_val[:2]}:{t_val[2:4]}" if len(t_val) >= 4 else ""
            date_fmt = f"{b_date[4:6]}/{b_date[6:8]}" if len(b_date) == 8 else b_date

            is_live_prog = bool(is_time_type and b_date == today_str and cur_m_status.get('is_live', False))

            return {
                'name': '프로그램 비차익 순매매',
                'non_arbitrage': round(bi_diff, 0),
                'arbitrage': round(diff, 0),
                'total': round(tot_diff, 0),
                'bizdate': b_date,
                'bizdate_fmt': date_fmt,
                'time_str': time_fmt,
                'is_live': is_live_prog
            }
    except Exception as e:
        print(f"Error fetching KOSPI program trading: {e}")
    return default_prog


def fetch_exchange_rate():
    """원/달러 환율 수집 (네이버 공식 프론트 API 우선, yfinance 2순위)"""
    # 1순위: 네이버 공식 환율 프론트 API (초고속 응답 보장)
    try:
        url = 'https://m.stock.naver.com/front-api/marketIndex/prices?category=exchange&reutersCode=FX_USDKRW'
        r = requests.get(url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            items = r.json().get('result', [])
            if items:
                latest = items[0]
                price = clean_float(latest.get('closePrice'))
                change = clean_float(latest.get('fluctuations'))
                ratio = clean_float(latest.get('fluctuationsRatio'))
                return {
                    'name': '원/달러 환율 (USD/KRW)',
                    'price': round(price, 2),
                    'change': round(change, 2),
                    'ratio': round(ratio, 2)
                }
    except Exception as e:
        print(f"Naver FX fetch failed, fallback to yfinance: {e}")

    # 2순위: yfinance 폴백
    try:
        usdkrw = yf.Ticker('KRW=X')
        info = usdkrw.fast_info
        last_price = info.last_price if hasattr(info, 'last_price') else 0.0
        prev_close = info.previous_close if hasattr(info, 'previous_close') else last_price
        change = last_price - prev_close
        ratio = (change / prev_close) * 100 if prev_close else 0.0
        return {
            'name': '원/달러 환율 (USD/KRW)',
            'price': round(last_price, 2),
            'change': round(change, 2),
            'ratio': round(ratio, 2)
        }
    except Exception:
        pass

    return {'name': '원/달러 환율', 'price': 1345.0, 'change': 0.0, 'ratio': 0.0}


def fetch_market_breadth():
    """KOSPI & KOSDAQ 등락 종목 수 (Market Breadth) 수집"""
    breadth = {
        'kospi': {'up': 0, 'down': 0, 'flat': 0, 'total': 0, 'up_ratio': 0.0},
        'kosdaq': {'up': 0, 'down': 0, 'flat': 0, 'total': 0, 'up_ratio': 0.0}
    }
    try:
        for mkt_code, mkt_key in [('KOSPI', 'kospi'), ('KOSDAQ', 'kosdaq')]:
            b_res = requests.get(
                'https://m.stock.naver.com/front-api/stock/domestic/integration',
                params={'code': mkt_code, 'endType': 'index'},
                headers=HEADERS,
                timeout=4
            )
            if b_res.status_code == 200:
                b_json = b_res.json()
                u_info = b_json.get('result', {}).get('upDownStockInfo', {})
                if u_info:
                    b_up = int(str(u_info.get('riseCount', 0)).replace(',', ''))
                    b_down = int(str(u_info.get('fallCount', 0)).replace(',', ''))
                    b_flat = int(str(u_info.get('steadyCount', 0)).replace(',', ''))
                    b_upper = int(str(u_info.get('upperCount', 0)).replace(',', ''))
                    b_lower = int(str(u_info.get('lowerCount', 0)).replace(',', ''))
                    b_tot = b_up + b_down + b_flat
                    b_ratio = round((b_up / (b_up + b_down) * 100) if (b_up + b_down) > 0 else 0.0, 1)
                    if b_tot > 0:
                        breadth[mkt_key] = {
                            'up': b_up,
                            'down': b_down,
                            'flat': b_flat,
                            'upper': b_upper,
                            'lower': b_lower,
                            'total': b_tot,
                            'up_ratio': b_ratio
                        }
    except Exception as e:
        print(f"Error fetching market breadth: {e}")
    return breadth


def fetch_top_stocks(cur_m_status, today_iso):
    """KOSPI 시총 상위 대표 종목들 (당일 실시간 & 전일 마감 확정)"""
    top_stocks = []
    top_stocks_prev = []
    top_stocks_prev_date = ''
    is_pre_market = cur_m_status.get('status') == 'PRE_MARKET'

    try:
        res = requests.get('https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=6', headers=HEADERS, timeout=4)
        if res.status_code == 200:
            stocks = res.json().get('stocks', [])
            for st in stocks:
                p_code = st.get('compareToPreviousPrice', {}).get('code', '3')
                price = clean_float(st.get('closePrice'))
                change = clean_float(st.get('compareToPreviousClosePrice'))
                ratio = clean_float(st.get('fluctuationsRatio'))

                # 개장 전(PRE_MARKET)에는 당일 정규장 거래가 시작되지 않았으므로
                # 현재가는 전일 종가(기준가)이며, 당일 전일대비와 등락률은 0.0으로 표기
                if is_pre_market:
                    chg_val = 0.0
                    rat_val = 0.0
                    direction = 'FLAT'
                else:
                    chg_val = change
                    rat_val = ratio
                    direction = 'UP' if p_code in ['2', '1'] else ('DOWN' if p_code in ['5', '4'] else 'FLAT')

                top_stocks.append({
                    'name': st.get('stockName'),
                    'code': st.get('itemCode'),
                    'price': price,
                    'change': chg_val,
                    'ratio': rat_val,
                    'direction': direction,
                    'is_live': not is_pre_market
                })

            def fetch_prev_stock_price(stock_item):
                code = stock_item.get('code')
                name = stock_item.get('name')
                try:
                    r = requests.get(f'https://m.stock.naver.com/api/stock/{code}/price', headers=HEADERS, timeout=3)
                    if r.status_code == 200:
                        items = r.json()
                        if items:
                            # 첫 번째 항목이 오늘(장중 체결)이면 직전 마감은 items[1], 개장 전이거나 오늘 데이터가 없으면 items[0]
                            if items[0].get('localTradedAt') == today_iso and len(items) > 1:
                                prev = items[1]
                            else:
                                prev = items[0]

                            pr_code = prev.get('compareToPreviousPrice', {}).get('code', '3')
                            chg = clean_float(prev.get('compareToPreviousClosePrice', 0))
                            ratio = clean_float(prev.get('fluctuationsRatio', 0))
                            if pr_code in ['5', '4']:
                                chg = -abs(chg)
                                ratio = -abs(ratio)
                                direction = 'DOWN'
                            elif pr_code in ['2', '1']:
                                chg = abs(chg)
                                ratio = abs(ratio)
                                direction = 'UP'
                            else:
                                direction = 'FLAT'
                            return {
                                'name': name,
                                'code': code,
                                'date': prev.get('localTradedAt', ''),
                                'price': clean_float(prev.get('closePrice')),
                                'change': chg,
                                'ratio': ratio,
                                'direction': direction
                            }
                except Exception:
                    pass
                return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as stock_executor:
                prev_results = list(stock_executor.map(fetch_prev_stock_price, top_stocks))

            for p in prev_results:
                if p:
                    top_stocks_prev.append(p)
                    if not top_stocks_prev_date and p.get('date'):
                        top_stocks_prev_date = p.get('date')
    except Exception as e:
        print(f"Error fetching top stocks: {e}")

    return {
        'top_stocks': top_stocks,
        'top_stocks_prev': top_stocks_prev,
        'top_stocks_prev_date': top_stocks_prev_date
    }


def get_krx_summary():
    """
    한국 시장(KRX) 마감 종합 데이터 반환 (병렬 수집을 통한 초고속 렌더링)
    """
    cur_m_status = get_market_status('KRX')
    today_str = get_now_kst().strftime('%Y%m%d')
    today_iso = get_now_kst().strftime('%Y-%m-%d')

    result = {
        'market': 'KRX',
        'date': get_now_kst().strftime('%Y-%m-%d'),
        'kospi': {},
        'kosdaq': {},
        'exchange_rate': {},
        'investors_kospi': {},
        'investors_kosdaq': {},
        'investors_kospi_prev': {},
        'investors_kosdaq_prev': {},
        'investors_history_kospi': pd.DataFrame(),
        'investors_history_kosdaq': pd.DataFrame(),
        'program': {},
        'breadth': {},
        'top_stocks': [],
        'top_stocks_prev': [],
        'top_stocks_prev_date': '',
        'history': pd.DataFrame()
    }

    # 독립된 외부 호출들을 ThreadPoolExecutor로 병렬 실행하여 로딩 시간 대폭 단축 (1.5초 이내)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        f_kp_price = executor.submit(fetch_index_price, 'KOSPI')
        f_kd_price = executor.submit(fetch_index_price, 'KOSDAQ')
        f_kp_hist = executor.submit(get_investor_trend_history, '01')
        f_kd_hist = executor.submit(get_investor_trend_history, '02')
        f_kp_trend = executor.submit(fetch_live_investor_trend, 'KOSPI', cur_m_status, today_str)
        f_kd_trend = executor.submit(fetch_live_investor_trend, 'KOSDAQ', cur_m_status, today_str)
        f_prog = executor.submit(fetch_program_trading, cur_m_status, today_str)
        f_fx = executor.submit(fetch_exchange_rate)
        f_breadth = executor.submit(fetch_market_breadth)
        f_stocks = executor.submit(fetch_top_stocks, cur_m_status, today_iso)

        result['kospi'] = f_kp_price.result()
        result['kosdaq'] = f_kd_price.result()
        
        hist_kp = f_kp_hist.result()
        result['investors_kospi_prev'] = hist_kp.get('prev', {})
        result['investors_history_kospi'] = hist_kp.get('history', pd.DataFrame())

        hist_kd = f_kd_hist.result()
        result['investors_kosdaq_prev'] = hist_kd.get('prev', {})
        result['investors_history_kosdaq'] = hist_kd.get('history', pd.DataFrame())

        result['investors_kospi'] = f_kp_trend.result()
        result['investors_kosdaq'] = f_kd_trend.result()
        result['program'] = f_prog.result()
        result['exchange_rate'] = f_fx.result()
        result['breadth'] = f_breadth.result()

        st_info = f_stocks.result()
        result['top_stocks'] = st_info['top_stocks']
        result['top_stocks_prev'] = st_info['top_stocks_prev']
        result['top_stocks_prev_date'] = st_info['top_stocks_prev_date']

    return result



def get_us_summary():
    """
    미국 시장(US) 마감 종합 데이터 반환
    """
    result = {
        'market': 'US',
        'date': get_now_ny().strftime('%Y-%m-%d'),
        'indices': {},
        'macro': {},
        'm7_stocks': [],
        'history': pd.DataFrame()
    }

    # 미국 핵심 티커 리스트
    # ^GSPC: S&P500, ^IXIC: 나스닥, ^SOX: 필라델피아 반도체, ^DJI: 다우존스, ^RUT: 러셀2000
    # ^VIX: 공포지수, ^TNX: 10년물 금리, CL=F: WTI유가, DX-Y.NYB: 달러인덱스, GC=F: 금선물, BTC-USD: 비트코인
    tickers = ['^GSPC', '^IXIC', '^SOX', '^DJI', '^RUT', '^VIX', '^TNX', 'CL=F', 'DX-Y.NYB', 'GC=F', 'BTC-USD']
    m7_symbols = ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA']

    try:
        all_data = yf.download(tickers + m7_symbols, period='5d', progress=False, timeout=10)['Close']
        
        # 지수 파싱
        name_map = {
            '^GSPC': 'S&P 500',
            '^IXIC': '나스닥 종합 (Nasdaq)',
            '^SOX': '필라델피아 반도체 (SOX)',
            '^DJI': '다우존스 (Dow Jones)',
            '^RUT': '러셀 2000 (소형주)'
        }
        for sym, name in name_map.items():
            if sym in all_data.columns and len(all_data[sym].dropna()) >= 2:
                series = all_data[sym].dropna()
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                change = curr - prev
                ratio = (change / prev) * 100
                result['indices'][sym] = {
                    'name': name,
                    'price': round(curr, 2),
                    'change': round(change, 2),
                    'ratio': round(ratio, 2)
                }

        # 매크로 지표 파싱 (M7 7개 종목과의 시각적 대칭을 맞춘 7대 거시 매크로 지표)
        macro_map = {
            '^SOX': '필라델피아 반도체 (SOX)',
            '^TNX': '미 국채 10년물 금리',
            'DX-Y.NYB': '달러 인덱스 (DXY)',
            'CL=F': 'WTI 원유 선물',
            'GC=F': '금 선물 (Gold)',
            'BTC-USD': '비트코인 (BTC)',
            '^VIX': '변동성 지수 (VIX)'
        }
        for sym, name in macro_map.items():
            if sym in all_data.columns and len(all_data[sym].dropna()) >= 2:
                series = all_data[sym].dropna()
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                change = curr - prev
                ratio = (change / prev) * 100
                if sym == '^TNX':
                    unit = '%'
                elif sym in ['CL=F', 'GC=F', 'BTC-USD']:
                    unit = '$'
                else:
                    unit = 'pt'
                result['macro'][sym] = {
                    'name': name,
                    'price': round(curr, 2),
                    'change': round(change, 2),
                    'ratio': round(ratio, 2),
                    'unit': unit
                }

        # M7 종목 파싱
        m7_name_map = {
            'NVDA': '엔비디아 (NVIDIA)',
            'AAPL': '애플 (Apple)',
            'MSFT': '마이크로소프트 (MSFT)',
            'AMZN': '아마존 (Amazon)',
            'GOOGL': '알파벳 (Google)',
            'META': '메타 (Meta)',
            'TSLA': '테슬라 (Tesla)'
        }
        for sym in m7_symbols:
            if sym in all_data.columns and len(all_data[sym].dropna()) >= 2:
                series = all_data[sym].dropna()
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                change = curr - prev
                ratio = (change / prev) * 100
                result['m7_stocks'].append({
                    'name': m7_name_map.get(sym, sym),
                    'ticker': sym,
                    'price': round(curr, 2),
                    'change': round(change, 2),
                    'ratio': round(ratio, 2)
                })

        # S&P 500 과거 차트용
        if '^GSPC' in all_data.columns:
            s_series = all_data['^GSPC'].dropna().tail(7).reset_index()
            s_series.columns = ['Date', 'Close']
            s_series['DateStr'] = s_series['Date'].dt.strftime('%m-%d')
            result['history'] = s_series

    except Exception as e:
        print(f"Error fetching US summary: {e}")

    return result

def get_latest_expected_trading_day(target_date: str = None) -> str:
    """
    가장 최근 거래 완료된 실제 영업일 YYYY-MM-DD 반환.
    - target_date가 전달된 경우: 해당 날짜 기준 (또는 직전 영업일)
    - target_date가 없는 경우: KST 기준 15:45 이전이거나 오늘이 주말/새벽이면 직전 마감 거래일 반환
    """
    from datetime import datetime, timezone, timedelta
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    if target_date:
        try:
            clean_date = str(target_date).replace('-', '')
            dt = datetime.strptime(clean_date, "%Y%m%d").replace(tzinfo=timezone(timedelta(hours=9)))
        except Exception:
            dt = now_kst
    else:
        dt = now_kst

    # 평일 15:45 이후에만 당일 종가 확정
    if dt.weekday() < 5 and (dt.hour > 15 or (dt.hour == 15 and dt.minute >= 45)):
        return dt.strftime("%Y-%m-%d")

    # 장전, 새벽, 주말: 직전 마감 거래일 산출
    if dt.weekday() == 0:    # 월요일 장전 -> 지난주 금요일 (3일 전)
        days_back = 3
    elif dt.weekday() == 6:  # 일요일 -> 지난주 금요일 (2일 전)
        days_back = 2
    elif dt.weekday() == 5:  # 토요일 -> 지난주 금요일 (1일 전)
        days_back = 1
    else:                    # 화~금 장전/새벽 -> 전일 (1일 전)
        days_back = 1

    return (dt - timedelta(days=days_back)).strftime("%Y-%m-%d")
