
class YouTubeTranscriptApi:
    @staticmethod
    def get_transcript(video_id):
        return [{"text": "Example transcript line."}]

    @staticmethod
    def list_transcripts(video_id):
        return "Dummy transcript list"

    @staticmethod
    def get_transcripts(video_ids):
        return {"video_id": "Transcript"}
