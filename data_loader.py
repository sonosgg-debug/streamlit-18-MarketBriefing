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

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None

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

def get_market_status(market='KRX'):
    """
    서버 환경(로컬 PC 또는 UTC 기반 클라우드 서버)에 관계없이
    항상 한국 표준시(KST) 및 뉴욕 표준시(ET)를 기준으로 실시간 장중 여부 정확히 판정
    """
    if market == 'KRX':
        now_kst = get_now_kst()
        weekday = now_kst.weekday() # 0:월 ~ 4:금, 5:토, 6:일
        if weekday >= 5:
            return {
                'status': 'WEEKEND',
                'label': '🏖️ 주말 휴장 (직전 거래일 종가 기준)',
                'badge': '⚪ 주말 휴장',
                'is_live': False,
                'title_suffix': '마감 종합 브리핑',
                'time_str': f"{now_kst.strftime('%Y-%m-%d')} (직전 정규장 마감)",
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

def get_krx_summary():
    """
    한국 시장(KRX) 마감 종합 데이터 반환
    """
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
        'program': {
            'name': '프로그램 비차익 순매매',
            'non_arbitrage': 0.0,
            'arbitrage': 0.0,
            'total': 0.0,
            'bizdate': '',
            'bizdate_fmt': '',
            'time_str': '',
            'is_live': False
        },
        'breadth': {
            'kospi': {'up': 0, 'down': 0, 'flat': 0, 'total': 0, 'up_ratio': 0.0},
            'kosdaq': {'up': 0, 'down': 0, 'flat': 0, 'total': 0, 'up_ratio': 0.0}
        },
        'top_stocks': [],
        'top_stocks_prev': [],
        'top_stocks_prev_date': '',
        'history': pd.DataFrame()
    }

    # 1. KOSPI 지수 정보 (Naver Mobile API)
    try:
        res = requests.get('https://m.stock.naver.com/api/index/KOSPI/price', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            item = res.json()[0]
            result['kospi'] = {
                'name': '코스피 (KOSPI)',
                'price': clean_float(item.get('closePrice')),
                'change': clean_float(item.get('compareToPreviousClosePrice')),
                'ratio': clean_float(item.get('fluctuationsRatio')),
                'direction': 'UP' if item.get('compareToPreviousPrice', {}).get('code') in ['2', '1'] else 'DOWN',
                'date': item.get('localTradedAt', '')
            }
    except Exception as e:
        print(f"Error fetching KOSPI price: {e}")

    # 2. KOSDAQ 지수 정보
    try:
        res = requests.get('https://m.stock.naver.com/api/index/KOSDAQ/price', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            item = res.json()[0]
            result['kosdaq'] = {
                'name': '코스닥 (KOSDAQ)',
                'price': clean_float(item.get('closePrice')),
                'change': clean_float(item.get('compareToPreviousClosePrice')),
                'ratio': clean_float(item.get('fluctuationsRatio')),
                'direction': 'UP' if item.get('compareToPreviousPrice', {}).get('code') in ['2', '1'] else 'DOWN',
                'date': item.get('localTradedAt', '')
            }
    except Exception as e:
        print(f"Error fetching KOSDAQ price: {e}")

    cur_m_status = get_market_status('KRX')

    # 3. KOSPI 전일 마감 수급 및 최근 일자별 추이 (공식 REST API)
    try:
        hist_kospi = get_investor_trend_history('01')
        result['investors_kospi_prev'] = hist_kospi.get('prev', {})
        result['investors_history_kospi'] = hist_kospi.get('history', pd.DataFrame())
    except Exception as e:
        print(f"Error attaching KOSPI history: {e}")
        hist_kospi = {'prev': {}, 'history': pd.DataFrame()}

    # 3-1. KOSPI 실시간 잠정 수급 (당일 장중/개장전 수치 유지)
    kp_inv_live = {'personal': 0.0, 'foreign': 0.0, 'institutional': 0.0, 'bizdate': ''}
    try:
        res = requests.get('https://m.stock.naver.com/api/index/KOSPI/trend', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            trend = res.json()
            kp_inv_live = {
                'personal': clean_float(trend.get('personalValue', 0)),
                'foreign': clean_float(trend.get('foreignValue', 0)),
                'institutional': clean_float(trend.get('institutionalValue', 0)),
                'bizdate': trend.get('bizdate', '')
            }
    except Exception as e:
        print(f"Error fetching KOSPI trend: {e}")

    result['investors_kospi'] = kp_inv_live

    # 4. KOSDAQ 전일 마감 수급 및 최근 일자별 추이
    try:
        hist_kosdaq = get_investor_trend_history('02')
        result['investors_kosdaq_prev'] = hist_kosdaq.get('prev', {})
        result['investors_history_kosdaq'] = hist_kosdaq.get('history', pd.DataFrame())
    except Exception as e:
        print(f"Error attaching KOSDAQ history: {e}")
        hist_kosdaq = {'prev': {}, 'history': pd.DataFrame()}

    # 4-1. KOSDAQ 실시간 잠정 수급 (당일 장중/개장전 수치 유지)
    kd_inv_live = {'personal': 0.0, 'foreign': 0.0, 'institutional': 0.0, 'bizdate': ''}
    try:
        res = requests.get('https://m.stock.naver.com/api/index/KOSDAQ/trend', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            trend = res.json()
            kd_inv_live = {
                'personal': clean_float(trend.get('personalValue', 0)),
                'foreign': clean_float(trend.get('foreignValue', 0)),
                'institutional': clean_float(trend.get('institutionalValue', 0)),
                'bizdate': trend.get('bizdate', '')
            }
    except Exception as e:
        print(f"Error fetching KOSDAQ trend: {e}")

    result['investors_kosdaq'] = kd_inv_live

    # 4-1. KOSPI 프로그램 매매 (특히 비차익 순매매)
    try:
        now_kst = get_now_kst()
        today_str = now_kst.strftime('%Y%m%d')
        
        # 1) 실시간 장중(TIME) 데이터 우선 호출
        res_prog = requests.get(
            'https://stock.naver.com/api/domestic/market/trendProgram',
            params={'tradeType': 'KRX', 'krxMarketType': 'KOSPI', 'bizdate': today_str, 'startIdx': '1', 'pageSize': '1', 'periodType': 'TIME'},
            headers=HEADERS,
            timeout=5
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
                timeout=5
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

            cur_m_status = get_market_status('KRX')
            is_live_prog = bool(is_time_type and b_date == today_str and cur_m_status.get('is_live', False))

            result['program'] = {
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

    # 5. 원/달러 환율 (yfinance)
    try:
        usdkrw = yf.Ticker('KRW=X')
        info = usdkrw.fast_info
        last_price = info.last_price if hasattr(info, 'last_price') else 0.0
        prev_close = info.previous_close if hasattr(info, 'previous_close') else last_price
        change = last_price - prev_close
        ratio = (change / prev_close) * 100 if prev_close else 0.0
        result['exchange_rate'] = {
            'name': '원/달러 환율 (USD/KRW)',
            'price': round(last_price, 2),
            'change': round(change, 2),
            'ratio': round(ratio, 2)
        }
    except Exception as e:
        result['exchange_rate'] = {'name': '원/달러 환율', 'price': 1345.0, 'change': 0.0, 'ratio': 0.0}

    # 6. KOSPI 시총 상위 대표 종목들 (당일 실시간 & 전일 마감 확정)
    try:
        res = requests.get('https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=6', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            stocks = res.json().get('stocks', [])
            for st in stocks:
                p_code = st.get('compareToPreviousPrice', {}).get('code', '3')
                result['top_stocks'].append({
                    'name': st.get('stockName'),
                    'code': st.get('itemCode'),
                    'price': clean_float(st.get('closePrice')),
                    'change': clean_float(st.get('compareToPreviousClosePrice')),
                    'ratio': clean_float(st.get('fluctuationsRatio')),
                    'direction': 'UP' if p_code in ['2', '1'] else ('DOWN' if p_code in ['5', '4'] else 'FLAT')
                })

            # 전일 마감 확정 시세 병렬 수집
            def fetch_prev_stock_price(stock_item):
                code = stock_item.get('code')
                name = stock_item.get('name')
                try:
                    r = requests.get(f'https://m.stock.naver.com/api/stock/{code}/price', headers=HEADERS, timeout=3)
                    if r.status_code == 200:
                        items = r.json()
                        if len(items) > 1:
                            prev = items[1]
                            pr_code = prev.get('compareToPreviousPrice', {}).get('code', '3')
                            sign = 1 if pr_code in ['2', '1'] else (-1 if pr_code in ['5', '4'] else 0)
                            chg = clean_float(prev.get('compareToPreviousClosePrice', 0)) * sign
                            ratio = clean_float(prev.get('fluctuationsRatio', 0)) * sign
                            return {
                                'name': name,
                                'code': code,
                                'date': prev.get('localTradedAt', ''),
                                'price': clean_float(prev.get('closePrice')),
                                'change': chg,
                                'ratio': ratio,
                                'direction': 'UP' if sign > 0 else ('DOWN' if sign < 0 else 'FLAT')
                            }
                except Exception:
                    pass
                return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                prev_results = list(executor.map(fetch_prev_stock_price, result['top_stocks']))

            prev_date_str = ""
            for p in prev_results:
                if p:
                    result['top_stocks_prev'].append(p)
                    if not prev_date_str and p.get('date'):
                        prev_date_str = p.get('date')
            result['top_stocks_prev_date'] = prev_date_str
    except Exception as e:
        print(f"Error fetching top stocks: {e}")

    # 7. KOSPI 과거 7일 지수 추이 (차트용)
    try:
        df = yf.download('^KS11', period='1mo', interval='1d', progress=False)
        if not df.empty:
            df = df[['Close']].tail(7).reset_index()
            df.columns = ['Date', 'Close']
            df['DateStr'] = df['Date'].dt.strftime('%m-%d')
            result['history'] = df
    except Exception as e:
        pass

    # 8. KOSPI & KOSDAQ 시장 등락 종목 수 (Market Breadth)
    # 1) Naver 모바일 프론트 API를 통한 실시간 등락 종목 수 직접 수집 (1순위: 실시간 집계 보장)
    try:
        for mkt_code, mkt_key in [('KOSPI', 'kospi'), ('KOSDAQ', 'kosdaq')]:
            b_res = requests.get(
                'https://m.stock.naver.com/front-api/stock/domestic/integration',
                params={'code': mkt_code, 'endType': 'index'},
                headers=HEADERS,
                timeout=5
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
                        result['breadth'][mkt_key] = {
                            'up': b_up,
                            'down': b_down,
                            'flat': b_flat,
                            'upper': b_upper,
                            'lower': b_lower,
                            'total': b_tot,
                            'up_ratio': b_ratio
                        }
    except Exception as e:
        print(f"Error fetching Naver market breadth: {e}")

    # 2) Naver 실패 시 FinanceDataReader 폴백 (2순위)
    if result['breadth']['kospi']['total'] == 0 and fdr is not None:
        try:
            df_krx = fdr.StockListing('KRX')
            if not df_krx.empty and 'Market' in df_krx.columns and 'Changes' in df_krx.columns:
                kp_stocks = df_krx[df_krx['Market'] == 'KOSPI']
                kd_stocks = df_krx[df_krx['Market'] == 'KOSDAQ']

                if not kp_stocks.empty and not kp_stocks['Changes'].isna().all():
                    kp_up = int((kp_stocks['Changes'] > 0).sum())
                    kp_down = int((kp_stocks['Changes'] < 0).sum())
                    kp_flat = int((kp_stocks['Changes'] == 0).sum())
                    kp_tot = len(kp_stocks)
                    kp_ratio = round((kp_up / (kp_up + kp_down) * 100) if (kp_up + kp_down) > 0 else 0.0, 1)
                    result['breadth']['kospi'] = {
                        'up': kp_up,
                        'down': kp_down,
                        'flat': kp_flat,
                        'total': kp_tot,
                        'up_ratio': kp_ratio
                    }

                if not kd_stocks.empty and not kd_stocks['Changes'].isna().all():
                    kd_up = int((kd_stocks['Changes'] > 0).sum())
                    kd_down = int((kd_stocks['Changes'] < 0).sum())
                    kd_flat = int((kd_stocks['Changes'] == 0).sum())
                    kd_tot = len(kd_stocks)
                    kd_ratio = round((kd_up / (kd_up + kd_down) * 100) if (kd_up + kd_down) > 0 else 0.0, 1)
                    result['breadth']['kosdaq'] = {
                        'up': kd_up,
                        'down': kd_down,
                        'flat': kd_flat,
                        'total': kd_tot,
                        'up_ratio': kd_ratio
                    }
        except Exception as e:
            print(f"Error fetching KRX market breadth fallback: {e}")

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
        all_data = yf.download(tickers + m7_symbols, period='5d', progress=False)['Close']
        
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
