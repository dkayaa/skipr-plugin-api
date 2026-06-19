import re
from urllib.parse import parse_qs, urlparse

_VIDEO_ID_PATTERN = re.compile(r"^[\w-]{11}$")


class YouTubeUrlError(ValueError):
    pass


def parse_video_id(link: str | None) -> str:
    if link is None or not link.strip():
        raise YouTubeUrlError("Missing required query parameter: link")

    parsed = urlparse(link.strip())

    if not parsed.netloc:
        raise YouTubeUrlError("Invalid link: not a valid URL")

    host = parsed.netloc.removeprefix("www.").lower()
    video_id = _extract_video_id(host, parsed.path, parsed.query)

    if video_id is None:
        raise YouTubeUrlError("Invalid link: unsupported YouTube URL format")

    if not _VIDEO_ID_PATTERN.match(video_id):
        raise YouTubeUrlError("Invalid link: video ID must be 11 characters")

    return video_id


def _extract_video_id(host: str, path: str, query: str) -> str | None:
    if host == "youtu.be":
        return _first_path_segment(path)

    if host not in ("youtube.com", "m.youtube.com", "music.youtube.com"):
        return None

    if path in ("/watch", "/watch/"):
        params = parse_qs(query)
        values = params.get("v")
        return values[0] if values else None

    for prefix in ("/embed/", "/v/", "/shorts/"):
        if path.startswith(prefix):
            return _first_path_segment(path[len(prefix):])

    return None


def _first_path_segment(path: str) -> str | None:
    segment = path.strip("/").split("/")[0]
    return segment or None
