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
