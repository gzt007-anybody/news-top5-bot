import streamlit as st

import requests

from datetime import datetime

from email.utils import parsedate_to_datetime

st.set_page_config(

    page_title="NEWS TOP 5 BOT",

    page_icon="📰",

    layout="wide"

)

st.title("📰 NEWS TOP 5 BOT")

st.caption("최신 뉴스 수집 테스트")

# -----------------------------

# 네이버 뉴스 검색

# -----------------------------

def get_naver_news():

    client_id = st.secrets["NAVER_CLIENT_ID"]

    client_secret = st.secrets["NAVER_CLIENT_SECRET"]

    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {

        "X-Naver-Client-Id": client_id,

        "X-Naver-Client-Secret": client_secret

    }

    params = {

        "query": "뉴스",

        "display": 20,

        "start": 1,

        "sort": "date"

    }

    response = requests.get(

        url,

        headers=headers,

        params=params,

        timeout=10

    )

    if response.status_code != 200:

        st.error(

            f"네이버 뉴스 API 오류: "

            f"{response.status_code}"

        )

        return []

    return response.json().get("items", [])

# -----------------------------

# 제목 HTML 태그 제거

# -----------------------------

def clean_text(text):

    return (

        text.replace("<b>", "")

            .replace("</b>", "")

            .replace("&quot;", '"')

            .replace("&amp;", "&")

            .replace("&lt;", "<")

            .replace("&gt;", ">")

    )

# -----------------------------

# 뉴스 가져오기 버튼

# -----------------------------

if st.button(

    "🔄 최신 뉴스 20개 가져오기",

    type="primary",

    use_container_width=True

):

    with st.spinner("최신 뉴스를 가져오는 중입니다..."):

        news_list = get_naver_news()

    if news_list:

        st.session_state["news_list"] = news_list

        st.success(

            f"최신 뉴스 {len(news_list)}개를 가져왔습니다."

        )

# -----------------------------

# 뉴스 목록 표시

# -----------------------------

if "news_list" in st.session_state:

    st.divider()

    st.subheader("📰 최신 뉴스")

    for i, news in enumerate(

        st.session_state["news_list"],

        start=1

    ):

        title = clean_text(news.get("title", ""))

        description = clean_text(

            news.get("description", "")

        )

        link = news.get("originallink") or news.get("link", "")

        pub_date = news.get("pubDate", "")

        try:

            dt = parsedate_to_datetime(pub_date)

            pub_date = dt.strftime(

                "%Y-%m-%d %H:%M"

            )

        except Exception:

            pass

        with st.container():

            st.markdown(

                f"### {i}. {title}"

            )

            st.caption(

                f"🕐 {pub_date}"

            )

            if description:

                st.write(description)

            if link:

                st.link_button(

                    "🔗 원문 보기",

                    link

                )

            st.divider()
