import streamlit as st
from datetime import date, timedelta, datetime, timezone

from channels import CHANNELS
from youtube_api import fetch_channel_videos, fetch_top_liked_comments, fetch_top_relevance_comments

st.set_page_config(
    page_title="정치 채널 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 정치 YouTube 채널 대시보드")
st.caption("채널별 인기 영상 & 댓글 분석")

# ── 사이드바 필터 ─────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 필터 설정")

    default_end   = date.today()
    default_start = default_end - timedelta(days=7)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작일", value=default_start, max_value=default_end)
    with col2:
        end_date = st.date_input("종료일", value=default_end, min_value=start_date)

    channel_names = [ch["name"] for ch in CHANNELS]
    selected_names = st.multiselect(
        "채널 선택 (미선택 시 전체)",
        options=channel_names,
        default=[],
        placeholder="채널을 선택하세요",
    )
    if not selected_names:
        selected_channels = CHANNELS
    else:
        selected_channels = [ch for ch in CHANNELS if ch["name"] in selected_names]

    max_videos = st.slider("채널당 최대 영상 수", min_value=3, max_value=30, value=10)

    min_views = st.number_input(
        "최소 조회수 필터",
        min_value=0,
        max_value=10_000_000,
        value=0,
        step=10_000,
        help="이 조회수 미만 영상은 제외됩니다",
    )

    st.divider()
    run_btn = st.button("🔄 조회", use_container_width=True, type="primary")


def to_rfc3339(d: date, end: bool = False) -> str:
    if end:
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()


def fmt_num(n: int) -> str:
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}억"
    if n >= 10_000:
        return f"{n / 10_000:.1f}만"
    return f"{n:,}"


def render_comment_card(c: dict, rank: int, accent: str = "#4a9eff"):
    st.markdown(
        f"""
        <div style="background:#1a1a2e;border-radius:8px;padding:10px 14px;
                    margin-bottom:8px;border-left:3px solid {accent};">
          <div style="font-size:12px;color:#888;">
            <b style="color:#ccc;">#{rank}</b> &nbsp;
            <span style="color:{accent};">{c['author']}</span>
            &nbsp;·&nbsp; {c['published']}
          </div>
          <div style="margin-top:6px;font-size:14px;line-height:1.6;color:#eee;">{c['text']}</div>
          <div style="margin-top:6px;font-size:12px;color:#aaa;">
            👍 {fmt_num(c['like_count'])} &nbsp; 💬 {c['reply_count']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_video(video: dict, rank: int):
    video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
    pub_date  = video["published"][:10] if len(video.get("published","")) >= 10 else video.get("published","")

    with st.container(border=True):
        # 영상 정보 행
        img_col, info_col = st.columns([1, 4])

        with img_col:
            if video["thumbnail"]:
                st.image(video["thumbnail"], use_container_width=True)

        with info_col:
            st.markdown(f"### [{rank}위 · {video['title']}]({video_url})")
            st.markdown(
                f"**조회수** &nbsp; `{fmt_num(video['view_count'])}`"
                + (f" &nbsp;&nbsp; 게시일: `{pub_date}`" if pub_date else "")
            )

        # 댓글 행 — 바로 노출
        st.markdown("---")
        left, right = st.columns(2)

        with left:
            st.markdown("#### 👍 좋아요 많은 댓글 TOP 3")
            with st.spinner("불러오는 중..."):
                liked = fetch_top_liked_comments(video["video_id"], n=3)
            if liked:
                for i, c in enumerate(liked, 1):
                    render_comment_card(c, i, accent="#4a9eff")
            else:
                st.caption("댓글을 불러올 수 없습니다.")

        with right:
            st.markdown("#### 🔥 YouTube 인기 댓글 TOP 3")
            with st.spinner("불러오는 중..."):
                popular = fetch_top_relevance_comments(video["video_id"], n=3)
            if popular:
                for i, c in enumerate(popular, 1):
                    render_comment_card(c, i, accent="#ff6b6b")
            else:
                st.caption("댓글을 불러올 수 없습니다.")


# ── 메인 ─────────────────────────────────────────────────────
if not run_btn:
    st.info("사이드바에서 기간과 채널을 설정한 후 **🔄 조회** 버튼을 눌러주세요.")
    st.stop()

after  = to_rfc3339(start_date)
before = to_rfc3339(end_date, end=True)

st.markdown(f"### 📅 {start_date} ~ {end_date} &nbsp;|&nbsp; 채널 {len(selected_channels)}개"
            + (f" &nbsp;|&nbsp; 최소 조회수 {fmt_num(int(min_views))}" if min_views > 0 else ""))
st.divider()

overall_progress = st.progress(0, text="채널 데이터 불러오는 중...")

for ch_idx, channel in enumerate(selected_channels):
    overall_progress.progress(
        ch_idx / len(selected_channels),
        text=f"[{ch_idx+1}/{len(selected_channels)}] {channel['name']} 조회 중...",
    )

    videos = fetch_channel_videos(
        channel_id=channel["id"],
        after=after,
        before=before,
        max_results=max_videos,
    )

    # 조회수 필터 적용
    if min_views > 0:
        videos = [v for v in videos if v["view_count"] >= min_views]

    st.subheader(f"📺 {channel['name']}")

    if not videos:
        st.warning("해당 기간·조회수 조건에 맞는 영상이 없습니다.")
        st.divider()
        continue

    for rank, video in enumerate(videos, 1):
        render_video(video, rank)

    st.divider()

overall_progress.progress(1.0, text="완료!")
overall_progress.empty()
