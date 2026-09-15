"""
calendar_data.py
한국(KRX) 및 미국(US) 주요 경제 및 증시 일정 관리 모듈
실행 시점(현재 날짜)을 기준으로 다가오는 핵심 이벤트 D-Day 계산 및 큐레이션 제공
"""

from datetime import datetime, date, timedelta

# 주요 정례 일정 및 규칙 생성기
def get_upcoming_events(market='KRX', max_items=5):
    """
    market: 'KRX' 또는 'US'
    max_items: 표시할 최대 이벤트 수
    """
    today = date.today()
    events = []

    if market == 'KRX':
        # 한국 주요 예정 일정 정의
        # 1) 선물옵션 만기일 계산 (매월 둘째 목요일)
        # 2) 경제 지표 및 금통위 등
        raw_events = [
            # 2026년 기준 주요 금통위 및 경제 일정 샘플 및 동적 생성
            {"title": "한국은행 금융통화위원회 (기준금리 결정)", "month": 10, "day": 15, "impact": "High", "desc": "국내 기준금리 동결 여부 및 경기 진단 발표"},
            {"title": "한국 10월 수출입동향 잠정치 발표", "month": 11, "day": 1, "impact": "High", "desc": "반도체 및 자동차 수출 실적 모멘텀 확인"},
            {"title": "한국 9월 소비자물가지수(CPI)", "month": 10, "day": 6, "impact": "Medium", "desc": "물가 안정 추세 지속 여부 및 금리 경로 점검"},
            {"title": "삼성전자 3분기 잠정 실적 발표", "month": 10, "day": 8, "impact": "High", "desc": "반도체/HBM 영업이익 및 가이던스 확인"},
            {"title": "한국은행 금융통화위원회 (통화정책방향)", "month": 11, "day": 26, "impact": "High", "desc": "올해 마지막 기준금리 결정 및 경제전망 수정"},
            {"title": "관세청 1~20일 수출입 통계", "month": 9, "day": 21, "impact": "Medium", "desc": "월중 수출입 속보치 및 업종별 추이"},
            {"title": "한국 8월 산업활동동향", "month": 9, "day": 30, "impact": "Medium", "desc": "생산, 소비, 설비투자 경기 지표"},
        ]

        # 매월 둘째 목요일 (옵션/선물옵션 만기일) 계산
        for m in range(today.month, min(today.month + 3, 13)):
            second_thursday = get_nth_weekday(today.year, m, weekday=3, n=2) # 3: 목요일
            if second_thursday >= today:
                is_quad = (m in [3, 6, 9, 12])
                raw_events.append({
                    "title": f"{m}월 선물·옵션 동시만기일" if is_quad else f"{m}월 옵션만기일",
                    "month": m,
                    "day": second_thursday.day,
                    "impact": "High" if is_quad else "Medium",
                    "desc": "프로그램 매매 출회 및 마감 동시호가 변동성 유의"
                })

    else:
        # 미국 주요 예정 일정 정의 (US)
        raw_events = [
            {"title": "미 연준 FOMC 정례회의 (기준금리 결정)", "month": 9, "day": 16, "impact": "High", "desc": "기준금리 인하 폭 및 점도표(Dot Plot) 공개"},
            {"title": "미국 8월 소매판매(Retail Sales)", "month": 9, "day": 17, "impact": "Medium", "desc": "미국 소비 경기 및 경기 침체(R-공포) 점검"},
            {"title": "미국 8월 개인소비지출(PCE) 물가지수", "month": 9, "day": 25, "impact": "High", "desc": "연준이 가장 주목하는 핵심 물가 지표 발표"},
            {"title": "미국 9월 고용보고서 (비농업 고용 & 실업률)", "month": 10, "day": 2, "impact": "High", "desc": "노동시장 냉각 속도 및 임금 상승률 확인"},
            {"title": "미국 9월 소비자물가지수(CPI)", "month": 10, "day": 13, "impact": "High", "desc": "인플레이션 둔화 추세 지속 여부"},
            {"title": "미 연준 11월 FOMC 회의", "month": 11, "day": 5, "impact": "High", "desc": "대선 직후 금리 결정 및 제롬 파월 기자회견"},
            {"title": "마이크론 테크놀로지 실적 발표", "month": 9, "day": 25, "impact": "High", "desc": "글로벌 메모리 반도체 및 AI 수요 가늠자"},
            {"title": "엔비디아(NVDA) 3분기 실적 발표", "month": 11, "day": 18, "impact": "High", "desc": "차세대 블랙웰 칩 수요 및 AI 인프라 투자 지속성"},
        ]

        # 미국 선물옵션 동시만기일 (3, 6, 9, 12월 셋째 금요일)
        for m in [3, 6, 9, 12]:
            if m >= today.month:
                third_friday = get_nth_weekday(today.year, m, weekday=4, n=3) # 4: 금요일
                if third_friday >= today:
                    raw_events.append({
                        "title": f"미국 {m}월 쿼드러플 위칭데이 (선물옵션 만기)",
                        "month": m,
                        "day": third_friday.day,
                        "impact": "High",
                        "desc": "주가지수/개별주식 선물옵션 4종 동시 만기, 막판 거래량 급증"
                    })

    # D-Day 계산 및 미래 이벤트만 필터링
    filtered = []
    for ev in raw_events:
        try:
            ev_date = date(today.year, ev['month'], ev['day'])
            # 연말을 넘기는 경우 처리
            if ev_date < today:
                ev_date = date(today.year + 1, ev['month'], ev['day'])
            
            delta_days = (ev_date - today).days
            if delta_days >= 0:
                if delta_days == 0:
                    dday_str = "D-Day"
                    color_cls = "dday-red"
                elif delta_days == 1:
                    dday_str = "D-1"
                    color_cls = "dday-orange"
                elif delta_days <= 7:
                    dday_str = f"D-{delta_days}"
                    color_cls = "dday-blue"
                else:
                    dday_str = f"D-{delta_days}"
                    color_cls = "dday-gray"

                filtered.append({
                    "date": ev_date.strftime("%m월 %d일"),
                    "dday": dday_str,
                    "delta": delta_days,
                    "color_cls": color_cls,
                    "title": ev['title'],
                    "impact": ev.get('impact', 'Medium'),
                    "desc": ev.get('desc', '')
                })
        except Exception:
            continue

    # 날짜 빠른 순 정렬 후 max_items만큼 반환
    filtered.sort(key=lambda x: x['delta'])
    return filtered[:max_items]

def get_nth_weekday(year, month, weekday, n):
    """특정 연/월의 n번째 요일 구하기 (weekday: 0=월, 3=목, 4=금)"""
    first_day = date(year, month, 1)
    day_diff = (weekday - first_day.weekday()) % 7
    first_target_day = first_day + timedelta(days=day_diff)
    return first_target_day + timedelta(weeks=n - 1)
