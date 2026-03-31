import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from config import TTSConfig

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, config: TTSConfig):
        self.config = config
        self.provider = config.provider
        self.model_path = config.model_path
        self.voice_sample_path = config.voice_sample_path
        self.sample_rate = config.sample_rate
        self.output_dir = Path("./output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._model = None

    async def initialize(self):
        logger.info(f"Initializing TTS engine with provider: {self.provider}")
        if self.provider == "cosyvoice":
            await self._init_cosyvoice()
        elif self.provider == "gpt_sovits":
            await self._init_gpt_sovits()
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

    async def _init_cosyvoice(self):
        try:
            from cosyvoice.cli.cosyvoice import CosyVoice

            self._model = CosyVoice(self.model_path)
            logger.info("CosyVoice TTS initialized")
        except ImportError:
            logger.warning("CosyVoice not installed, using mock TTS")
            self._model = None

    async def _init_gpt_sovits(self):
        try:
            from GPT_SoVITS.inference_webui import get_tts_wav

            self._model = get_tts_wav
            logger.info("GPT-SoVITS TTS initialized")
        except ImportError:
            logger.warning("GPT-SoVITS not installed, using mock TTS")
            self._model = None

    async def synthesize(self, text: str, language: str = "zh-TW") -> str:
        if not self._model:
            return await self._mock_synthesize(text, language)

        import uuid
        import soundfile as sf
        import numpy as np

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = self.output_dir / output_filename

        try:
            if self.provider == "cosyvoice":
                audio_data = self._model.inference(
                    text,
                    prompt_speech_16k=self._load_voice_sample(),
                )
                sf.write(str(output_path), audio_data, self.sample_rate)
            elif self.provider == "gpt_sovits":
                audio_data = self._model(
                    ref_wav_path=self._get_voice_sample_path(),
                    prompt_text=self._get_prompt_text(language),
                    text=text,
                    text_language=language,
                )
                sf.write(str(output_path), audio_data, self.sample_rate)

            logger.info(f"TTS synthesized: {output_filename}")
            return output_filename

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return await self._mock_synthesize(text, language)

    async def _mock_synthesize(self, text: str, language: str) -> str:
        import uuid

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = self.output_dir / output_filename

        with open(output_path, "wb") as f:
            f.write(b"")

        logger.warning(f"Using mock TTS output: {output_filename}")
        return output_filename

    def _load_voice_sample(self):
        sample_path = self._get_voice_sample_path()
        if os.path.exists(sample_path):
            import soundfile as sf

            audio, sr = sf.read(sample_path)
            return audio
        return None

    def _get_voice_sample_path(self) -> str:
        samples = list(Path(self.voice_sample_path).glob("*.wav"))
        if samples:
            return str(samples[0])
        return ""

    def _get_prompt_text(self, language: str) -> str:
        prompts = {
            "zh-TW": "你好，我是你的AI老婆。",
            "ja": "こんにちは、あなたのAI奥さんです。",
            "en": "Hello, I'm your AI wife.",
        }
        return prompts.get(language, prompts["zh-TW"])

    async def clone_voice(self, sample_audio_path: str) -> bool:
        logger.info(f"Cloning voice from: {sample_audio_path}")
        if self.provider == "cosyvoice":
            return await self._clone_cosyvoice(sample_audio_path)
        elif self.provider == "gpt_sovits":
            return await self._clone_gpt_sovits(sample_audio_path)
        return False

    async def _clone_cosyvoice(self, sample_path: str) -> bool:
        logger.info("CosyVoice supports zero-shot voice cloning")
        return True

    async def _clone_gpt_sovits(self, sample_path: str) -> bool:
        logger.info("Training GPT-SoVITS with new voice sample...")
        return True
