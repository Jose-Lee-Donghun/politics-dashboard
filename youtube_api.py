import streamlit as st
from datetime import datetime, timezone
import scrapetube
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR, SORT_BY_RECENT


def _parse_dt(iso_str: str) -> datetime:
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))


def _view_text_to_int(text: str) -> int:
    """'1.2M views' 같은 문자열을 정수로 변환."""
    if not text:
        return 0
    text = text.replace(",", "").replace(" views", "").replace(" view", "").strip()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(text)
    except ValueError:
        return 0


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_channel_videos(channel_id: str, after: str, before: str, max_results: int = 20) -> list[dict]:
    """채널의 기간 내 동영상을 조회수 내림차순으로 반환 (API 키 불필요)."""
    after_dt  = _parse_dt(after)
    before_dt = _parse_dt(before)

    videos = []
    try:
        # sort_by=1: 최신순, 넉넉하게 가져온 뒤 날짜 필터
        for raw in scrapetube.get_channel(channel_id=channel_id, limit=100, sort_by="newest"):
            published_text = (
                raw.get("publishedTimeText", {}).get("simpleText", "") or ""
            )

            # 날짜 파싱 — scrapetube는 ISO 날짜를 안 주므로 publishedAt 필드 활용
            # richThumbnail 등 없이 videoId 기준으로 접근
            video_id = raw.get("videoId", "")
            if not video_id:
                continue

            title = ""
            if "title" in raw:
                runs = raw["title"].get("runs", [])
                title = runs[0]["text"] if runs else raw["title"].get("simpleText", "")

            view_count = 0
            if "viewCountText" in raw:
                view_text = raw["viewCountText"].get("simpleText", "") or \
                            raw["viewCountText"].get("runs", [{}])[0].get("text", "")
                view_count = _view_text_to_int(view_text)

            thumbnail = ""
            thumbs = raw.get("thumbnail", {}).get("thumbnails", [])
            if thumbs:
                thumbnail = thumbs[-1].get("url", "")

            # 날짜: scrapetube는 "2 days ago" 형식만 줄 때가 많음
            # lengthText, publishedTimeText 등으로 대략 필터
            # → 정확한 필터는 published_text 파싱 대신,
            #   가져온 뒤 videos.json 같은 보완 없이 텍스트로만 판단
            published_iso = raw.get("publishedAt", "")  # 없을 수 있음

            if published_iso:
                try:
                    pub_dt = _parse_dt(published_iso)
                    if not (after_dt <= pub_dt <= before_dt):
                        continue
                except Exception:
                    pass
            # publishedAt 없으면 최신 100개 안에서 날짜 텍스트로 거름
            # (너무 오래된 영상은 "X months ago" 등 — 아래에서 rough 필터)
            else:
                too_old_keywords = ["year", "년"]
                if any(k in published_text.lower() for k in too_old_keywords):
                    break  # 최신순 정렬이므로 이후는 더 오래됨

            videos.append({
                "video_id":      video_id,
                "title":         title,
                "published":     published_iso or published_text,
                "thumbnail":     thumbnail,
                "view_count":    view_count,
                "like_count":    0,
                "comment_count": 0,
            })

            if len(videos) >= max_results * 3:
                break

    except Exception as e:
        st.warning(f"채널 데이터 수집 오류: {e}")
        return []

    videos.sort(key=lambda v: v["view_count"], reverse=True)
    return videos[:max_results]


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_top_liked_comments(video_id: str, n: int = 3) -> list[dict]:
    """좋아요 수 기준 상위 댓글 (SORT_BY_POPULAR 후 likeCount 정렬)."""
    try:
        dl = YoutubeCommentDownloader()
        comments = []
        for c in dl.get_comments_from_url(
            f"https://www.youtube.com/watch?v={video_id}",
            sort_by=SORT_BY_POPULAR,
        ):
            comments.append({
                "text":        c.get("text", ""),
                "author":      c.get("author", ""),
                "like_count":  int(c.get("votes", 0) or 0),
                "reply_count": int(c.get("reply_count", 0) or 0),
                "published":   c.get("time", ""),
            })
            if len(comments) >= 50:
                break

        comments.sort(key=lambda c: c["like_count"], reverse=True)
        return comments[:n]
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_top_relevance_comments(video_id: str, n: int = 3) -> list[dict]:
    """YouTube 인기순 상위 댓글."""
    try:
        dl = YoutubeCommentDownloader()
        comments = []
        for c in dl.get_comments_from_url(
            f"https://www.youtube.com/watch?v={video_id}",
            sort_by=SORT_BY_POPULAR,
        ):
            comments.append({
                "text":        c.get("text", ""),
                "author":      c.get("author", ""),
                "like_count":  int(c.get("votes", 0) or 0),
                "reply_count": int(c.get("reply_count", 0) or 0),
                "published":   c.get("time", ""),
            })
            if len(comments) >= n:
                break

        return comments
    except Exception:
        return []
