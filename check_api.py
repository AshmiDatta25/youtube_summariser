import sys
sys.path.insert(0, '.')

from youtube_transcript_api import YouTubeTranscriptApi
import inspect

print("=== Debug Info ===")
print("Module path:", inspect.getfile(YouTubeTranscriptApi))
print("Has get_transcript:", hasattr(YouTubeTranscriptApi, "get_transcript"))

print("\nAvailable attributes in YouTubeTranscriptApi:")
for name in dir(YouTubeTranscriptApi):
    if not name.startswith("_"):
        print("-", name)
