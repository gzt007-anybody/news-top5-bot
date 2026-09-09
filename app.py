import streamlit as st
import requests
import html
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
st.caption("기간 · 주제 · 기사 수를 선택해서 최신 기사를 검색합니다.")


# =========================================================
# 네이버 뉴스 API 호출
# =========================================================
def get_naver_news(query, start=1, display=100):

    try:
        client_id = st.secrets["NAVER_CLIENT_ID"]
        client_secret = st.secrets["NAVER_CLIENT_SECRET"]

    except KeyError:
        st.error(
            "NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 "
            "Streamlit Secrets에 없습니다."
        )
        return []

    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": "date"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )

    except requests.RequestException as e:
        st.error(f"네이버 뉴스 연결 오류: {e}")
        return []

    if response.status_code != 200:
        st.error(
            f"네이버 뉴스 API 오류: "
            f"{response.status_code}"
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
# 직접 검색어 입력
# =========================================================
if topic == "직접 입력":

    query = st.text_input(
        "검색할 주제를 입력하세요",
        placeholder="예: 부동산, 배달앱, 대통령, 인공지능"
    )

else:

    query = topic_map[topic]


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
    f"검색 주제: {query if query else '-'}  |  "
    f"기간: {start_date} ~ {end_date}  |  "
    f"기사 수: {int(result_count)}개"
)


# =========================================================
# 기사 수집 함수
# =========================================================
def collect_news(
    query,
    start_date,
    end_date,
    wanted_count
):

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

            title = clean_text(
                news.get("title", "")
            ).strip()

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

    if topic == "직접 입력" and not query.strip():

        st.warning(
            "검색할 주제를 입력해주세요."
        )

    elif start_date > end_date:

        st.error(
            "시작일이 종료일보다 늦습니다."
        )

    else:

        with st.spinner(
            "조건에 맞는 최신 기사를 검색하고 있습니다..."
        ):

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

    st.subheader(
        f"📰 검색 결과 — {len(news_list)}개"
    )

    saved_query = st.session_state.get(
        "search_query",
        ""
    )

    saved_start = st.session_state.get(
        "start_date",
        ""
    )

    saved_end = st.session_state.get(
        "end_date",
        ""
    )

    st.caption(
        f"주제: {saved_query} | "
        f"기간: {saved_start} ~ {saved_end}"
    )

    if len(news_list) == 0:

        st.warning(
            "선택한 조건에 해당하는 기사를 찾지 못했습니다."
        )

    else:

        for i, news in enumerate(
            news_list,
            start=1
        ):

            title = clean_text(
                news.get(
                    "title",
                    "제목 없음"
                )
            )

            description = clean_text(
                news.get(
                    "description",
                    ""
                )
            )

            link = (
                news.get("originallink")
                or news.get("link")
                or ""
            )

            pub_date = news.get(
                "pubDate",
                ""
            )

            dt = get_news_datetime(
                pub_date
            )

            if dt:

                pub_date_text = dt.strftime(
                    "%Y-%m-%d %H:%M"
                )

            else:

                pub_date_text = pub_date

            with st.container():

                st.markdown(
                    f"### {i}. {title}"
                )

                st.caption(
                    f"🕐 {pub_date_text}"
                )

                if description:

                    st.write(
                        description
                    )

                if link:

                    st.link_button(
                        "🔗 원문 기사 보기",
                        link
                    )

                st.divider()
