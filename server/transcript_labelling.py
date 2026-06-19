import logging
import os

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

from classifier import load_classifier

ytt_api = YouTubeTranscriptApi()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

_classifier = load_classifier()

logger = logging.getLogger(__name__)

WINDOW_SIZE = 20
STRIDE = 5


def _ner_enabled() -> bool:
    return os.getenv("NER_ENABLED", "false").lower() in ("1", "true", "yes")


def _orgs_for_ad_window(segment_text: str) -> list[str]:
    if not _ner_enabled():
        return []
    from org_extractor import get_orgs

    return get_orgs(segment_text)


class TranscriptFetchError(RuntimeError):
    """Raised when the YouTube transcript cannot be fetched."""


def _build_windows(fetched_transcript) -> list[tuple[str, float]]:
    windows = []
    for index in range(0, len(fetched_transcript) - WINDOW_SIZE, STRIDE):
        segment_text = " ".join(
            snippet.text for snippet in fetched_transcript[index: index + WINDOW_SIZE]
        )
        segment_start = fetched_transcript[index].start
        windows.append((segment_text, segment_start))
    return windows


def _classify_windows(texts: list[str]) -> list[int]:
    return _classifier.predict(texts)


def get_labelled_tscript(video_id: str) -> list[dict]:
    logger.info("Fetching transcript video_id=%s", video_id)
    try:
        fetched_transcript = ytt_api.fetch(video_id)
    except Exception as exc:
        logger.error(
            "Transcript fetch failed video_id=%s error=%s",
            video_id,
            exc,
        )
        raise TranscriptFetchError(
            f"Failed to fetch transcript for video {video_id}"
        ) from exc

    if not fetched_transcript:
        logger.warning("Empty transcript video_id=%s", video_id)
        return []

    windows = _build_windows(fetched_transcript)
    if not windows:
        logger.warning(
            "Transcript too short for windows video_id=%s snippet_count=%d",
            video_id,
            len(fetched_transcript),
        )
        return []

    texts = [window[0] for window in windows]
    labels = _classify_windows(texts)

    segments = []
    for (segment_text, segment_start), predicted_class in zip(windows, labels):
        orgs = _orgs_for_ad_window(
            segment_text) if predicted_class == 1 else []
        segments.append(
            {
                "text": segment_text,
                "start": segment_start,
                "label": predicted_class,
                "orgs": orgs,
            }
        )

    ad_count = sum(1 for segment in segments if segment["label"] == 1)
    logger.info(
        "Labelled transcript video_id=%s window_count=%d ad_window_count=%d",
        video_id,
        len(segments),
        ad_count,
    )
    return segments


def compute_intervals(data, interval_threshold=5, min_duration=45):
    """
    input: list of dicts with keys 'text', 'start', 'label'

    output: list of dicts with keys 'start_time', 'end_time'
    """

    data.sort(key=lambda x: x["start"])

    intervals = []

    i = 0
    while i < len(data):
        if data[i]["label"] != 1:
            i += 1
            continue

        start_time = data[i]["start"]
        orgs: list[str] = []
        j = i
        while j < len(data) and data[j]["label"] == 1:
            orgs = list(set(orgs + data[j].get("orgs", [])))
            j += 1

        if j < len(data) and data[j]["label"] == 0:
            intervals.append(
                {
                    "start_time": start_time,
                    "end_time": data[j]["start"],
                    "orgs": orgs,
                }
            )
        i = j

    intervals_merged = []

    i = 0
    while i < len(intervals):
        intervals_merged.append(intervals[i].copy())
        for j in range(i, len(intervals)):
            if (
                intervals[j]["start_time"] - intervals_merged[-1]["end_time"]
                <= interval_threshold
            ):
                intervals_merged[-1]["end_time"] = intervals[j]["end_time"]
                intervals_merged[-1]["orgs"] = list(
                    set(
                        intervals_merged[-1].get("orgs", [])
                        + intervals[j].get("orgs", [])
                    )
                )
                i += 1
            else:
                i = j
                break

    intervals_merged = [
        x
        for x in intervals_merged
        if x["end_time"] - x["start_time"] > min_duration
    ]

    for interval in intervals_merged:
        orgs = sorted(set(interval.get("orgs", [])))
        interval["orgs"] = orgs if orgs else ["UNKNOWN"]

    return intervals_merged
