import youtube_transcript_api
from youtube_transcript_api import YouTubeTranscriptApi

print("== Debug Info ==")
print("Module path:", youtube_transcript_api.__file__)
print("Class:", YouTubeTranscriptApi)
print("Has get_transcript:", hasattr(YouTubeTranscriptApi, "get_transcript"))
