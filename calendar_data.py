"""
calendar_data.py
한국(KRX) 및 미국(US) 주요 경제 및 증시 일정 관리 모듈
- 실행 시점(현재 날짜)을 기준으로 오직 다가오는 미래의 핵심 예정 사항(Upcoming Events)만 엄격 선별
- 이미 지나간 과거 일정은 연도 래핑 없이 원천 배제
- 매월 정례 경제 지표(CPI, PCE, 고용, 수출입, 소매판매 등) 및 선물옵션 만기일 동적 생성
- 미 연준 FOMC, 한국은행 금통위 등 핵심 정책 회의 및 대형주 실적 일정 통합 제공
"""

from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo


def get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """특정 연/월의 n번째 요일 구하기 (weekday: 0=월, 1=화, 2=수, 3=목, 4=금, 5=토, 6=일)"""
    first_day = date(year, month, 1)
    day_diff = (weekday - first_day.weekday()) % 7
    first_target_day = first_day + timedelta(days=day_diff)
    return first_target_day + timedelta(weeks=n - 1)


def get_last_day_of_month(year: int, month: int) -> date:
    """해당 연/월의 마지막 일자 반환"""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def get_upcoming_events(market='KRX', max_items=5, base_date=None):
    """
    시장별 미래 예정 사항(Upcoming Events)만 엄격 필터링하여 반환
    market: 'KRX' 또는 'US'
    max_items: 표시할 최대 이벤트 수 (기본 5개)
    base_date: 기준일자 (기본값: 각 증시 현지 시각 기준 오늘)
    """
    if base_date:
        if isinstance(base_date, str):
            try:
                clean_d = base_date.replace('-', '').replace('.', '')[:8]
                today = datetime.strptime(clean_d, "%Y%m%d").date()
            except Exception:
                today = date.today()
        elif isinstance(base_date, datetime):
            today = base_date.date()
        else:
            today = base_date
    else:
        try:
            tz = ZoneInfo('Asia/Seoul') if market == 'KRX' else ZoneInfo('America/New_York')
            today = datetime.now(tz).date()
        except Exception:
            offset = 9 if market == 'KRX' else -4
            today = datetime.now(timezone(timedelta(hours=offset))).date()

    candidates = []

    # 1. 정례 경제 지표 및 파생상품 만기일 동적 생성 (현재 월부터 향후 4개월)
    for offset in range(4):
        tot_month = today.month - 1 + offset
        m = (tot_month % 12) + 1
        y = today.year + (tot_month // 12)
        prev_m = 12 if m == 1 else m - 1

        if market == 'KRX':
            # ① 매월 1일: 전월 수출입동향 잠정치 발표 (산업통상자원부)
            candidates.append({
                "date": date(y, m, 1),
                "title": f"한국 {prev_m}월 수출입동향 잠정치 발표",
                "impact": "High",
                "desc": "반도체 및 자동차 수출 실적 모멘텀 확인"
            })
            # ② 매월 2일경: 전월 소비자물가지수(CPI) 발표 (통계청)
            candidates.append({
                "date": date(y, m, 2),
                "title": f"한국 {prev_m}월 소비자물가지수(CPI)",
                "impact": "High",
                "desc": "물가 안정 추세 지속 여부 및 금리 경로 점검"
            })
            # ③ 매월 둘째 목요일: 선물/옵션 만기일 (3, 6, 9, 12월은 동시만기일)
            thu2 = get_nth_weekday(y, m, weekday=3, n=2)
            is_quad = (m in [3, 6, 9, 12])
            candidates.append({
                "date": thu2,
                "title": f"{m}월 선물·옵션 동시만기일" if is_quad else f"{m}월 옵션만기일",
                "impact": "High" if is_quad else "Medium",
                "desc": "프로그램 매매 출회 및 마감 동시호가 변동성 유의"
            })
            # ④ 매월 21일: 관세청 1~20일 수출입 속보치
            candidates.append({
                "date": date(y, m, 21),
                "title": f"관세청 {m}월 1~20일 수출입 속보치",
                "impact": "Medium",
                "desc": "월중 수출입 속보치 및 반도체/자동차 업종별 추이"
            })
            # ⑤ 매월 말일: 전월 산업활동동향 (통계청)
            d_last = get_last_day_of_month(y, m)
            candidates.append({
                "date": d_last,
                "title": f"한국 {prev_m}월 산업활동동향",
                "impact": "Medium",
                "desc": "생산, 소비, 설비투자 경기 지표 점검"
            })

        else:  # US
            # ① 매월 첫째 금요일: 전월 고용보고서 (노동부)
            fri1 = get_nth_weekday(y, m, weekday=4, n=1)
            candidates.append({
                "date": fri1,
                "title": f"미국 {prev_m}월 고용보고서 (비농업 고용 & 실업률)",
                "impact": "High",
                "desc": "노동시장 냉각 속도 및 임금 상승률 확인"
            })
            # ② 매월 12일경: 전월 소비자물가지수(CPI)
            candidates.append({
                "date": date(y, m, 12),
                "title": f"미국 {prev_m}월 소비자물가지수(CPI)",
                "impact": "High",
                "desc": "인플레이션 둔화 추세 지속 여부 및 차기 금리 경로 가늠자"
            })
            # ③ 매월 16일경: 소매판매(Retail Sales) & PPI
            candidates.append({
                "date": date(y, m, 16),
                "title": f"미국 {prev_m}월 소매판매(Retail Sales)",
                "impact": "Medium",
                "desc": "미국 소비 경기 및 경제 펀더멘털 점검"
            })
            # ④ 매월 셋째 금요일: 옵션/선물옵션 만기일 (3, 6, 9, 12월은 쿼드러플 위칭데이)
            fri3 = get_nth_weekday(y, m, weekday=4, n=3)
            is_quad = (m in [3, 6, 9, 12])
            candidates.append({
                "date": fri3,
                "title": f"미국 {m}월 쿼드러플 위칭데이 (선물옵션 만기)" if is_quad else f"미국 {m}월 월간 옵션만기일",
                "impact": "High" if is_quad else "Medium",
                "desc": "선물옵션 만기 포지션 청산 및 장 마감 변동성 유의"
            })
            # ⑤ 매월 25일경: 개인소비지출(PCE) 물가지수
            candidates.append({
                "date": date(y, m, 25),
                "title": f"미국 {prev_m}월 개인소비지출(PCE) 물가지수",
                "impact": "High",
                "desc": "연준이 가장 주목하는 핵심 물가 벤치마크 지표"
            })

    # 2. 주요 확정 정책 회의, 증시 휴장일 및 메가캡 실적 발표 (연/월/일 지정)
    if market == 'KRX':
        special_events = [
            {"date": date(2026, 11, 26), "title": "한국은행 금융통화위원회 (통화정책방향)", "impact": "High", "desc": "올해 마지막 기준금리 결정 및 경제전망 수정"},
            {"date": date(2026, 12, 31), "title": "한국거래소(KRX) 연말 휴장일", "impact": "Medium", "desc": "국내 증시 납회일(12/30) 이후 연말 휴장"},
            {"date": date(2027, 1, 8), "title": "삼성전자 4분기 잠정 실적 발표", "impact": "High", "desc": "반도체/HBM 영업이익 및 연간 실적 집계"},
            {"date": date(2027, 1, 14), "title": "한국은행 금융통화위원회 (기준금리 결정)", "impact": "High", "desc": "2027년 첫 기준금리 결정 및 통화정책 방향"},
            {"date": date(2027, 2, 25), "title": "한국은행 금융통화위원회 (경제전망)", "impact": "High", "desc": "기준금리 결정 및 2027년 경제성장률 전망"},
        ]
    else:  # US
        special_events = [
            {"date": date(2026, 11, 18), "title": "엔비디아(NVDA) 3분기 실적 발표", "impact": "High", "desc": "차세대 블랙웰 칩 수요 및 AI 인프라 투자 지속성"},
            {"date": date(2026, 11, 26), "title": "미국 추수감사절(Thanksgiving) 휴장", "impact": "Medium", "desc": "뉴욕 증시 전면 휴장"},
            {"date": date(2026, 11, 27), "title": "블랙프라이데이 (증시 13:00 조기마감)", "impact": "Medium", "desc": "연말 최대 쇼핑시즌 개막 및 증시 조기 종료"},
            {"date": date(2026, 12, 16), "title": "미 연준 12월 FOMC 회의 (기준금리 결정)", "impact": "High", "desc": "올해 마지막 기준금리 결정 및 경제전망·점도표(Dot Plot) 공개"},
            {"date": date(2026, 12, 25), "title": "크리스마스(Christmas Day) 휴장", "impact": "Medium", "desc": "뉴욕 증시 전면 휴장"},
            {"date": date(2027, 1, 1), "title": "신정(New Year's Day) 휴장", "impact": "Medium", "desc": "글로벌 증시 신정 휴장"},
            {"date": date(2027, 1, 27), "title": "미 연준 2027년 1월 FOMC 회의", "impact": "High", "desc": "새해 첫 통화정책 결정 및 제롬 파월 기자회견"},
            {"date": date(2027, 3, 17), "title": "미 연준 3월 FOMC 회의 (경제전망·점도표)", "impact": "High", "desc": "기준금리 결정 및 2027년 금리 인하 경로 점검"},
        ]
    candidates.extend(special_events)

    # 3. 엄격한 미래 이벤트 필터링 (ev['date'] >= today)
    # 이미 지난 과거의 일정은 연도 래핑 없이 완벽히 배제
    filtered = []
    seen_keys = set()

    for ev in candidates:
        ev_date = ev['date']
        # 과거 일정은 절대 포함하지 않음
        if ev_date < today:
            continue

        delta = (ev_date - today).days
        # 다가오는 90일 이내의 가까운 예정 사항만 선별
        if delta > 90:
            continue

        # 같은 날짜에 중복된 유사 타이틀 방지
        key = (ev_date, ev['title'][:6])
        if key in seen_keys:
            continue
        seen_keys.add(key)

        if delta == 0:
            dday_str = "D-Day"
            color_cls = "dday-red"
        elif delta == 1:
            dday_str = "D-1"
            color_cls = "dday-orange"
        elif delta <= 7:
            dday_str = f"D-{delta}"
            color_cls = "dday-blue"
        else:
            dday_str = f"D-{delta}"
            color_cls = "dday-gray"

        filtered.append({
            "date": ev_date.strftime("%m월 %d일"),
            "dday": dday_str,
            "delta": delta,
            "color_cls": color_cls,
            "title": ev['title'],
            "impact": ev.get('impact', 'Medium'),
            "desc": ev.get('desc', '')
        })

    # 날짜 빠른 순(D-Day가 가까운 순)으로 정렬 후 상위 max_items 반환
    filtered.sort(key=lambda x: x['delta'])
    return filtered[:max_items]
