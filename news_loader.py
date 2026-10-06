"""
news_loader.py
시장 핵심 동인(Market Drivers) 뉴스 수집 및 3~4문장 지능형 브리핑 엔진
- 한국 증시(KRX): 네이버 증권 주요 시황 뉴스 API (실시간/마감 핵심 동인 선별)
- 미국 증시(US): Yahoo Finance 실시간/마감 마켓 랩 뉴스 (yfinance Search/Ticker)
- 하이브리드 요약: Gemini API(설정 시) 또는 내장 스마트 추출 엔진(Zero Dependency)
"""

import os
import requests
import yfinance as yf
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_gemini_api_key():
    """환경 변수, Streamlit session_state 또는 Streamlit secrets에서 Gemini API 키 확인"""
    try:
        import streamlit as st
        # 1. 사이드바 UI 입력값 (세션 상태)
        if st.session_state.get('gemini_api_key_input'):
            return st.session_state['gemini_api_key_input'].strip()
        # 2. .streamlit/secrets.toml 파일
        if hasattr(st, "secrets") and st.secrets and 'GEMINI_API_KEY' in st.secrets:
            return st.secrets['GEMINI_API_KEY'].strip()
    except BaseException:
        pass
    # 3. OS 환경 변수
    key = os.environ.get('GEMINI_API_KEY')
    if key:
        return key.strip()
    return None


def call_gemini_generate(prompt: str, api_key: str):
    """Google Gemini REST API 호출 (최신 사용 가능 모델 순차 시도 및 즉시 응답 최적화)"""
    models_to_try = ["gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-3.8-flash"]
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800,
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }
    headers = {"Content-Type": "application/json"}

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get('candidates', [])
                if candidates:
                    text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    if text:
                        return text.strip()
        except Exception as e:
            print(f"Gemini API call ({model}) failed: {e}")
    return None


def fetch_krx_top_news(count=3):
    """
    네이버 증권 모바일 API에서 당일 장중/마감 시황 핵심 뉴스 선별
    - 시간 가중치 및 당일 기사 우선 선별로 실시간 최신 시황 반영
    """
    url = 'https://m.stock.naver.com/api/news/list?category=mainnews&pageSize=35'
    try:
        res = requests.get(url, headers=HEADERS, timeout=4)
        if res.status_code != 200:
            return []
        items = res.json()
    except Exception as e:
        print(f"KRX News fetch failed: {e}")
        return []

    scored_news = []
    keywords = {
        '코스피': 5, '코스닥': 5, '증시': 4, '시황': 5, '마감': 4, '장중': 4,
        '상승': 2, '하락': 2, '혼조': 3, '외인': 3, '기관': 3, '외국인': 3,
        '금리': 3, '환율': 3, '반도체': 2, '국채': 3, '물가': 2, '긴축': 2,
        '유가': 3, '고용': 3, '보합': 3, '등락': 3
    }
    now_dt_str = datetime.now().strftime('%Y%m%d')

    for it in items:
        tit = it.get('tit', '')
        sub = it.get('subcontent', '')
        oid = it.get('oid', '')
        aid = it.get('aid', '')
        ohnm = it.get('ohnm', '네이버뉴스')
        dt = it.get('dt', '')

        # 개별 종목 단순 공시, 테마주 잡음 필터링
        if any(bad in tit for bad in ['[특징주]', '인사', '부음', '포토', '골프', '코인', '동정', '사설', '부고']):
            continue

        score = sum(weight for kw, weight in keywords.items() if kw in tit) * 2
        score += sum(weight for kw, weight in keywords.items() if kw in sub)

        # 시간 가중치: 당일 기사 및 최신 시간대 추가 가산점
        if dt.startswith(now_dt_str):
            score += 4
            try:
                pub_hour = int(dt[8:10])
                current_hour = datetime.now().hour
                hour_diff = max(0, current_hour - pub_hour)
                if hour_diff <= 2:
                    score += 4
                elif hour_diff <= 4:
                    score += 2
            except Exception:
                pass

        if score >= 4:
            time_str = ""
            if len(dt) >= 12:
                time_str = f"{dt[4:6]}.{dt[6:8]} {dt[8:10]}:{dt[10:12]}"

            scored_news.append({
                'score': score,
                'title': tit,
                'summary': sub,
                'press': ohnm,
                'time': time_str,
                'dt': dt,
                'link': f"https://n.news.naver.com/mnews/article/{oid}/{aid}",
                'source': '네이버 증권'
            })

    scored_news.sort(key=lambda x: (x['score'], x.get('dt', '')), reverse=True)
    return scored_news[:count]


def fetch_us_top_news(count=3):
    """
    Yahoo Finance에서 미국 증시 당일 장중/마감 대표 기사 선별
    - 최신 36시간 이내 기사 대상 (장마감 및 당일 정규장 시황 집중)
    - providerPublishTime 기준 최신순 정렬
    - 뉴욕 현지 시각(ET) 포맷 제공
    """
    try:
        from zoneinfo import ZoneInfo
        ny_tz = ZoneInfo('America/New_York')
    except Exception:
        from datetime import timezone, timedelta
        ny_tz = timezone(timedelta(hours=-4))

    now_ts = datetime.now().timestamp()
    cutoff_ts = now_ts - 36 * 3600

    raw_items = []
    try:
        s = yf.Search('stock market today', news_count=20, timeout=5)
        if s.news:
            raw_items.extend(s.news)
    except Exception as e:
        print(f"Yahoo Search (stock market today) failed: {e}")

    if len(raw_items) < 3:
        try:
            s2 = yf.Search('S&P 500', news_count=10, timeout=5)
            if s2.news:
                raw_items.extend(s2.news)
        except Exception as e:
            print(f"Yahoo Search (S&P 500) failed: {e}")

    seen_titles = set()
    articles = []

    market_keywords = [
        'stock market today', 'stocks', 'dow', 's&p', 'nasdaq', 'wall street',
        'treasury', 'yields', 'rebound', 'comeback', 'indexes fared', 'close',
        'fed', 'inflation', 'quarter', 'rally', 'equities', 'chips', 'tech'
    ]

    for it in raw_items:
        title = it.get('title', '').strip()
        link = it.get('link', '').strip()
        pub_time = it.get('providerPublishTime')
        pub = it.get('publisher', 'Yahoo Finance')

        if not title or not link or title in seen_titles:
            continue
        seen_titles.add(title)

        # 36시간 이전 구형 기사 제외
        if pub_time and pub_time < cutoff_ts:
            continue

        t_lower = title.lower()
        score = sum(1 for kw in market_keywords if kw in t_lower)

        time_str = ""
        if pub_time:
            try:
                dt_ny = datetime.fromtimestamp(pub_time, ny_tz)
                time_str = dt_ny.strftime('%m.%d %H:%M ET')
            except Exception:
                pass

        articles.append({
            'title': title,
            'summary': '',
            'press': pub,
            'time': time_str,
            'pub_time': pub_time or 0,
            'score': score,
            'link': link,
            'source': 'Yahoo Finance'
        })

    # 최신성(발행시각)과 시황 적합도(스코어) 기준 우선 정렬
    articles.sort(key=lambda x: (x['score'] >= 1, x['pub_time']), reverse=True)
    return articles[:count]


def generate_krx_drivers_nlp(news_list, krx_data=None, is_live=False):
    """
    한국 시장 핵심 동인 3~4문장 지능형 추출(Extractive Synthesis) 알고리즘
    - 실제 수집된 최신 기사 헤드라인 및 본문 요약에서 동적 동인 추출
    - 정규장 실시간(is_live=True) vs 마감(is_live=False) 시제 및 문맥 분기
    - 실제 지수 등락률 및 투자 주체별 수급 데이터 결합
    """
    kospi = (krx_data or {}).get('kospi', {})
    kosdaq = (krx_data or {}).get('kosdaq', {})
    inv = (krx_data or {}).get('investors_kospi', {})
    inv_prev = (krx_data or {}).get('investors_kospi_prev', {})

    kp_p = kospi.get('price', 0.0)
    kp_r = kospi.get('ratio', 0.0)
    kd_p = kosdaq.get('price', 0.0)
    kd_r = kosdaq.get('ratio', 0.0)

    kp_for = inv.get('foreign', 0.0)
    kp_inst = inv.get('institutional', 0.0)

    # 개장 전(PRE_MARKET), 휴장일 또는 당일 수급이 아직 0인 경우 직전 거래일 마감 확정치로 통일
    if not is_live and (kp_for == 0.0 and kp_inst == 0.0) and inv_prev:
        kp_for = inv_prev.get('foreign', 0.0)
        kp_inst = inv_prev.get('institutional', 0.0)
        inv = inv_prev

    if not news_list:
        action_verb = "보이고 있습니다" if is_live else "마감했습니다"
        return {
            'sentences': [
                f"당일 코스피는 {kp_p:,.2f}pt({kp_r:+.2f}%) 수준에서 글로벌 매크로 지표 관망 심리와 대외 변수를 주시하며 흐름을 {action_verb}.",
                "외국인과 기관의 수급 공방 속에 지수의 방향성이 제한되는 양상이 이어지고 있습니다.",
                "대형주 중심의 차별화 장세가 이어지며 개별 실적 모멘텀에 따른 순환매가 전개되고 있습니다."
            ],
            'tags': ["#관망세", "#수급공방", "#개별종목장세"]
        }

    all_text = " ".join([f"{n.get('title', '')} {n.get('summary', '')}" for n in news_list])

    sentences = []
    tags = []

    # 1. 거시 환경 & 지수 종합 흐름
    macro_items = []
    if '유가' in all_text:
        macro_items.append("국제유가 상승")
        tags.append("#국제유가상승")
    if any(k in all_text for k in ['금리', '국채', '10년물']):
        macro_items.append("미 국채금리 변동성")
        tags.append("#국채금리변동")
    if any(k in all_text for k in ['고용', '지표', '경계심리']):
        macro_items.append("미국 고용지표 발표 대기 경계감")
        tags.append("#미고용지표대기")
    if '환율' in all_text or '달러' in all_text:
        macro_items.append("원/달러 환율 변동")
        tags.append("#환율변동성")

    macro_str = ", ".join(macro_items[:2]) if macro_items else "대외 매크로 변수와 관망 심리"

    if is_live:
        if abs(kp_r) < 0.3:
            s1 = f"{macro_str}이 발목을 잡으며 코스피는 {kp_p:,.2f}pt({kp_r:+.2f}%) 선에서 뚜렷한 방향성 없이 보합권 등락을 이어가고 있습니다."
        elif kp_r > 0:
            s1 = f"{macro_str}에도 불구하고 코스피는 {kp_p:,.2f}pt({kp_r:+.2f}%)로 상승세를 나타내며 지수 하방을 견고히 지지하고 있습니다."
        else:
            s1 = f"{macro_str}이 하방 압력으로 작용하며 코스피가 {kp_p:,.2f}pt({kp_r:+.2f}%)로 후퇴해 약세 흐름을 보이고 있습니다."
    else:
        if abs(kp_r) < 0.3:
            s1 = f"{macro_str}의 영향으로 코스피는 {kp_p:,.2f}pt({kp_r:+.2f}%) 보합권에서 장을 마쳤습니다."
        elif kp_r > 0:
            s1 = f"{macro_str} 속에서도 매수세가 유입되며 코스피는 {kp_p:,.2f}pt({kp_r:+.2f}%) 상승 마감했습니다."
        else:
            s1 = f"{macro_str}에 따른 투자심리 위축으로 코스피는 {kp_p:,.2f}pt({kp_r:+.2f}%) 하락 마감했습니다."
    sentences.append(s1)

    # 2. 섹터 & 기사 핵심 팩트
    if any(k in all_text for k in ['900선', '900']) and '코스닥' in all_text:
        tags.append("#코스닥900선공방")
        if is_live:
            s2 = f"코스닥 지수는 {kd_p:,.2f}pt({kd_r:+.2f}%)를 기록하며 장중 900선 돌파 및 안착을 시도하는 등 양대 지수 간 뚜렷한 차별화 장세가 두드러지고 있습니다."
        else:
            s2 = f"코스닥 지수는 {kd_p:,.2f}pt({kd_r:+.2f}%)로 마감하며 900선 공방 속 양대 지수 간 차별화 장세가 나타났습니다."
    elif any(k in all_text for k in ['반도체', '삼성전자', '삼전', '하이닉스']):
        tags.append("#반도체대형주흐름")
        if is_live:
            s2 = "반도체 대표주(삼성전자, SK하이닉스)와 시총 상위 대형주들이 업종별로 엇갈린 주가 흐름을 보이며 차익실현 매물을 소화하고 있습니다."
        else:
            s2 = "반도체 대표주와 시총 상위 대형주들이 엇갈린 주가 흐름을 나타내며 업종별 순환매 장세로 장을 마쳤습니다."
    else:
        if is_live:
            s2 = "시가총액 상위 대형주 전반에서 실적 모멘텀과 밸류에이션 매력도에 따른 종목별 순환매가 전개되고 있습니다."
        else:
            s2 = "대형주 전반에서 개별 실적 모멘텀에 따른 차별화 순환매가 전개되었습니다."
    sentences.append(s2)

    # 3. 수급 주체 동향 (실제 외국인/기관 수치 결합)
    if kp_for != 0 or kp_inst != 0:
        for_str = f"외국인이 {kp_for:+,.0f}억원"
        inst_str = f"기관이 {kp_inst:+,.0f}억원"
        if kp_for < 0 and kp_inst < 0:
            tags.append("#외인기관동반매도")
            if is_live:
                s3 = f"수급 측면에서는 유가증권시장에서 {for_str}, {inst_str} 규모의 동반 순매도세가 출회되어 지수 반등의 탄력을 제한하고 있습니다."
            else:
                s3 = f"수급 측면에서는 유가증권시장에서 {for_str}, {inst_str} 규모의 동반 순매도가 출회되며 장 막판까지 지수 상단을 제약했습니다."
        elif kp_for > 0 and kp_inst > 0:
            tags.append("#외인기관쌍끌이")
            if is_live:
                s3 = f"수급 측면에서는 유가증권시장에서 {for_str}, {inst_str} 규모의 쌍끌이 순매수가 유입되며 지수 상승 탄력을 견인하고 있습니다."
            else:
                s3 = f"수급 측면에서는 유가증권시장에서 {for_str}, {inst_str} 규모의 쌍끌이 순매수가 유입되며 견조한 상승세를 이끌었습니다."
        elif kp_for < 0:
            tags.append("#외인순매도")
            if is_live:
                s3 = f"수급 측면에서는 {for_str} 규모의 순매도세가 이어지는 가운데, 기관과 개인이 매물을 분할 흡수하며 치열한 수급 공방을 벌이고 있습니다."
            else:
                s3 = f"수급 측면에서는 {for_str} 규모의 순매도가 지속된 가운데 기관이 방어적 매수에 나서며 장을 마쳤습니다."
        else:
            tags.append("#외인순매수")
            if is_live:
                s3 = f"수급 측면에서는 {for_str} 규모의 외국인 매수 우위가 지수 하방을 지지하는 핵심 버팀목 역할을 하고 있습니다."
            else:
                s3 = f"수급 측면에서는 {for_str} 규모의 외국인 순매수가 유입되며 지수 하방을 지지했습니다."
    else:
        if is_live:
            s3 = "장중 투자 주체 간 뚜렷한 방향성 베팅이 엇갈리며 프로그램 매매 추이에 따라 지수 등락이 좌우되고 있습니다."
        else:
            s3 = "투자 주체 간 뚜렷한 방향성 베팅이 부재한 가운데 프로그램 매매 추이에 따라 등락을 마쳤습니다."
    sentences.append(s3)

    # 4. 결론 및 관전 포인트
    if is_live:
        s4 = "시장 참여자들은 대외 매크로 불확실성과 오후장 수급 주체들의 추가 포지션 변화를 주시하며 신중한 대응을 이어가고 있습니다."
    else:
        s4 = "결과적으로 향후 발표될 대외 거시경제 지표 결과와 3분기 기업 실적 가이던스가 시장의 추가 반등 동력을 결정할 핵심 관전 포인트입니다."
    sentences.append(s4)

    if not tags:
        tags = ["#국내증시", "#시황동향", "#수급체크"]

    return {
        'sentences': sentences,
        'tags': tags[:4]
    }


def generate_us_drivers_nlp(news_list, us_data=None, is_live=False):
    """미국 시장 핵심 동인 3~4문장 지능형 추출 알고리즘 (Yahoo Finance 기사 및 시장 수치 기반)"""
    indices = (us_data or {}).get('indices', {})
    macro = (us_data or {}).get('macro', {})

    sp500 = indices.get('^GSPC', {})
    nasdaq = indices.get('^IXIC', {})
    tnx = macro.get('^TNX', {})

    sp_ratio = sp500.get('ratio', 0.0)
    nasdaq_ratio = nasdaq.get('ratio', 0.0)
    tnx_val = tnx.get('price', 4.0)
    tnx_chg = tnx.get('change', 0.0)

    all_titles = " ".join([n.get('title', '') for n in news_list]).lower()

    sentences = []
    tags = []

    # 1문장: 국채금리 및 거시 환경 요인
    has_yield_drop = any(w in all_titles for w in ['yields fall', 'recede', 'slump', 'drop', 'lower']) or tnx_chg < -0.01
    has_yield_rise = any(w in all_titles for w in ['rising treasury', 'yields climb', 'higher yields']) or tnx_chg > 0.03

    if has_yield_drop:
        tags.append("#국채금리안정")
        if is_live:
            sentences.append(f"치솟던 미 국채 10년물 금리가 {tnx_val:.2f}% 선에서 하향 안정세를 나타내며, 기술주 및 지수 전반에 우호적인 투자 환경을 제공하고 있습니다.")
        else:
            sentences.append(f"치솟던 미 국채 10년물 금리가 {tnx_val:.2f}% 선에서 하향 안정세를 나타내며, 증시 전반에 가해지던 긴축 경계감과 밸류에이션 부담을 덜어주었습니다.")
    elif has_yield_rise:
        tags.append("#미국채금리상승")
        if is_live:
            sentences.append(f"미 국채 10년물 금리가 {tnx_val:.2f}% 수준으로 상승 압력을 가하며 고밸류에이션 기술주 및 지수 상단에 부담 요인으로 작용하고 있습니다.")
        else:
            sentences.append(f"미 국채 10년물 금리가 {tnx_val:.2f}% 수준으로 상승 압력을 가하며 고밸류에이션 기술주 및 지수 상단에 부담 요인으로 작용했습니다.")
    elif 'fed' in all_titles or 'inflation' in all_titles:
        tags.append("#연준정책주시")
        if is_live:
            sentences.append("연준의 차기 금리 정책 경로와 주요 거시 경제 지표를 둘러싼 시장의 경계감이 지속되며 조심스러운 관망세가 형성되고 있습니다.")
        else:
            sentences.append("연준의 차기 금리 정책 경로와 주요 거시 경제 지표를 둘러싼 시장의 경계감이 지속되며 관망 심리가 형성되었습니다.")
    else:
        tags.append("#매크로관망")
        if is_live:
            sentences.append(f"미 국채 10년물 금리가 {tnx_val:.2f}% 부근에서 안정적인 흐름을 유지하며 대외 매크로 변수를 소화하는 양상을 나타내고 있습니다.")
        else:
            sentences.append(f"미 국채 10년물 금리가 {tnx_val:.2f}% 부근에서 안정적인 흐름을 유지하며 대외 매크로 변수를 소화하는 양상을 보였습니다.")

    # 2문장: 기업 실적 및 반도체/빅테크 흐름
    has_chip = any(w in all_titles for w in ['chip', 'semiconductor', 'micron', 'nvidia', 'sox'])
    has_tech = any(w in all_titles for w in ['tech', 'nasdaq', 'apple', 'microsoft'])

    if has_chip:
        if any(w in all_titles for w in ['reverses', 'gain', 'comeback', 'rise']) or nasdaq_ratio >= 0:
            tags.append("#반도체저가매수")
            if is_live:
                sentences.append("마이크론 등 주요 반도체 기업들의 반등과 함께 핵심 기술주를 중심으로 저가 매수세가 유입되며 나스닥 지수의 하방을 단단히 지지하고 있습니다.")
            else:
                sentences.append("마이크론 등 주요 반도체 기업들의 반등과 함께 핵심 기술주를 중심으로 저가 매수세가 유입되며 나스닥 지수의 하방을 단단히 지지했습니다.")
        else:
            tags.append("#기술주변동성")
            if is_live:
                sentences.append("반도체 및 하드웨어 섹터 내 차익 실현 매물이 출회되며 기술주 중심의 장중 변동성이 이어지고 있습니다.")
            else:
                sentences.append("반도체 및 하드웨어 섹터 내 차익 실현 매물이 출회되며 기술주 중심의 변동성이 이어졌습니다.")
    elif has_tech or nasdaq_ratio > 0.3:
        tags.append("#빅테크반등")
        if is_live:
            sentences.append("인공지능(AI) 및 대형 테크 기업들을 향한 투자 심리가 회복세를 보이며 지수 상승 전환의 견인차 역할을 하고 있습니다.")
        else:
            sentences.append("인공지능(AI) 및 대형 테크 기업들을 향한 투자 심리가 회복세를 보이며 지수 상승 전환의 견인차 역할을 했습니다.")
    else:
        tags.append("#대형주차별화")
        if is_live:
            sentences.append("시가총액 상위 대형주 내에서 실적 전망과 밸류에이션 매력도에 따른 뚜렷한 업종별 차별화 장세가 전개되고 있습니다.")
        else:
            sentences.append("시가총액 상위 대형주 내에서 실적 전망과 밸류에이션 매력도에 따른 뚜렷한 업종별 차별화 장세가 전개되었습니다.")

    # 3문장: 지수 종합 흐름 및 투자 심리
    has_comeback = any(w in all_titles for w in ['comeback', 'rebound', 'slips', 'flat', 'rise']) or sp_ratio > 0
    if has_comeback and sp_ratio >= 0:
        tags.append("#뉴욕증시컴백")
        if is_live:
            sentences.append("장 초반의 변동성과 하락 압력을 딛고 매수세가 유입되며 주요 지수가 견조한 반등 흐름을 이어가고 있습니다.")
        else:
            sentences.append("장 초반의 변동성과 하락 압력을 딛고 장 후반으로 갈수록 매수세가 결집하며 주요 지수가 극적인 반등(컴백)에 성공했습니다.")
    elif sp_ratio < 0:
        tags.append("#지수상단제한")
        if is_live:
            sentences.append("고금리 장기화 리스크와 경기 둔화 우려 속에 지수 상단이 제한되며 조심스러운 박스권 흐름이 이어지고 있습니다.")
        else:
            sentences.append("고금리 장기화 리스크와 경기 둔화 우려 속에 지수 상단이 제한되며 조심스러운 박스권 흐름이 이어졌습니다.")
    else:
        tags.append("#보합권공방")
        if is_live:
            sentences.append("투자 주체 간 뚜렷한 방향성 베팅이 엇갈리며 보합권 공방 속에 시장의 지지력을 다지는 흐름을 나타내고 있습니다.")
        else:
            sentences.append("투자 주체 간 뚜렷한 방향성 베팅이 엇갈리며 보합권 공방 속에 시장의 지지력을 다지는 흐름을 나타냈습니다.")

    # 4문장: 결론 및 관전 포인트
    if is_live:
        sentences.append("결과적으로 투자자들은 채권 금리의 추가 변동성과 주요 고용·물가 지표를 주시하며 신중한 대응을 이어가고 있습니다.")
    else:
        sentences.append("결과적으로 투자자들은 채권 금리의 추가 안정 여부와 향후 예정된 주요 고용·물가 지표를 주시하며 신중한 대응을 이어가고 있습니다.")

    if not tags:
        tags = ["#뉴욕증시", "#야후파이낸스", "#월가동향"]

    return {
        'sentences': sentences,
        'tags': tags[:4]
    }


def parse_ai_response(text: str):
    """AI 모델 응답 텍스트를 문장 리스트와 태그로 파싱"""
    if not text:
        return {'sentences': [], 'tags': []}

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    sentences = []
    tags = []

    for line in lines:
        if line.startswith('#'):
            for tag in line.split():
                if tag.startswith('#'):
                    tags.append(tag)
        else:
            # 서두 안내문구 필터링 (예: "오늘의 시장 브리핑입니다")
            if any(intro in line for intro in ['브리핑입니다', '요약입니다', '요약해 드립니다', '다음과 같습니다', '핵심 동인:']):
                continue

            clean = line
            # 번호나 불릿 제거
            for prefix in ['1.', '2.', '3.', '4.', '1)', '2)', '3)', '4)', '-', '•', '*']:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):].strip()
            # 볼드 마크다운 제거
            clean = clean.replace('**', '').strip()
            if len(clean) >= 20:
                sentences.append(clean)

    if not tags:
        tags = ["#시장핵심동인", "#시황브리핑", "#투자체크"]
    return {
        'sentences': sentences[:4],
        'tags': tags[:4]
    }


def get_krx_market_drivers(krx_data=None, is_live=False):
    """
    한국 증시(KRX) 오늘의 시장을 움직인 핵심 동인 브리핑 & 대표 뉴스 3선
    """
    top_news = fetch_krx_top_news(count=3)
    api_key = get_gemini_api_key()
    today_date = (krx_data or {}).get('date', '')

    kospi = (krx_data or {}).get('kospi', {})
    kosdaq = (krx_data or {}).get('kosdaq', {})
    inv_kp = (krx_data or {}).get('investors_kospi', {})
    inv_prev = (krx_data or {}).get('investors_kospi_prev', {})
    kp_p = kospi.get('price', 0.0)
    kp_r = kospi.get('ratio', 0.0)
    kd_p = kosdaq.get('price', 0.0)
    kd_r = kosdaq.get('ratio', 0.0)
    kp_for = inv_kp.get('foreign', 0.0)
    kp_inst = inv_kp.get('institutional', 0.0)

    effective_date = today_date
    if not is_live:
        if kospi.get('date'):
            effective_date = kospi.get('date')
        elif inv_prev.get('date'):
            effective_date = f"20{inv_prev.get('date')}" if len(inv_prev.get('date', '')) == 8 else inv_prev.get('date')

        # 개장 전(PRE_MARKET), 휴장일 또는 당일 수급이 아직 집계되지 않은 경우 직전 마감 확정치로 통일
        if (kp_for == 0.0 and kp_inst == 0.0) and inv_prev:
            kp_for = inv_prev.get('foreign', 0.0)
            kp_inst = inv_prev.get('institutional', 0.0)
            inv_kp = inv_prev

    if api_key and top_news:
        news_context = "\n".join([f"- [{n['press']}] {n['title']}: {n['summary'][:120]}" for n in top_news])

        market_mode_str = (
            "현재 한국 증시는 정규장 진행 중(실시간 장중)입니다. "
            "반드시 현재 진행형 시제(~하고 있습니다, ~나타내고 있습니다, ~공방을 벌이고 있습니다 등)로 서술해 주시고, "
            "마감형(~마감했습니다, ~장을 마쳤습니다 등) 시제를 사용하지 마세요."
            if is_live else
            f"현재 한국 증시는 정규장 개장 전 또는 마감 상태입니다. 직전 거래일({effective_date}) 마감 기준의 확정 데이터이므로 반드시 마감형 시제(~마감했습니다, ~작용했습니다, ~마쳤습니다 등)로 서술해 주세요."
        )

        prompt = f"""
당신은 국내 최고 금융기관의 수석 시장 전략가입니다.
{market_mode_str}
[시장 데이터]: 코스피 {kp_p:,.2f}pt({kp_r:+.2f}%), 코스닥 {kd_p:,.2f}pt({kd_r:+.2f}%), 외국인 순매매 {kp_for:+,.0f}억원, 기준일자: {effective_date}

아래는 네이버 증권에서 수집된 핵심 시황 뉴스 3편의 정보입니다:
{news_context}

위 기사들의 구체적 팩트(국제유가, 국채금리, 고용지표, 대형주/반도체 동향 등)와 시장 데이터(코스피/코스닥 등락률 및 외국인 순매매 수치: {kp_for:+,.0f}억원)를 유기적으로 종합하여, {effective_date} 한국 증시의 흐름을 이끈 '핵심적인 동적 요인(Market Drivers)'을 인과관계 중심으로 3~4문장의 유려하고 전문적인 한국어로 브리핑해 주세요.
(주의: 직전 거래일 기준 외국인 순매매는 {kp_for:+,.0f}억원이므로 결코 '0원'이나 '관망세'로 설명하지 말고 실제 수치인 {kp_for:+,.0f}억원의 매매 동향을 있는 그대로 반영해 주세요.)
반드시 아래 형식에 맞추어 작성해 주세요:
1. (첫 번째 핵심 동인 문장)
2. (두 번째 핵심 동인 문장)
3. (세 번째 핵심 동인 문장)
4. (네 번째 핵심 동인 문장)
#핵심태그1 #핵심태그2 #핵심태그3
""".strip()
        ai_resp = call_gemini_generate(prompt, api_key)
        if ai_resp:
            parsed = parse_ai_response(ai_resp)
            if len(parsed['sentences']) >= 2:
                return {
                    'sentences': parsed['sentences'],
                    'tags': parsed['tags'],
                    'articles': top_news,
                    'engine': 'Gemini AI'
                }

    # Fallback to smart NLP engine
    nlp_res = generate_krx_drivers_nlp(top_news, krx_data, is_live=is_live)
    return {
        'sentences': nlp_res['sentences'],
        'tags': nlp_res['tags'],
        'articles': top_news,
        'engine': 'Smart Engine'
    }


def get_us_market_drivers(us_data=None, is_live=False):
    """
    미국 증시(US) 오늘의 시장을 움직인 핵심 동인 브리핑 & 대표 뉴스 3선
    """
    top_news = fetch_us_top_news(count=3)
    api_key = get_gemini_api_key()
    today_date = (us_data or {}).get('date', '')

    if api_key and top_news:
        news_context = "\n".join([f"- [{n['press']}] {n['title']}" for n in top_news])
        indices = (us_data or {}).get('indices', {})
        sp_ratio = indices.get('^GSPC', {}).get('ratio', 0.0)
        nasdaq_ratio = indices.get('^IXIC', {}).get('ratio', 0.0)
        macro = (us_data or {}).get('macro', {})
        tnx_rate = macro.get('^TNX', {}).get('price', 0.0)

        market_mode_str = (
            "현재 미국 증시는 정규장 진행 중(실시간)입니다. 반드시 현재 진행형 시제(~하고 있습니다, ~이어지고 있습니다 등)로 서술해 주세요."
            if is_live else
            "현재 미국 증시는 정규장 마감 상태입니다. 마감형 시제(~마감했습니다, ~장을 마쳤습니다 등)로 서술해 주세요."
        )

        prompt = f"""
당신은 월가 수석 시황 애널리스트입니다.
{market_mode_str}
아래는 오늘({today_date}) Yahoo Finance에서 수집된 뉴욕 증시 핵심 기사 3편의 헤드라인과 시장 데이터입니다.
- S&P 500: {sp_ratio:+.2f}%, 나스닥: {nasdaq_ratio:+.2f}%, 미 10년물 국채금리: {tnx_rate:.2f}%
{news_context}

오늘 미국 증시의 흐름(상승/하락/혼조)을 이끈 '핵심적인 동적 요인(Market Drivers)'을 위 기사들의 구체적인 사실을 반영하여 인과관계 중심으로 3~4문장의 전문적인 한국어로 브리핑해 주세요.
반드시 아래 형식에 맞추어 작성해 주세요:
1. (첫 번째 핵심 동인 문장)
2. (두 번째 핵심 동인 문장)
3. (세 번째 핵심 동인 문장)
4. (네 번째 핵심 동인 문장)
#핵심태그1 #핵심태그2 #핵심태그3
""".strip()
        ai_resp = call_gemini_generate(prompt, api_key)
        if ai_resp:
            parsed = parse_ai_response(ai_resp)
            if len(parsed['sentences']) >= 2:
                return {
                    'sentences': parsed['sentences'],
                    'tags': parsed['tags'],
                    'articles': top_news,
                    'engine': 'Gemini AI'
                }

    # Fallback to smart NLP engine
    nlp_res = generate_us_drivers_nlp(top_news, us_data, is_live=is_live)
    return {
        'sentences': nlp_res['sentences'],
        'tags': nlp_res['tags'],
        'articles': top_news,
        'engine': 'Smart Engine'
    }
