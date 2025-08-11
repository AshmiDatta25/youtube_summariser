# pip install yt-dlp google-genai requests fastapi uvicorn

import os
import re
import html
import json
import requests
from yt_dlp import YoutubeDL
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# FastAPI app instance
ytsum = FastAPI()

# === Constants ===
GEMINI_API_KEY = "AIzaSyCJecQ8qkWfOGXwpDN9ltjUqChoZWqJ_qA"
GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=Kw4UHNnilPY"

# === Quiet logger for yt-dlp ===
class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)

# === Extract transcript ===
def get_clean_transcript(video_url: str, lang: str = "en") -> str:
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [lang],
        "quiet": True,
        "logger": QuietLogger(),
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        subs = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}
        track = (subs.get(lang) or auto.get(lang) or [{}])[-1]
        if "url" not in track:
            raise RuntimeError("No transcript available for this video / language.")
        vtt_or_srt_text = requests.get(track["url"]).text

    return _clean_caption_text(vtt_or_srt_text)

def _clean_caption_text(text: str) -> str:
    lines = text.strip().splitlines()
    transcript_lines = []
    ts_vtt_re = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d+\s+-->")
    ts_srt_re = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->")
    number_re = re.compile(r"^\d+$")

    for line in lines:
        if number_re.match(line):
            continue
        if ts_vtt_re.match(line) or ts_srt_re.match(line):
            continue
        if "align:" in line or "position:" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)
        line = html.unescape(line).strip()
        if not line or re.match(r"^\[.*\]$", line):
            continue
        transcript_lines.append(line)

    clean_lines = []
    last = None
    for l in transcript_lines:
        if l != last:
            clean_lines.append(l)
            last = l

    return "\n".join(clean_lines)

# === Gemini summarization ===
def summarize_with_gemini(transcript_text: str) -> dict:
    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ No API key found. Falling back to local summary.")
        return local_fallback_summary(transcript_text)

    client = genai.Client(api_key=api_key)
    prompt = f'''
Return ONLY valid JSON with:
  "topic_name": short title of the main topic
  "topic_summary": brief summary

No extra text, no markdown.

Transcript:
\"\"\"{transcript_text}\"\"\"
'''

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
        )
        raw = (resp.text or "").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                raise ValueError(f"Gemini did not return valid JSON:\n{raw}")
            return json.loads(m.group(0))
    except ClientError as e:
        print(f"[Gemini ERROR] {e}. Falling back to local summarizer...")
        return local_fallback_summary(transcript_text)
    except Exception as e:
        print(f"[Gemini ERROR - unexpected] {e}. Falling back to local summarizer...")
        return local_fallback_summary(transcript_text)

def local_fallback_summary(text: str, max_chars: int = 800) -> dict:
    first = text[:max_chars].splitlines()
    lines = [l for l in first if l.strip()][:5]
    return {
        "topic_name": "Transcript Summary (local fallback)",
        "topic_summary": " ".join(lines) if lines else "No transcript text available."
    }

# === Extract video ID (optional helper) ===
def extract_video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", url)
    return match.group(1) if match else ""

# === FastAPI route ===
@ytsum.get("/summarize")
def get_summary(url: str = DEFAULT_YOUTUBE_URL):
    try:
        video_id = extract_video_id(url)
        print(f"🔍 Extracting transcript for video ID: {video_id}")
        transcript = get_clean_transcript(url)

        print("🤖 Summarising with Gemini...")
        summary = summarize_with_gemini(transcript)

        return JSONResponse(content=summary)
    except Exception as e:
        return {"error": str(e)}

# === Optional CLI runner ===
if __name__ == "__main__":
    transcript = get_clean_transcript(DEFAULT_YOUTUBE_URL)
    print(f"📝 Transcript length: {len(transcript)} chars")

    with open("transcript.txt", "w", encoding="utf-8") as f:
        f.write(transcript)
    print("✅ Transcript saved to transcript.txt")

    summary = summarize_with_gemini(transcript)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    with open("summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("✅ Summary saved to summary.json")
