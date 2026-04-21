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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #000000; color: #ffffff; }

[data-testid="stSidebar"] {
    background: #050508 !important;
    border-right: 1px solid #1a1a2e;
}

.stButton > button {
    background: #ffffff !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-size: 12px !important;
}

/* container 패딩 축소 */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #1a1a2e !important;
    border-radius: 4px !important;
    background: #05050a !important;
    padding: 0 !important;
}

/* expander */
[data-testid="stExpander"] {
    background: #05050a !important;
    border: 1px solid #1a1a2e !important;
    border-radius: 4px !important;
}
details summary {
    font-size: 11px !important;
    letter-spacing: 0.15em !important;
    color: #555 !important;
    text-transform: uppercase !important;
}

[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #00d4ff, #ffffff) !important;
}

/* 전체 block 수직 간격 축소 */
[data-testid="stVerticalBlock"] { gap: 0rem !important; }
.element-container { margin-bottom: 0 !important; }

hr { border-color: #111 !important; margin: 6px 0 !important; }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("""
<div style="padding:20px 0 8px 0;display:flex;align-items:baseline;gap:16px;">
  <span style="font-size:28px;font-weight:900;letter-spacing:-0.02em;">POLISCAN</span>
  <span style="font-size:10px;color:#444;letter-spacing:0.3em;text-transform:uppercase;">
    한국 정치 유튜브 채널 분석
  </span>
</div>
<div style="height:1px;background:linear-gradient(90deg,#00d4ff,transparent);margin-bottom:16px;"></div>
""", unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.markdown('<div style="font-size:10px;letter-spacing:0.3em;color:#555;text-transform:uppercase;padding:16px 0 10px;">FILTER</div>', unsafe_allow_html=True)

    default_end   = date.today()
    default_start = default_end - timedelta(days=7)

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("START", value=default_start, max_value=default_end)
    with c2:
        end_date = st.date_input("END", value=default_end, min_value=start_date)

    channel_names  = [ch["name"] for ch in CHANNELS]
    selected_names = st.multiselect("CHANNELS", options=channel_names, default=[], placeholder="전체")
    selected_channels = (
        [ch for ch in CHANNELS if ch["name"] in selected_names] if selected_names else CHANNELS
    )

    max_videos = st.slider("VIDEOS PER CHANNEL", 3, 10, 5)
    min_views  = st.number_input("MIN VIEWS", min_value=0, max_value=10_000_000, value=0, step=10_000)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    run_btn = st.button("⚡  SCAN", use_container_width=True, type="primary")


def to_rfc3339(d: date, end: bool = False) -> str:
    if end:
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()


def fmt_num(n: int) -> str:
    if n >= 100_000_000: return f"{n/100_000_000:.1f}억"
    if n >= 10_000:      return f"{n/10_000:.1f}만"
    return f"{n:,}"


def render_comment_block(comments: list[dict], label: str, accent: str):
    st.markdown(f'<div style="font-size:9px;letter-spacing:0.2em;color:{accent};text-transform:uppercase;margin-bottom:6px;">{label}</div>', unsafe_allow_html=True)
    if not comments:
        st.markdown('<div style="color:#333;font-size:11px;">데이터 없음</div>', unsafe_allow_html=True)
        return
    for i, c in enumerate(comments, 1):
        text = c['text'].replace('<','&lt;').replace('>','&gt;')
        st.markdown(f"""
        <div style="border-left:2px solid {accent}33;padding:6px 10px;margin-bottom:6px;background:#08080f;border-radius:0 3px 3px 0;">
          <div style="font-size:9px;color:#444;">#{i} <span style="color:{accent}88;">{c['author']}</span> · 👍{fmt_num(c['like_count'])}</div>
          <div style="font-size:11px;color:#ccc;line-height:1.4;margin-top:3px;">{text}</div>
        </div>""", unsafe_allow_html=True)


def render_channel_row(channel: dict, videos: list[dict]):
    ch_url = f"https://www.youtube.com/channel/{channel['id']}"

    # 채널명 + 영상 카드들을 한 줄로
    name_col, *vid_cols = st.columns([1.2] + [1] * len(videos))

    with name_col:
        st.markdown(f"""
        <div style="height:100%;display:flex;flex-direction:column;justify-content:center;
                    padding:8px 0;border-right:1px solid #111;">
          <div style="width:2px;height:14px;background:#00d4ff;margin-bottom:6px;"></div>
          <a href="{ch_url}" target="_blank"
             style="font-size:13px;font-weight:700;color:#fff;text-decoration:none;line-height:1.3;">
            {channel['name']}
          </a>
          <div style="font-size:9px;color:#333;margin-top:4px;letter-spacing:0.1em;">
            {len(videos)} VIDEOS
          </div>
        </div>
        """, unsafe_allow_html=True)

    for col, video, rank in zip(vid_cols, videos, range(1, len(videos)+1)):
        video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
        with col:
            # 썸네일
            if video["thumbnail"]:
                st.image(video["thumbnail"], use_container_width=True)
            # 텍스트 정보
            st.markdown(f"""
            <div style="padding:4px 6px 6px 6px;">
              <div style="font-size:9px;color:#00d4ff;letter-spacing:0.1em;">#{rank}</div>
              <a href="{video_url}" target="_blank"
                 style="font-size:10px;font-weight:600;color:#ddd;text-decoration:none;
                        line-height:1.3;display:block;margin-top:2px;">
                {video['title'][:40]}{'…' if len(video['title'])>40 else ''}
              </a>
              <div style="font-size:10px;color:#00d4ff;font-weight:700;margin-top:3px;">
                {fmt_num(video['view_count'])}
              </div>
            </div>
            """, unsafe_allow_html=True)

    # 댓글은 expander로 — 채널 행 아래
    with st.expander(f"💬  {channel['name']} 댓글 보기"):
        for video, rank in zip(videos, range(1, len(videos)+1)):
            video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
            st.markdown(f"""
            <div style="font-size:11px;font-weight:700;color:#fff;margin:12px 0 8px 0;">
              #{rank} &nbsp;<a href="{video_url}" target="_blank"
                style="color:#fff;text-decoration:none;">{video['title'][:60]}</a>
              <span style="color:#00d4ff;margin-left:8px;">{fmt_num(video['view_count'])}</span>
            </div>
            """, unsafe_allow_html=True)

            lc, rc = st.columns(2)
            with lc:
                liked = fetch_top_liked_comments(video["video_id"], n=3)
                render_comment_block(liked, "👍 좋아요 TOP 3", "#4a9eff")
            with rc:
                popular = fetch_top_relevance_comments(video["video_id"], n=3)
                render_comment_block(popular, "🔥 인기 TOP 3", "#ff6b6b")

            st.markdown('<div style="height:1px;background:#111;margin:8px 0;"></div>', unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:#111;margin:4px 0 8px 0;"></div>', unsafe_allow_html=True)


# ── 메인 ─────────────────────────────────────────────────────
if not run_btn:
    st.markdown("""
    <div style="text-align:center;padding:100px 0;color:#1a1a1a;">
      <div style="font-size:64px;margin-bottom:12px;">⚡</div>
      <div style="font-size:11px;letter-spacing:0.3em;text-transform:uppercase;">
        SET PARAMETERS AND PRESS SCAN
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

after  = to_rfc3339(start_date)
before = to_rfc3339(end_date, end=True)

st.markdown(f"""
<div style="font-size:10px;color:#444;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:12px;">
  {start_date} → {end_date} &nbsp;·&nbsp; {len(selected_channels)} channels
  {f' &nbsp;·&nbsp; min {fmt_num(int(min_views))} views' if min_views > 0 else ''}
</div>
""", unsafe_allow_html=True)

progress = st.progress(0, text="")

for idx, channel in enumerate(selected_channels):
    progress.progress(idx / len(selected_channels),
                      text=f"SCANNING {channel['name']} [{idx+1}/{len(selected_channels)}]")

    videos = fetch_channel_videos(channel["id"], after, before, max_results=max_videos)

    if min_views > 0:
        videos = [v for v in videos if v["view_count"] >= min_views]

    if not videos:
        st.markdown(f'<div style="font-size:10px;color:#2a2a2a;padding:4px 0;">{channel["name"]} — NO DATA</div>',
                    unsafe_allow_html=True)
        continue

    render_channel_row(channel, videos)

progress.progress(1.0, text="COMPLETE")
progress.empty()
