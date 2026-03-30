import logging

import requests

from mygo.devtools import no_error

from mod import textcompare, tools


logger = logging.getLogger(__name__)

SEARCH_URL = "https://lrclib.net/api/search"
REQUEST_TIMEOUT = 10
RATIO_THRESHOLD = 0.2
RESULT_CAP = 3

headers = {
    "User-Agent": "LrcApiMMy/1.0",
}


def _pick_title(item: dict) -> str:
    return item.get("trackName") or item.get("name") or ""


def _pick_lyrics(item: dict) -> str:
    synced_lyrics = item.get("syncedLyrics")
    if isinstance(synced_lyrics, str) and synced_lyrics.strip():
        return synced_lyrics

    plain_lyrics = item.get("plainLyrics")
    if isinstance(plain_lyrics, str) and plain_lyrics.strip():
        return plain_lyrics

    return ""


@no_error(throw=logger.info,
          exceptions=(requests.RequestException, ValueError, AttributeError))
def search(title="", artist="", album="") -> list:
    if not title:
        return []

    params = {"track_name": title}
    if artist:
        params["artist_name"] = artist
    if album:
        params["album_name"] = album

    response = requests.get(
        SEARCH_URL,
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    search_result = response.json()
    if not isinstance(search_result, list):
        return []

    logger.info(
        "LRCLIB request succeeded: title=%r artist=%r album=%r results=%d",
        title,
        artist,
        album,
        len(search_result),
    )

    candidate_songs = []
    for item in search_result:
        if not isinstance(item, dict):
            continue

        lyrics = _pick_lyrics(item)
        if not lyrics or item.get("instrumental"):
            continue

        track_title = _pick_title(item)
        artist_name = item.get("artistName") or ""
        album_name = item.get("albumName") or ""

        title_ratio = max(
            textcompare.association(title, track_title),
            textcompare.association(title, item.get("name") or ""),
        )
        artist_ratio = textcompare.assoc_artists(artist, artist_name)
        album_ratio = textcompare.association(album, album_name)

        ratio = (title_ratio * (artist_ratio + album_ratio) / 2.0) ** 0.5
        if ratio < RATIO_THRESHOLD:
            continue

        candidate_songs.append({
            "ratio": ratio,
            "item": {
                "title": track_title or title,
                "album": album_name,
                "artist": artist_name,
                "lyrics": tools.standard_lrc(lyrics),
                "cover": "",
                "id": tools.calculate_md5(
                    f"title:{track_title or title};artists:{artist_name};album:{album_name}",
                    base="decstr",
                ),
            },
        })

    candidate_songs.sort(key=lambda x: x["ratio"], reverse=True)
    return [item["item"] for item in candidate_songs[:RESULT_CAP]]


if __name__ == "__main__":
    print(search(title="光辉岁月", artist="Beyond"))
