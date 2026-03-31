import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)

FALLBACK_RESPONSES = {
    "zh-TW": "抱歉～我現在看不太清楚呢，你可以告訴我你在做什麼嗎？",
    "ja": "ごめんね～今ちょっとよく見えないの。何してるか教えてくれる？",
    "en": "Sorry~ I can't see clearly right now. Can you tell me what you're doing?",
}


class VisionAnalyzer:
    def __init__(self, vision_model=None, llm_client=None, change_threshold: float = 0.3):
        self._vision_model = vision_model
        self._llm_client = llm_client
        self._change_threshold = change_threshold
        self._last_hash: Optional[str] = None

    def _image_hash(self, image_data: bytes) -> str:
        return hashlib.md5(image_data).hexdigest()

    def has_significant_change(self, current: bytes, previous: Optional[bytes]) -> bool:
        if previous is None:
            return True
        return self._image_hash(current) != self._image_hash(previous)

    def analyze_single(self, image_data: bytes, language: str = "zh-TW", context: str = "") -> dict:
        if self._vision_model is None and self._llm_client is None:
            return {
                "text": FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en"]),
                "emotion": "neutral",
            }
        return {
            "text": FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en"]),
            "emotion": "neutral",
        }

    def analyze_stream(self, current_frame: bytes, previous_frame: Optional[bytes],
                       language: str = "zh-TW", context: str = "") -> Optional[dict]:
        if not self.has_significant_change(current_frame, previous_frame):
            return None
        return self.analyze_single(current_frame, language, context)
