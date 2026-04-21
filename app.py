import streamlit as st
from datetime import date, timedelta, datetime, timezone

from channels import CHANNELS
from youtube_api import fetch_channel_videos, fetch_top_liked_comments, fetch_top_relevance_comments

st.set_page_config(
    page_title="POLISCAN",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 글로벌 CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* 배경 */
.stApp {
    background: #000000;
    color: #ffffff;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: #050508 !important;
    border-right: 1px solid #1a1a2e;
}

/* 버튼 */
.stButton > button {
    background: #ffffff !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-size: 12px !important;
    padding: 10px 20px !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover {
    opacity: 0.85 !important;
}

/* 입력 필드 */
[data-testid="stDateInput"] input,
[data-testid="stNumberInput"] input {
    background: #0d0d14 !important;
    border: 1px solid #2a2a3e !important;
    color: #fff !important;
    border-radius: 2px !important;
}

/* 멀티셀렉트 */
[data-testid="stMultiSelect"] > div {
    background: #0d0d14 !important;
    border: 1px solid #2a2a3e !important;
    border-radius: 2px !important;
}

/* 슬라이더 */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: #ffffff !important;
}

/* 구분선 */
hr { border-color: #1a1a2e !important; }

/* progress bar */
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #00d4ff, #ffffff) !important;
}

/* 경고/info */
[data-testid="stAlert"] {
    background: #0d0d14 !important;
    border: 1px solid #2a2a3e !important;
    border-radius: 2px !important;
}

/* container border */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #1a1a2e !important;
    border-radius: 4px !important;
    background: #05050a !important;
}

/* metric */
[data-testid="stMetric"] {
    background: transparent !important;
}
[data-testid="stMetricValue"] {
    color: #00d4ff !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)


# ── 헤더 ─────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 40px 0 20px 0;">
  <div style="font-size:11px;letter-spacing:0.3em;color:#555;text-transform:uppercase;margin-bottom:8px;">
    INTELLIGENCE DASHBOARD
  </div>
  <div style="font-size:42px;font-weight:900;letter-spacing:-0.02em;line-height:1;">
    POLISCAN
  </div>
  <div style="font-size:13px;color:#555;margin-top:8px;letter-spacing:0.05em;">
    한국 정치 유튜브 채널 실시간 분석
  </div>
</div>
<div style="height:1px;background:linear-gradient(90deg,#00d4ff,transparent);margin-bottom:32px;"></div>
""", unsafe_allow_html=True)


# ── 사이드바 ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:10px;letter-spacing:0.3em;color:#555;text-transform:uppercase;
                padding:20px 0 12px 0;">FILTER PARAMETERS</div>
    """, unsafe_allow_html=True)

    default_end   = date.today()
    default_start = default_end - timedelta(days=7)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("START", value=default_start, max_value=default_end)
    with col2:
        end_date = st.date_input("END", value=default_end, min_value=start_date)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    channel_names = [ch["name"] for ch in CHANNELS]
    selected_names = st.multiselect(
        "CHANNELS",
        options=channel_names,
        default=[],
        placeholder="전체 채널",
    )
    selected_channels = (
        [ch for ch in CHANNELS if ch["name"] in selected_names]
        if selected_names else CHANNELS
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    max_videos = st.slider("VIDEOS PER CHANNEL", min_value=3, max_value=15, value=5)

    min_views = st.number_input(
        "MIN VIEWS",
        min_value=0, max_value=10_000_000, value=0, step=10_000,
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    run_btn = st.button("SCAN", use_container_width=True, type="primary")

    st.markdown(f"""
    <div style="font-size:10px;color:#333;margin-top:24px;letter-spacing:0.05em;">
      CHANNELS LOADED: {len(selected_channels)}<br>
      PERIOD: {start_date} → {end_date}
    </div>
    """, unsafe_allow_html=True)


# ── 유틸 ─────────────────────────────────────────────────────
def to_rfc3339(d: date, end: bool = False) -> str:
    if end:
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()


def fmt_num(n: int) -> str:
    if n >= 100_000_000:
        return f"{n/100_000_000:.1f}억"
    if n >= 10_000:
        return f"{n/10_000:.1f}만"
    return f"{n:,}"


def render_comment_block(comments: list[dict], label: str, accent: str):
    st.markdown(f"""
    <div style="font-size:10px;letter-spacing:0.2em;color:{accent};
                text-transform:uppercase;margin-bottom:10px;">{label}</div>
    """, unsafe_allow_html=True)
    if not comments:
        st.markdown('<div style="color:#333;font-size:12px;">데이터 없음</div>', unsafe_allow_html=True)
        return
    for i, c in enumerate(comments, 1):
        text = c['text'].replace('<', '&lt;').replace('>', '&gt;')
        st.markdown(f"""
        <div style="border-left:2px solid {accent}22;padding:8px 12px;margin-bottom:8px;
                    background:#0a0a12;border-radius:0 4px 4px 0;">
          <div style="font-size:10px;color:#444;margin-bottom:4px;">
            #{i} &nbsp;<span style="color:{accent}88;">{c['author']}</span>
            &nbsp;·&nbsp; 👍 {fmt_num(c['like_count'])}
          </div>
          <div style="font-size:12px;color:#ccc;line-height:1.5;">{text}</div>
        </div>
        """, unsafe_allow_html=True)


def render_channel_row(channel: dict, videos: list[dict]):
    # 채널 헤더
    ch_url = f"https://www.youtube.com/channel/{channel['id']}"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;padding:20px 0 12px 0;">
      <div style="width:3px;height:20px;background:#00d4ff;border-radius:2px;"></div>
      <a href="{ch_url}" target="_blank"
         style="font-size:18px;font-weight:700;color:#fff;text-decoration:none;
                letter-spacing:0.02em;">
        {channel['name']}
      </a>
      <div style="font-size:10px;color:#333;letter-spacing:0.2em;text-transform:uppercase;">
        · {len(videos)} VIDEOS
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 영상 카드 — 가로 row
    cols = st.columns(len(videos))
    for col, video, rank in zip(cols, videos, range(1, len(videos)+1)):
        video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
        pub = video["published"][:10] if len(video.get("published","")) >= 10 else video.get("published","")

        with col:
            with st.container(border=True):
                # 썸네일 (절반 크기 = 컬럼 전체 너비의 절반을 빈 col로 처리)
                if video["thumbnail"]:
                    _, img_c, _ = st.columns([1, 4, 1])
                    with img_c:
                        st.image(video["thumbnail"], use_container_width=True)

                st.markdown(f"""
                <div style="padding:6px 2px;">
                  <div style="font-size:10px;color:#00d4ff;letter-spacing:0.1em;margin-bottom:4px;">
                    #{rank}
                  </div>
                  <a href="{video_url}" target="_blank"
                     style="font-size:12px;font-weight:600;color:#fff;text-decoration:none;
                            line-height:1.4;display:block;">
                    {video['title'][:45]}{'...' if len(video['title'])>45 else ''}
                  </a>
                  <div style="font-size:11px;color:#00d4ff;font-weight:700;margin-top:6px;">
                    {fmt_num(video['view_count'])} views
                  </div>
                  <div style="font-size:10px;color:#333;margin-top:2px;">{pub}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div style="height:1px;background:#1a1a2e;margin:8px 0;"></div>',
                            unsafe_allow_html=True)

                # 댓글
                with st.spinner(""):
                    liked   = fetch_top_liked_comments(video["video_id"], n=3)
                    popular = fetch_top_relevance_comments(video["video_id"], n=3)

                render_comment_block(liked,   "👍 좋아요 TOP 3", "#4a9eff")
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                render_comment_block(popular, "🔥 인기 TOP 3",  "#ff6b6b")

    st.markdown('<div style="height:1px;background:#111;margin:24px 0;"></div>',
                unsafe_allow_html=True)


# ── 메인 ─────────────────────────────────────────────────────
if not run_btn:
    st.markdown("""
    <div style="text-align:center;padding:80px 0;color:#222;">
      <div style="font-size:48px;margin-bottom:16px;">⚡</div>
      <div style="font-size:13px;letter-spacing:0.2em;text-transform:uppercase;">
        SET PARAMETERS AND PRESS SCAN
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

after  = to_rfc3339(start_date)
before = to_rfc3339(end_date, end=True)

st.markdown(f"""
<div style="display:flex;gap:24px;margin-bottom:24px;font-size:11px;
            letter-spacing:0.1em;color:#555;text-transform:uppercase;">
  <span>📅 {start_date} → {end_date}</span>
  <span>·</span>
  <span>{len(selected_channels)} CHANNELS</span>
  {f'<span>·</span><span>MIN {fmt_num(int(min_views))} VIEWS</span>' if min_views > 0 else ''}
</div>
""", unsafe_allow_html=True)

overall_progress = st.progress(0, text="")

for ch_idx, channel in enumerate(selected_channels):
    overall_progress.progress(
        ch_idx / len(selected_channels),
        text=f"SCANNING  {channel['name']}  [{ch_idx+1}/{len(selected_channels)}]",
    )

    videos = fetch_channel_videos(
        channel_id=channel["id"],
        after=after,
        before=before,
        max_results=max_videos,
    )

    if min_views > 0:
        videos = [v for v in videos if v["view_count"] >= min_views]

    if not videos:
        st.markdown(f"""
        <div style="padding:12px 0;font-size:11px;color:#333;letter-spacing:0.1em;">
          {channel['name']} — NO DATA FOR THIS PERIOD
        </div>
        """, unsafe_allow_html=True)
        continue

    render_channel_row(channel, videos)

overall_progress.progress(1.0, text="SCAN COMPLETE")
overall_progress.empty()
