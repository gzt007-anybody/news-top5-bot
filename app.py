import streamlit as st
import requests
import html
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# =========================================================
# 기본 화면 설정
# =========================================================
st.set_page_config(
    page_title="NEWS TOP 기사 수집",
    page_icon="📰",
    layout="wide"
)

st.title("📰 최신 기사 수집 BOT")
st.caption("NAVER API HUB 기반 · 기간 · 주제 · 추가 검색어 · 기사 수를 선택해서 최신 기사를 검색합니다.")

# =========================================================
# 네이버 API HUB 뉴스 검색
# =========================================================
def get_naver_news(query, start=1, display=100):
    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]
    except KeyError as e:
        st.error(
            "Streamlit Secrets에 필요한 키가 없습니다.\n\n"
            "필요한 항목:\n"
            "- NAVER_CLIENT_ID\n"
            "- NAVER_CLIENT_SECRET\n\n"
            f"누락된 키: {e}"
        )
        return []

    client_id = str(client_id).strip()
    client_secret = str(client_secret).strip()

    if not client_id:
        st.error("NAVER_CLIENT_ID 값이 비어 있습니다.")
        return []

    if not client_secret:
        st.error("NAVER_CLIENT_SECRET 값이 비어 있습니다.")
        return []

    url = "https://naverapihub.apigw.ntruss.com/search/v1/news"

    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret
    }

    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": "date",
        "format": "json"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )
    except requests.Timeout:
        st.error("네이버 API HUB 연결 시간이 초과되었습니다.")
        return []
    except requests.RequestException as e:
        st.error(f"네이버 API HUB 연결 오류: {e}")
        return []

    if response.status_code != 200:
        try:
            error_data = response.json()
            error_code = (
                error_data.get("errorCode")
                or error_data.get("code")
                or ""
            )
            error_message = (
                error_data.get("errorMessage")
                or error_data.get("message")
                or ""
            )
        except Exception:
            error_code = ""
            error_message = response.text

        st.error(f"네이버 API HUB 오류: {response.status_code}")
        st.markdown("#### 🔎 오류 상세 진단")
        st.write(f"**오류코드:** {error_code if error_code else '확인 불가'}")
        st.write(f"**오류내용:** {error_message if error_message else '확인 불가'}")
        st.caption("※ 보안을 위해 Client ID와 Client Secret 실제 값은 화면에 표시하지 않습니다.")

        if response.status_code in (401, 403):
            st.warning(
                "인증 또는 권한 오류입니다.\n\n"
                "확인할 항목:\n"
                "1. API HUB에서 발급된 Client ID / Client Secret인지\n"
                "2. 해당 API HUB Application에 검색 API가 연결되어 있는지\n"
                "3. Streamlit Secrets에 값이 정확히 저장되어 있는지\n"
                "4. Client Secret이 재발급된 적이 있는지"
            )

        return []

    return response.json().get("items", [])

# =========================================================
# 텍스트 정리
# =========================================================
def clean_text(text):
    if not text:
        return ""
    text = text.replace("<b>", "")
    text = text.replace("</b>", "")
    return html.unescape(text)

# =========================================================
# 날짜 변환
# =========================================================
KOREA_TZ = timezone(timedelta(hours=9))

def get_news_datetime(pub_date):
    try:
        dt = parsedate_to_datetime(pub_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KOREA_TZ)
    except Exception:
        return None

# =========================================================
# 주제 설정
# =========================================================
topic_map = {
    "종합": "뉴스",
    "정치": "정치",
    "경제": "경제",
    "사회": "사회",
    "국제": "국제",
    "IT·과학": "IT 과학",
    "생활·문화": "생활 문화",
    "스포츠": "스포츠",
    "연예": "연예"
}

# =========================================================
# 검색 조건
# =========================================================
st.subheader("🔎 검색 조건")

col1, col2 = st.columns(2)

with col1:
    topic = st.selectbox(
        "주제 선택",
        [
            "종합",
            "정치",
            "경제",
            "사회",
            "국제",
            "IT·과학",
            "생활·문화",
            "스포츠",
            "연예",
            "직접 입력"
        ],
        index=0
    )

with col2:
    result_count = st.number_input(
        "검색 기사 수",
        min_value=1,
        max_value=100,
        value=20,
        step=1
    )

# =========================================================
# 추가 검색어 입력
# =========================================================
if topic == "직접 입력":
    extra_keyword = st.text_input(
        "원하는 검색어 입력",
        placeholder="예: 배달앱, 부동산, 대통령, 인공지능"
    )
    query = extra_keyword.strip()

else:
    extra_keyword = st.text_input(
        "추가 검색어 (선택)",
        placeholder="예: 정치 선택 후 '대통령', 경제 선택 후 '금리' 입력"
    )

    base_query = topic_map[topic]

    if extra_keyword.strip():
        query = f"{base_query} {extra_keyword.strip()}"
    else:
        query = base_query

# =========================================================
# 조회기간 선택
# =========================================================
st.markdown("#### 📅 조회기간")

today = datetime.now(KOREA_TZ).date()

period_option = st.selectbox(
    "조회기간 선택",
    [
        "오늘",
        "최근 3일",
        "최근 7일",
        "최근 30일",
        "직접 입력"
    ],
    index=0
)

if period_option == "오늘":
    start_date = today
    end_date = today
elif period_option == "최근 3일":
    start_date = today - timedelta(days=2)
    end_date = today
elif period_option == "최근 7일":
    start_date = today - timedelta(days=6)
    end_date = today
elif period_option == "최근 30일":
    start_date = today - timedelta(days=29)
    end_date = today
else:
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input(
            "시작일",
            value=today - timedelta(days=7)
        )
    with date_col2:
        end_date = st.date_input(
            "종료일",
            value=today
        )

# =========================================================
# 현재 선택 조건 표시
# =========================================================
st.info(
    f"검색어: {query if query else '-'}  |  "
    f"기간: {start_date} ~ {end_date}  |  "
    f"기사 수: {int(result_count)}개"
)

# =========================================================
# 기사 수집 함수
# =========================================================
def collect_news(query, start_date, end_date, wanted_count):
    collected = []
    seen_links = set()
    seen_titles = set()

    max_pages = 10

    for page in range(max_pages):
        start_number = page * 100 + 1

        items = get_naver_news(
            query=query,
            start=start_number,
            display=100
        )

        if not items:
            break

        old_news_found = False

        for news in items:
            pub_date = news.get("pubDate", "")
            dt = get_news_datetime(pub_date)

            if dt is None:
                continue

            news_date = dt.date()

            if news_date > end_date:
                continue

            if news_date < start_date:
                old_news_found = True
                continue

            title = clean_text(news.get("title", "")).strip()

            link = (
                news.get("originallink")
                or news.get("link")
                or ""
            ).strip()

            if link and link in seen_links:
                continue

            normalized_title = title.lower()

            if normalized_title in seen_titles:
                continue

            if link:
                seen_links.add(link)

            seen_titles.add(normalized_title)
            collected.append(news)

            if len(collected) >= wanted_count:
                return collected

        if old_news_found:
            break

    return collected

# =========================================================
# 검색 버튼
# =========================================================
st.divider()

search_clicked = st.button(
    "🔄 최신 기사 검색",
    type="primary",
    use_container_width=True
)

if search_clicked:
    if not query.strip():
        st.warning("검색어를 입력해주세요.")
    elif start_date > end_date:
        st.error("시작일이 종료일보다 늦습니다.")
    else:
        with st.spinner("조건에 맞는 최신 기사를 검색하고 있습니다..."):
            news_list = collect_news(
                query=query,
                start_date=start_date,
                end_date=end_date,
                wanted_count=int(result_count)
            )

        st.session_state["news_list"] = news_list
        st.session_state["search_query"] = query
        st.session_state["start_date"] = start_date
        st.session_state["end_date"] = end_date
        st.session_state["result_count"] = int(result_count)

# =========================================================
# 결과 표시
# =========================================================
if "news_list" in st.session_state:
    news_list = st.session_state["news_list"]

    st.divider()
    st.subheader(f"📰 검색 결과 — {len(news_list)}개")

    saved_query = st.session_state.get("search_query", "")
    saved_start = st.session_state.get("start_date", "")
    saved_end = st.session_state.get("end_date", "")

    st.caption(
        f"검색어: {saved_query} | "
        f"기간: {saved_start} ~ {saved_end}"
    )

    if len(news_list) == 0:
        st.warning("선택한 조건에 해당하는 기사를 찾지 못했습니다.")
    else:
        for i, news in enumerate(news_list, start=1):
            title = clean_text(news.get("title", "제목 없음"))
            description = clean_text(news.get("description", ""))

            link = (
                news.get("originallink")
                or news.get("link")
                or ""
            )

            pub_date = news.get("pubDate", "")
            dt = get_news_datetime(pub_date)

            if dt:
                pub_date_text = dt.strftime("%Y-%m-%d %H:%M")
            else:
                pub_date_text = pub_date

            with st.container():
                st.markdown(f"### {i}. {title}")
                st.caption(f"🕐 {pub_date_text}")

                if description:
                    st.write(description)

                if link:
                    st.link_button(
                        "🔗 원문 기사 보기",
                        link
                    )

                st.divider()


# Weekly search interest among candidates found in recent news headlines.
TITLE_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")
STOP_WORDS = set(
    "뉴스 속보 단독 종합 포토 영상 기자 오늘 내일 어제 이번 지난 최근 관련 발표 "
    "공개 진행 예정 개최 시작 완료 지원 확대 강화 올해 내년 한국 국내 세계 통해 "
    "대해 대한 위해 함께 다시 정부 사람 소식 상황 문제 결과 처음 가장 이후 이상 "
    "오전 오후 시 분 년 월 일 말 했다 한다 됐다 된다 있는 없는 하는 위한".split()
)
TREND_BATCH_SIZE = 5
MIN_HEADLINE_COUNT = 2


def headline_candidates(articles):
    counts = Counter()
    related = {}
    for article in articles:
        title = clean_text(article.get("title", ""))
        tokens = TITLE_TOKEN.findall(re.sub(r"\[[^\]]*\]", " ", title))
        seen = set()
        for index, token in enumerate(tokens):
            if token in STOP_WORDS or len(token) < 2 or token.isdecimal():
                continue
            seen.add(token.casefold())
            if index + 1 < len(tokens):
                following = tokens[index + 1]
                if following not in STOP_WORDS and len(following) >= 2 and not following.isdecimal():
                    seen.add(f"{token} {following}".casefold())
        counts.update(seen)
        link = (article.get("originallink") or article.get("link") or "").strip()
        if link.startswith(("https://", "http://")):
            for keyword in seen:
                related.setdefault(keyword, link)

    ranked = sorted(counts, key=lambda term: (-counts[term], -len(term.split()), term))
    return [
        (term, counts[term], related.get(term, ""))
        for term in ranked
        if counts[term] >= MIN_HEADLINE_COUNT
    ][:40]


def fetch_search_trends(keywords, start, end):
    headers = {
        "X-NCP-APIGW-API-KEY-ID": str(st.secrets["NAVER_CLIENT_ID"]).strip(),
        "X-NCP-APIGW-API-KEY": str(st.secrets["NAVER_CLIENT_SECRET"]).strip(),
    }
    response = requests.post(
        "https://naverapihub.apigw.ntruss.com/search-trend/v1/search",
        headers=headers,
        json={
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "timeUnit": "date",
            "keywordGroups": [{"groupName": term, "keywords": [term]} for term in keywords],
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["results"]


def compare_trend(points, start):
    ratios = {point["period"]: point["ratio"] for point in points}
    days = [(start + timedelta(days=offset)).isoformat() for offset in range(14)]
    if any(day not in ratios for day in days):
        return None
    previous = sum(ratios[day] for day in days[:7])
    recent = sum(ratios[day] for day in days[7:])
    if recent <= previous:
        return None
    return (recent / previous - 1) * 100 if previous > 0 else float("inf")


def weekly_ranking(candidates, start, end):
    ranking = []
    new_activity = []
    incomplete = 0
    for offset in range(0, len(candidates), TREND_BATCH_SIZE):
        batch = candidates[offset:offset + TREND_BATCH_SIZE]
        results = fetch_search_trends([term for term, _, _ in batch], start, end)
        by_term = {result["title"]: result["data"] for result in results}
        for term, count, link in batch:
            points = by_term.get(term, [])
            if len({point["period"] for point in points}) < 14:
                incomplete += 1
                continue
            growth = compare_trend(points, start)
            if growth == float("inf"):
                new_activity.append(term)
            elif growth is not None:
                ranking.append((term, growth, count, link))
    ranking.sort(key=lambda row: (-row[1], -row[2], row[0]))
    return ranking[:20], new_activity, incomplete


st.divider()
st.subheader("최근 7일 급상승 키워드")
trend_end = today - timedelta(days=1)
trend_recent_start = trend_end - timedelta(days=6)
trend_start = trend_recent_start - timedelta(days=7)
st.caption(
    f"어제까지 7일({trend_recent_start} ~ {trend_end})을 직전 7일과 비교합니다. "
    "선택한 검색 조건의 기사 제목에서 2건 이상 나온 후보를 최대 40개 비교합니다."
)

if st.button("급상승 키워드 조회", key="weekly_trend"):
    st.session_state.pop("weekly_trend_result", None)
    if not query.strip():
        st.warning("주제를 선택하거나 검색어를 입력해 주세요.")
    else:
        with st.spinner("최근 기사와 네이버 검색 관심도를 조회하고 있습니다..."):
            articles = collect_news(query, trend_recent_start, trend_end, wanted_count=200)
            candidates = headline_candidates(articles)
            if not candidates:
                st.info("비교할 키워드 후보가 부족합니다. 다른 주제나 검색어로 조회해 보세요.")
            else:
                try:
                    ranking, new_activity, incomplete = weekly_ranking(candidates, trend_start, trend_end)
                except requests.HTTPError as error:
                    status = error.response.status_code
                    if status in (401, 403):
                        st.error("NAVER API HUB에서 현재 Application의 검색어 트렌드 권한을 확인해 주세요.")
                    elif status == 429:
                        st.error("검색어 트렌드 API 호출 한도에 도달했습니다. 잠시 후 다시 시도해 주세요.")
                    else:
                        st.error(f"검색어 트렌드 API 요청이 실패했습니다. (HTTP {status})")
                except requests.RequestException:
                    st.error("검색어 트렌드 API에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.")
                except (KeyError, ValueError, TypeError):
                    st.error("Streamlit Secrets 또는 검색어 트렌드 API 응답을 확인해 주세요.")
                else:
                    st.session_state["weekly_trend_result"] = (
                        query, trend_end, len(articles), len(candidates), ranking, new_activity, incomplete
                    )

trend_result = st.session_state.get("weekly_trend_result")
if trend_result and trend_result[:2] == (query, trend_end):
    _, _, article_count, candidate_count, ranking, new_activity, incomplete = trend_result
    st.caption(
        f"검색어: {query} · 기사 {article_count}건 · 후보 {candidate_count}개 · "
        "기사에서 발굴한 후보의 검색 관심도 상승률 순위"
    )
    if ranking:
        st.dataframe(
            [
                {
                    "순위": rank,
                    "키워드": term,
                    "검색 관심도 상승률": f"+{growth:,.1f}%",
                    "제목 등장 기사 수": count,
                    "관련 기사": link,
                }
                for rank, (term, growth, count, link) in enumerate(ranking, start=1)
            ],
            hide_index=True,
            column_config={"관련 기사": st.column_config.LinkColumn("관련 기사")},
        )
    else:
        st.info("두 기간을 비교해 상승률을 계산할 수 있는 상승 키워드가 없습니다.")
    if new_activity:
        st.caption("직전 7일 지수가 0인 후보 · " + ", ".join(new_activity))
    if incomplete:
        st.caption(f"14일치 지수가 모두 제공되지 않은 후보 {incomplete}개는 비교에서 제외했습니다.")
