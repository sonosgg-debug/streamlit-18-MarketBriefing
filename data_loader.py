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

def get_investor_trend_history(sosok='01'):
    """
    네이버 금융 일자별 투자자 매매동향(최근 5~10일) 및 전일 마감 확정 수치 반환
    sosok: '01' (KOSPI), '02' (KOSDAQ)
    """
    try:
        now_kst = get_now_kst()
        today_str = now_kst.strftime('%Y%m%d')
        url = f'https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={today_str}&sosok={sosok}'
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            dfs = pd.read_html(io.StringIO(r.content.decode('cp949', errors='replace')))
            if dfs and not dfs[0].empty:
                df = dfs[0].dropna(how='all').copy()
                std_cols = ['날짜', '개인', '외국인', '기관계', '금융투자', '보험', '투신', '은행', '기타금융', '연기금', '기타법인']
                if len(df.columns) == len(std_cols):
                    df.columns = std_cols
                else:
                    df.columns = [c[1] if isinstance(c, tuple) and c[1] else c[0] if isinstance(c, tuple) else str(c) for c in df.columns]
                
                df = df[df['날짜'].astype(str).str.match(r'^\d{2}\.\d{2}\.\d{2}$')].reset_index(drop=True)
                for col in df.columns[1:]:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace('+', ''), errors='coerce').fillna(0.0)
                
                # 전일(직전 거래일) 마감 행 추출
                today_short = now_kst.strftime('%y.%m.%d')
                first_date = str(df.iloc[0]['날짜']).strip() if len(df) > 0 else ''
                
                # 첫 번째 행이 오늘 날짜(장중 잠정)이면 두 번째 행이 전일 마감, 아니면 첫 번째 행이 직전 마감
                if first_date == today_short and len(df) > 1:
                    prev_row = df.iloc[1]
                elif len(df) > 0:
                    prev_row = df.iloc[0]
                else:
                    prev_row = pd.Series()
                
                prev_data = {}
                if not prev_row.empty:
                    prev_data = {
                        'date': str(prev_row.get('날짜', '')),
                        'personal': float(prev_row.get('개인', 0.0)),
                        'foreign': float(prev_row.get('외국인', 0.0)),
                        'institutional': float(prev_row.get('기관계', 0.0)),
                        'financial_invest': float(prev_row.get('금융투자', 0.0)),
                        'insurance': float(prev_row.get('보험', 0.0)),
                        'investment_trust': float(prev_row.get('투신', 0.0)),
                        'bank': float(prev_row.get('은행', 0.0)),
                        'other_finance': float(prev_row.get('기타금융', 0.0)),
                        'pension': float(prev_row.get('연기금', 0.0)),
                        'other_corp': float(prev_row.get('기타법인', 0.0))
                    }
                
                return {
                    'prev': prev_data,
                    'history': df.head(6)
                }
    except Exception as e:
        print(f"Error fetching investor trend history (sosok={sosok}): {e}")
    
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
        'investors_history_kospi': pd.DataFrame(),
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

    # 3. KOSPI 투자자별 수급 (Trend API)
    try:
        res = requests.get('https://m.stock.naver.com/api/index/KOSPI/trend', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            trend = res.json()
            # 억 원 단위 변환 또는 원본 값 파싱
            result['investors_kospi'] = {
                'personal': clean_float(trend.get('personalValue', 0)),
                'foreign': clean_float(trend.get('foreignValue', 0)),
                'institutional': clean_float(trend.get('institutionalValue', 0)),
                'bizdate': trend.get('bizdate', '')
            }
    except Exception as e:
        print(f"Error fetching KOSPI trend: {e}")

    # 3-1. KOSPI 전일 마감 수급 및 최근 일자별 추이
    try:
        hist_kospi = get_investor_trend_history('01')
        result['investors_kospi_prev'] = hist_kospi.get('prev', {})
        result['investors_history_kospi'] = hist_kospi.get('history', pd.DataFrame())
    except Exception as e:
        print(f"Error attaching KOSPI history: {e}")

    # 4. KOSDAQ 투자자별 수급
    try:
        res = requests.get('https://m.stock.naver.com/api/index/KOSDAQ/trend', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            trend = res.json()
            result['investors_kosdaq'] = {
                'personal': clean_float(trend.get('personalValue', 0)),
                'foreign': clean_float(trend.get('foreignValue', 0)),
                'institutional': clean_float(trend.get('institutionalValue', 0)),
                'bizdate': trend.get('bizdate', '')
            }
    except Exception as e:
        print(f"Error fetching KOSDAQ trend: {e}")

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

    # 6. KOSPI 시총 상위 대표 종목들
    try:
        res = requests.get('https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=6', headers=HEADERS, timeout=5)
        if res.status_code == 200:
            stocks = res.json().get('stocks', [])
            for st in stocks:
                result['top_stocks'].append({
                    'name': st.get('stockName'),
                    'code': st.get('itemCode'),
                    'price': clean_float(st.get('closePrice')),
                    'change': clean_float(st.get('compareToPreviousClosePrice')),
                    'ratio': clean_float(st.get('fluctuationsRatio')),
                    'direction': 'UP' if st.get('compareToPreviousPrice', {}).get('code') in ['2', '1'] else 'DOWN'
                })
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
    # ^VIX: 공포지수, ^TNX: 10년물 금리, CL=F: WTI유가, DX-Y.NYB: 달러인덱스
    tickers = ['^GSPC', '^IXIC', '^SOX', '^DJI', '^RUT', '^VIX', '^TNX', 'CL=F', 'DX-Y.NYB']
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

        # 매크로 지표 파싱
        macro_map = {
            '^VIX': '변동성 지수 (VIX)',
            '^TNX': '미 국채 10년물 금리',
            'CL=F': 'WTI 원유 선물',
            'DX-Y.NYB': '달러 인덱스 (DXY)'
        }
        for sym, name in macro_map.items():
            if sym in all_data.columns and len(all_data[sym].dropna()) >= 2:
                series = all_data[sym].dropna()
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                change = curr - prev
                ratio = (change / prev) * 100
                unit = '%' if sym == '^TNX' else ('$' if sym == 'CL=F' else 'pt')
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
