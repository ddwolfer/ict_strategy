"""Download transcripts + titles for the 34 ICT videos into research/transcripts/."""
import json
import sys
import time
import urllib.request
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

VIDEO_IDS = [
    "vCvRrINpknI", "rNn0JkItAGo", "4f1vjQMlV50", "s1gCDuzcukU", "KQdsa7S1LoQ",
    "E0sA_SWIxKM", "ze8jAMdmBqc", "2CWIbdP1kZw", "SObhjCvXCNk", "H05w52zQGdQ",
    "JN_uaDDZ0rc", "bcp19tiJZA0", "NB7Bku099tU", "2fgXDt3T3XE", "BMYrtYMisnA",
    "fAcnhdaowME", "V0TFp7AvZqw", "5FTMSC4kLZM", "yC-gQhvexGg", "beTnmkbuUjg",
    "_7oZZ2bhEGU", "oheyS8MUqno", "G4lhid5dh0I", "fHp3JkxFFjU", "F-8hPvSyIB4",
    "twIPoG2TZ1o", "YIxurbDNrWM", "CTS27DsveNs", "E57WWIEjhvU", "UtdXo9HJHKU",
    "pblXxWhnRz4", "3xgtrXok-xs", "xi0N9BG1Qvs", "kNlySn81dmo",
]

OUT = Path(__file__).parent / "transcripts"
OUT.mkdir(exist_ok=True)


def fetch_title(video_id: str) -> str:
    url = (
        "https://www.youtube.com/oembed?url="
        f"https://www.youtube.com/watch?v={video_id}&format=json"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.load(r)["title"]
    except Exception as e:  # noqa: BLE001
        return f"<title unavailable: {e}>"


def main() -> None:
    api = YouTubeTranscriptApi()
    manifest = []
    for i, vid in enumerate(VIDEO_IDS, 1):
        title = fetch_title(vid)
        entry = {"id": vid, "title": title}
        out_file = OUT / f"{vid}.txt"
        if out_file.exists():
            entry["status"] = "cached"
        else:
            try:
                fetched = api.fetch(vid, languages=["en", "en-US", "en-GB"])
                text = "\n".join(s.text for s in fetched)
                out_file.write_text(f"# {title}\n# {vid}\n\n{text}", encoding="utf-8")
                entry["status"] = "ok"
                entry["chars"] = len(text)
            except Exception as e:  # noqa: BLE001
                entry["status"] = f"FAILED: {type(e).__name__}: {e}"
            time.sleep(1.5)
        print(f"[{i:2}/{len(VIDEO_IDS)}] {vid} {entry['status']} | {title}", flush=True)
        manifest.append(entry)
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    failed = [m for m in manifest if str(m["status"]).startswith("FAILED")]
    print(f"\nDone. {len(manifest) - len(failed)} ok, {len(failed)} failed.")
    if failed:
        for m in failed:
            print(f"  - {m['id']}: {m['status']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
