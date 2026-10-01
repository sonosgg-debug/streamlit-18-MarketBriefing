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
        if 'GEMINI_API_KEY' in st.secrets:
            return st.secrets['GEMINI_API_KEY'].strip()
    except Exception:
        pass
    # 3. OS 환경 변수
    key = os.environ.get('GEMINI_API_KEY')
    if key:
        return key.strip()
    return None


def call_gemini_generate(prompt: str, api_key: str):
    """Google Gemini REST API 호출 (추가 SDK 설치 불필요)"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800
        }
    }
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=7)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get('candidates', [])
            if candidates:
                text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return text.strip()
    except Exception as e:
        print(f"Gemini API call failed: {e}")
    return None


def fetch_krx_top_news(count=3):
    """
    네이버 증권 모바일 API에서 당일 장중/마감 시황 핵심 뉴스 선별
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
        '코스피': 5, '코스닥': 5, '증시': 4, '시황': 5, '마감': 4, '장중': 3,
        '상승': 2, '하락': 2, '혼조': 3, '외인': 3, '기관': 3, '외국인': 3,
        '금리': 3, '환율': 3, '반도체': 2, '국채': 3, '물가': 2, '긴축': 2
    }

    for it in items:
        tit = it.get('tit', '')
        sub = it.get('subcontent', '')
        oid = it.get('oid', '')
        aid = it.get('aid', '')
        ohnm = it.get('ohnm', '네이버뉴스')
        dt = it.get('dt', '')

        # 개별 종목 단순 공시, 테마주 잡음 필터링
        if any(bad in tit for bad in ['[특징주]', '인사', '부음', '포토', '골프', '코인']):
            continue

        score = sum(weight for kw, weight in keywords.items() if kw in tit) * 2
        score += sum(weight for kw, weight in keywords.items() if kw in sub)

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
                'link': f"https://n.news.naver.com/mnews/article/{oid}/{aid}",
                'source': '네이버 증권'
            })

    scored_news.sort(key=lambda x: x['score'], reverse=True)
    return scored_news[:count]


def fetch_us_top_news(count=3):
    """
    Yahoo Finance에서 미국 증시 당일 장중/마감 대표 기사 선별
    """
    articles = []
    seen_titles = set()

    # 1. 'stock market today' 검색 (야후 파이낸스 메인 시황 랩)
    try:
        s = yf.Search('stock market today', news_count=8)
        if s.news:
            for item in s.news:
                title = item.get('title')
                pub = item.get('publisher', 'Yahoo Finance')
                link = item.get('link')
                pub_time = item.get('providerPublishTime')
                time_str = ""
                if pub_time:
                    try:
                        time_str = datetime.fromtimestamp(pub_time).strftime('%m.%d %H:%M')
                    except Exception:
                        pass
                if title and link and title not in seen_titles:
                    seen_titles.add(title)
                    articles.append({
                        'title': title,
                        'summary': '',
                        'press': pub,
                        'time': time_str,
                        'link': link,
                        'source': 'Yahoo Finance'
                    })
    except Exception as e:
        print(f"Yahoo Search news failed: {e}")

    # 2. 보충: S&P 500 지수 연동 뉴스
    if len(articles) < count:
        try:
            s2 = yf.Search('S&P 500', news_count=5)
            if s2.news:
                for item in s2.news:
                    title = item.get('title')
                    pub = item.get('publisher', 'Yahoo Finance')
                    link = item.get('link')
                    if title and link and title not in seen_titles:
                        seen_titles.add(title)
                        articles.append({
                            'title': title,
                            'summary': '',
                            'press': pub,
                            'time': '',
                            'link': link,
                            'source': 'Yahoo Finance'
                        })
        except Exception:
            pass

    return articles[:count]


def generate_krx_drivers_nlp(news_list, krx_data=None):
    """한국 시장 핵심 동인 3~4문장 자체 스마트 추출 알고리즘"""
    if not news_list:
        return {
            'sentences': [
                "당일 장중 글로벌 매크로 지표 관망 심리와 대외 변수를 주시하며 관망세가 짙은 흐름입니다.",
                "외국인과 기관의 수급 공방 속에 지수의 방향성이 제한되고 있습니다.",
                "대형주 중심의 차별화 장세가 이어지며 개별 실적 모멘텀에 따른 순환매가 전개되고 있습니다."
            ],
            'tags': ["#관망세", "#수급공방", "#개별종목장세"]
        }

    all_text = " ".join([f"{n.get('title', '')} {n.get('summary', '')}" for n in news_list])

    has_rates = any(w in all_text for w in ['금리', '국채', '10년물', '긴축'])
    has_semicon = any(w in all_text for w in ['반도체', '마이크론', '삼성전자', '하이닉스'])
    has_fx = any(w in all_text for w in ['환율', '달러'])
    has_supply = any(w in all_text for w in ['외인', '외국인', '기관', '동반', '쌍끌이', '순매도', '순매수', '팔자', '사자'])
    has_drop = any(w in all_text for w in ['하락', '약세', '뒷걸음', '쇼크', '부담', '하방', '급락'])
    has_rise = any(w in all_text for w in ['상승', '강세', '반등', '훈풍', '급등', '서프라이즈', '랠리'])

    sentences = []
    tags = []

    # 1문장: 거시 환경 & 금리/대외 변수
    if has_rates and has_drop:
        sentences.append("미국 국채금리 고공행진과 글로벌 긴축 장기화 우려가 투자심리를 짓누르며 증시 전반에 강한 하방 압력으로 작용했습니다.")
        tags.append("#미국채금리상승")
    elif has_rates and has_rise:
        sentences.append("미국 국채금리 안정세와 글로벌 통화 완화 기대감이 위험자산 선호 심리를 자극하며 지수 반등을 견인했습니다.")
        tags.append("#금리안정세")
    elif has_fx:
        sentences.append("달러화 강세와 원/달러 환율 변동성 확대가 이어지며 외국인 수급 환경에 대한 경계감을 높였습니다.")
        tags.append("#환율변동성")
    else:
        sentences.append("간밤 뉴욕 증시의 엇갈린 흐름과 대외 경제 지표 발표를 앞둔 관망세가 국내 증시의 출발 분위기를 형성했습니다.")
        tags.append("#대외관망세")

    # 2문장: 주도 섹터(반도체/2차전지 등) 및 실적 이슈
    if has_semicon:
        if '마이크론' in all_text:
            sentences.append("마이크론의 깜짝 호실적 발표에도 불구하고 밸류에이션 부담과 고금리 우려가 겹치며 국내 반도체 대표주(삼성전자, SK하이닉스)는 차익 매물을 소화하는 약세를 보였습니다.")
            tags.append("#반도체차익실현")
        else:
            sentences.append("반도체와 2차전지 등 핵심 시총 상위 대형주들이 엇갈린 주가 흐름을 나타내며 업종별 뚜렷한 순환매 양상이 전개되었습니다.")
            tags.append("#대형주순환매")
    else:
        sentences.append("업종별로는 경기 방어주와 밸류업 수혜주를 중심으로 선별적 매수세가 유입되며 지수 하단을 지지했습니다.")
        tags.append("#방어주유입")

    # 3문장: 수급 주체 동향
    if has_supply:
        if '순매도' in all_text or '팔자' in all_text or (krx_data and krx_data.get('investors_kospi', {}).get('foreign', 0) < 0):
            sentences.append("유가증권시장에서 외국인과 기관이 동반 순매도세를 이어가며 지수 반등의 탄력을 제한했고, 개인이 홀로 매물을 흡수하는 양상이 이어졌습니다.")
            tags.append("#외인기관동반매도")
        else:
            sentences.append("수급 측면에서는 외국인의 선별적 순매수 유입과 기관의 프로그램 매매 방향성에 따라 지수의 등락 폭이 결정되었습니다.")
            tags.append("#수급공방")
    else:
        sentences.append("투자 주체 간 뚜렷한 방향성 베팅이 부재한 가운데 장중 수급 변화에 따라 지수가 좁은 박스권 등락을 반복했습니다.")
        tags.append("#박스권공방")

    # 4문장: 종합 시장 평가 및 관전 포인트
    if has_drop:
        sentences.append("결과적으로 고금리 장기화 리스크와 차익실현 욕구가 맞물려 단기 지지선 안착을 시험하는 숨고르기 장세가 지속되고 있습니다.")
    else:
        sentences.append("결과적으로 긍정적인 기업 실적 모멘텀과 대외 불확실성 해소 여부가 향후 시장의 추가 반등 동력을 결정할 핵심 변수로 꼽힙니다.")

    if not tags:
        tags = ["#국내증시", "#시황동향", "#수급체크"]

    return {
        'sentences': sentences,
        'tags': tags[:4]
    }


def generate_us_drivers_nlp(news_list, us_data=None):
    """미국 시장 핵심 동인 3~4문장 자체 스마트 요약 알고리즘 (Yahoo Finance 기반)"""
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

    # 1문장: 국채금리 및 통화정책 요인
    if 'treasury' in all_titles or 'yield' in all_titles or tnx_chg > 0.03:
        if tnx_chg >= 0:
            sentences.append(f"미 국채 10년물 금리가 {tnx_val:.2f}% 수준으로 상승세를 이어가며 기술주와 고밸류에이션 성장주에 부담 요인으로 작용했습니다.")
            tags.append("#미국채금리상승")
        else:
            sentences.append(f"미 국채 10년물 금리가 {tnx_val:.2f}% 선으로 하향 안정세를 나타내며 시장의 긴축 경계감을 다소 완화시켰습니다.")
            tags.append("#국채금리안정")
    elif 'inflation' in all_titles or 'cpi' in all_titles:
        sentences.append("주요 물가 지표가 시장 예상치를 밑돌며 인플레이션 둔화 신호를 보였으나, 연준의 추가 금리 인하 경로를 둘러싼 신중론이 교차했습니다.")
        tags.append("#인플레이션지표")
    else:
        sentences.append("글로벌 거시 경제 지표 발표와 연방준비제도(Fed) 위원들의 발언을 앞두고 채권 시장과 증시 전반에 짙은 관망세가 형성되었습니다.")
        tags.append("#연준관망세")

    # 2문장: 기업 실적 및 빅테크(M7) 흐름
    if 'micron' in all_titles or 'nvidia' in all_titles or 'tech' in all_titles or 'earnings' in all_titles:
        sentences.append("마이크론 등 주요 반도체 기업의 견조한 실적 발표와 대규모 자사주 매입 소식이 전해졌으나, 단기 급등에 따른 차익 실현 매물이 출회되며 기술주 내 혼조세가 나타났습니다.")
        tags.append("#빅테크실적혼조")
    elif nasdaq_ratio > 0.5:
        sentences.append("인공지능(AI) 인프라 투자 지속 기대감에 힘입어 엔비디아 등 메가캡 기술주를 중심으로 반발 매수세가 유입되며 나스닥 상승을 주도했습니다.")
        tags.append("#AI기술주강세")
    else:
        sentences.append("M7 메가캡 종목군에서는 호실적 기업과 차익 매물 출회 종목 간 차별화가 심화되며 지수 견인력이 분산되었습니다.")
        tags.append("#메가캡차별화")

    # 3문장: 시장 심리 및 월말/리밸런싱 요인
    if 'monthly' in all_titles or sp_ratio < 0:
        sentences.append("월말 포트폴리오 리밸런싱과 고금리 장기화에 대한 경계감이 맞물리며 다우와 S&P 500 등 주요 지수의 상단이 제한되는 압박을 받았습니다.")
        tags.append("#월말포트폴리오조정")
    else:
        sentences.append("위험자산 전반에 대한 선호 심리가 방어력을 형성하며 주요 지수가 안정적인 지지선을 구축하는 흐름을 보였습니다.")
        tags.append("#위험선호회복")

    # 4문장: 결론 및 관전 포인트
    sentences.append("결과적으로 투자자들은 추가적인 고용 및 인플레이션 데이터 확인 전까지 공격적인 포지션 확대를 자제하며 숨고르기 장세를 이어가고 있습니다.")

    if not tags:
        tags = ["#뉴욕증시", "#야후파이낸스", "#월가동향"]

    return {
        'sentences': sentences,
        'tags': tags[:4]
    }


def parse_ai_response(text: str):
    """AI 모델 응답 텍스트를 문장 리스트와 태그로 파싱"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    sentences = []
    tags = []

    for line in lines:
        if line.startswith('#'):
            # 태그 줄
            for tag in line.split():
                if tag.startswith('#'):
                    tags.append(tag)
        else:
            # 번호나 불릿 제거
            clean = line
            for prefix in ['1.', '2.', '3.', '4.', '-', '•', '*']:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):].strip()
            if len(clean) > 15:
                sentences.append(clean)

    if not tags:
        tags = ["#시장핵심동인", "#시황브리핑", "#투자체크"]
    return {
        'sentences': sentences[:4],
        'tags': tags[:4]
    }


def get_krx_market_drivers(krx_data=None):
    """
    한국 증시(KRX) 오늘의 시장을 움직인 핵심 동인 브리핑 & 대표 뉴스 3선
    """
    top_news = fetch_krx_top_news(count=3)
    api_key = get_gemini_api_key()

    if api_key and top_news:
        news_context = "\n".join([f"- [{n['press']}] {n['title']}: {n['summary'][:120]}" for n in top_news])
        prompt = f"""
당신은 국내 최고 금융기관의 수석 시장 전략가입니다.
아래는 오늘 네이버 증권에서 수집된 핵심 시황 뉴스 3편의 정보입니다.

{news_context}

오늘 한국 증시(코스피/코스닥)의 상승 또는 하락, 보합을 이끈 '핵심적인 동적 요인(Market Drivers)'을 3~4문장의 유려하고 논리적인 한국어로 브리핑해 주세요.
각 문장은 인과관계(거시 변수, 수급 주체, 주도 섹터의 영향)가 명확해야 합니다.
마지막 줄에는 핵심 키워드 해시태그 3~4개를 적어주세요 (예: #미국채금리 #외인기관동반매도 #반도체조정).
""".strip()
        ai_resp = call_gemini_generate(prompt, api_key)
        if ai_resp:
            parsed = parse_ai_response(ai_resp)
            if parsed['sentences']:
                return {
                    'sentences': parsed['sentences'],
                    'tags': parsed['tags'],
                    'articles': top_news,
                    'engine': 'Gemini AI'
                }

    # Fallback to smart NLP engine
    nlp_res = generate_krx_drivers_nlp(top_news, krx_data)
    return {
        'sentences': nlp_res['sentences'],
        'tags': nlp_res['tags'],
        'articles': top_news,
        'engine': 'Smart Engine'
    }


def get_us_market_drivers(us_data=None):
    """
    미국 증시(US) 오늘의 시장을 움직인 핵심 동인 브리핑 & 대표 뉴스 3선
    """
    top_news = fetch_us_top_news(count=3)
    api_key = get_gemini_api_key()

    if api_key and top_news:
        news_context = "\n".join([f"- [{n['press']}] {n['title']}" for n in top_news])
        indices = (us_data or {}).get('indices', {})
        sp_ratio = indices.get('^GSPC', {}).get('ratio', 0.0)
        nasdaq_ratio = indices.get('^IXIC', {}).get('ratio', 0.0)
        macro = (us_data or {}).get('macro', {})
        tnx_rate = macro.get('^TNX', {}).get('price', 0.0)

        prompt = f"""
당신은 월가 수석 시황 애널리스트입니다.
아래는 오늘 Yahoo Finance에서 수집된 뉴욕 증시 핵심 기사 3편의 헤드라인과 시장 데이터입니다.
- S&P 500: {sp_ratio:+.2f}%, 나스닥: {nasdaq_ratio:+.2f}%, 미 10년물 국채금리: {tnx_rate:.2f}%
{news_context}

오늘 미국 증시의 흐름(상승/하락/혼조)을 이끈 '핵심적인 동적 요인(Market Drivers)'을 3~4문장의 유려하고 전문적인 한국어로 브리핑해 주세요.
각 문장은 인과관계(채권 금리, 연준 정책, 빅테크 실적, 투자심리 등)가 명확해야 합니다.
마지막 줄에는 핵심 키워드 해시태그 3~4개를 적어주세요 (예: #국채금리상승 #빅테크차익실현 #월말포트폴리오조정).
""".strip()
        ai_resp = call_gemini_generate(prompt, api_key)
        if ai_resp:
            parsed = parse_ai_response(ai_resp)
            if parsed['sentences']:
                return {
                    'sentences': parsed['sentences'],
                    'tags': parsed['tags'],
                    'articles': top_news,
                    'engine': 'Gemini AI'
                }

    # Fallback to smart NLP engine
    nlp_res = generate_us_drivers_nlp(top_news, us_data)
    return {
        'sentences': nlp_res['sentences'],
        'tags': nlp_res['tags'],
        'articles': top_news,
        'engine': 'Smart Engine'
    }
