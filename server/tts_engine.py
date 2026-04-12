import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from config import TTSConfig

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, config: TTSConfig, llm_client=None):
        self.config = config
        self.provider = config.provider
        self.model_path = config.model_path
        self.voice_sample_path = config.voice_sample_path
        self.sample_rate = config.sample_rate
        self.output_dir = Path("./output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._llm_client = llm_client
        self._qwen3tts_mode = getattr(config, "qwen3tts_mode", "custom_voice")
        self._emotion_prompts = {}
        # Clean old audio files on startup (>1 hour old)
        self._cleanup_old_audio()

    def _cleanup_old_audio(self, max_age_hours: int = 1):
        """Remove audio files older than max_age_hours to prevent disk growth."""
        import time
        cutoff = time.time() - max_age_hours * 3600
        count = 0
        for f in self.output_dir.glob("*.wav"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    count += 1
            except Exception:
                pass
        if count:
            logger.info(f"Cleaned up {count} old audio files")

    async def initialize(self):
        logger.info(f"Initializing TTS engine with provider: {self.provider}")
        if self.provider == "cosyvoice":
            await self._init_cosyvoice()
        elif self.provider == "gpt_sovits":
            await self._init_gpt_sovits()
        elif self.provider == "voicebox":
            await self._init_voicebox()
        elif self.provider == "qwen3tts":
            await self._init_qwen3tts()
        elif self.provider == "nano_qwen3tts":
            await self._init_nano_qwen3tts()
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

    async def _init_voicebox(self):
        """Test Voicebox API connection."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.config.voicebox_api_url}/profiles")
                if resp.status_code == 200:
                    profiles = resp.json()
                    logger.info(
                        f"Voicebox connected: {len(profiles)} profiles available"
                    )
                    if self.config.voicebox_profile_id:
                        logger.info(
                            f"Using voice profile: {self.config.voicebox_profile_id}"
                        )
                    else:
                        logger.warning(
                            "No voicebox_profile_id set, using default voice"
                        )
                else:
                    logger.warning(f"Voicebox returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"Voicebox not available: {e}")
            self._model = None

    # Available preset speakers for CustomVoice mode
    PRESET_SPEAKERS = {
        "Ono_Anna":  {"language": "Japanese", "description": "活潑日語女聲", "gender": "female"},
        "Vivian":    {"language": "Chinese",  "description": "年輕中文女聲", "gender": "female"},
        "Serena":    {"language": "Chinese",  "description": "溫暖中文女聲", "gender": "female"},
        "Sohee":     {"language": "Korean",   "description": "韓語女聲",     "gender": "female"},
        "Ryan":      {"language": "English",  "description": "動感英語男聲", "gender": "male"},
        "Aiden":     {"language": "English",  "description": "美式英語男聲", "gender": "male"},
        "Uncle_Fu":  {"language": "Chinese",  "description": "成熟中文男聲", "gender": "male"},
        "Dylan":     {"language": "Chinese",  "description": "北京中文男聲", "gender": "male"},
        "Eric":      {"language": "Chinese",  "description": "四川中文男聲", "gender": "male"},
    }

    # ── Emotion Instruct System ──────────────────────────────────────
    # Base style (common prefix) + emotion modifier (per-emotion suffix)
    # Users can override these via /api/tts/emotion-prompts

    INSTRUCT_BASE_ZH = ""
    INSTRUCT_MODIFIER_ZH = {
        "neutral": (
            "音高: 女性中音区，语调自然平稳。"
            "语速: 适中偏慢，节奏从容。"
            "音量: 正常交谈音量。"
            "音色质感: 音色柔和清亮，温暖自然。"
            "情绪: 平静温柔，亲切友好。"
            "流畅度: 表达流畅自如。"
        ),
        "happy": (
            "音高: 女性中高音区，语调明显上扬，尾音带笑意上挑。"
            "语速: 语速明快活泼，节奏轻快有弹性。"
            "音量: 比正常稍大，笑声响亮。"
            "音色质感: 音色明亮清脆，富有活力，带着爽朗笑意。"
            "情绪: 愉悦兴奋，发自内心的开心，伴随轻笑。"
            "流畅度: 表达流畅自如，偶有因开心而加速。"
        ),
        "sad": (
            "音高: 女性中低音区，语调下沉低缓，句尾下降。"
            "语速: 语速缓慢，偶有停顿叹息。"
            "音量: 音量偏小，轻声诉说。"
            "音色质感: 声音轻柔带气息感，略带颤抖和哭腔。"
            "情绪: 悲伤低落，带着压抑的委屈，仿佛每个字都承载着沉重。"
            "流畅度: 偶有因情绪波动而产生的停顿。"
        ),
        "angry": (
            "音高: 女性中高音区，语调尖锐有力，重音明显。"
            "语速: 语速偏快，节奏紧凑急促。"
            "音量: 音量明显增大，接近斥责。"
            "音色质感: 声音尖锐有力度，带着紧绷感。"
            "情绪: 恼怒不满，语带斥责和威慑，情绪激动。"
            "流畅度: 表达连贯有力，字字分明。"
        ),
        "surprised": (
            "音高: 女性高音区，语调突然升高，起伏大。"
            "语速: 初始快速，之后放慢回味。"
            "音量: 音量突然增大。"
            "音色质感: 声音明亮，带有惊叹的气息感。"
            "情绪: 惊讶震惊，眼睛睁大的感觉，伴随惊喜。"
            "流畅度: 初始可能有短暂停顿，之后流畅。"
        ),
        "relaxed": (
            "音高: 女性低音区，语调平缓低柔。"
            "语速: 语速极慢，从容不迫。"
            "音量: 音量很小，接近耳语。"
            "音色质感: 声音温柔如丝，带有轻微气声，像在耳边低语。"
            "情绪: 放松慵懒，安静平和，带着睡意般的舒适感。"
            "流畅度: 极其流畅柔滑。"
        ),
        "horny": (
            "音高: 女性低音区，音调低沉带磁性。"
            "语速: 语速极慢，每个字都拖长。"
            "音量: 音量很小，气声明显。"
            "音色质感: 声音低沉带气声，略带沙哑和颤抖，呼吸声清晰可闻，"
            "尾音拖长上扬，带有轻微呻吟感。"
            "情绪: 害羞但沉浸其中，呼吸急促，声音轻颤，欲言又止。"
            "流畅度: 偶有因喘息而产生的自然停顿。"
        ),
    }

    async def _init_qwen3tts(self):
        """Load Qwen3-TTS model. Supports both CustomVoice and VoiceClone modes."""
        self._qwen3tts_mode = getattr(self.config, "qwen3tts_mode", "custom_voice")
        self._emotion_prompts = {}  # For voice_clone mode

        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            # Pick model based on mode
            if self._qwen3tts_mode == "custom_voice":
                model_name = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
            else:
                model_name = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

            device = self.config.qwen3tts_device
            logger.info(f"Loading Qwen3-TTS [{self._qwen3tts_mode}]: {model_name} on {device}")

            attn_impl = "sdpa"  # PyTorch native SDPA, works on Windows
            try:
                import flash_attn  # noqa: F401
                attn_impl = "flash_attention_2"  # Prefer if available
            except ImportError:
                pass

            try:
                self._model = Qwen3TTSModel.from_pretrained(
                    model_name,
                    device_map=device,
                    dtype=torch.bfloat16,
                    attn_implementation=attn_impl,
                )
            except Exception as load_err:
                logger.warning(f"from_pretrained with device_map={device} failed: {load_err}, retrying without device_map...")
                self._model = Qwen3TTSModel.from_pretrained(
                    model_name,
                    dtype=torch.bfloat16,
                    attn_implementation=attn_impl,
                )
                if torch.cuda.is_available():
                    self._model = self._model.to(device)

            if self._model is None:
                logger.error("Qwen3TTSModel.from_pretrained returned None!")
                return
            logger.info(f"Qwen3-TTS model loaded (attn={attn_impl})")

            if self._qwen3tts_mode == "custom_voice":
                speaker = getattr(self.config, "qwen3tts_speaker", "Ono_Anna")
                info = self.PRESET_SPEAKERS.get(speaker, {})
                logger.info(
                    f"CustomVoice ready: speaker={speaker} "
                    f"({info.get('description', '?')}, {info.get('language', '?')})"
                )
            else:
                # Voice clone: pre-compute prompts for each emotion ref
                self._build_clone_prompts()

        except ImportError:
            logger.error("qwen-tts not installed. Run: pip install -U qwen-tts")
            self._model = None
        except Exception as e:
            logger.error(f"Qwen3-TTS initialization failed: {e}")
            self._model = None

    def _build_clone_prompts(self):
        """Pre-compute voice_clone_prompt for each emotion reference audio."""
        self._emotion_prompts = {}
        emotion_refs = self.config.qwen3tts_emotion_refs or {}
        ref_texts = self.config.qwen3tts_ref_texts or {}
        x_vector_only = self.config.qwen3tts_x_vector_only

        if not emotion_refs:
            logger.warning(
                "No qwen3tts_emotion_refs configured. "
                "Voice clone needs reference audio files."
            )
            return

        for emotion, audio_path in emotion_refs.items():
            if not os.path.exists(audio_path):
                logger.warning(f"Emotion ref audio not found: {emotion} -> {audio_path}")
                continue
            ref_text = ref_texts.get(emotion, "")
            try:
                use_xvec = x_vector_only or not ref_text
                if not ref_text and not x_vector_only:
                    logger.warning(f"No ref_text for '{emotion}', using x_vector_only")
                prompt = self._model.create_voice_clone_prompt(
                    ref_audio=audio_path,
                    ref_text=ref_text if not use_xvec else "",
                    x_vector_only_mode=use_xvec,
                )
                self._emotion_prompts[emotion] = prompt
                logger.info(f"Voice prompt ready: {emotion} (x_vector={use_xvec})")
            except Exception as e:
                logger.error(f"Failed to build voice prompt for {emotion}: {e}")

        if self._emotion_prompts:
            logger.info(
                f"VoiceClone ready with {len(self._emotion_prompts)} emotion prompts: "
                f"{list(self._emotion_prompts.keys())}"
            )
        else:
            logger.warning("No emotion prompts built — check config")

    async def _init_nano_qwen3tts(self):
        """Test connection to nano-qwen3tts server (WSL2)."""
        import httpx
        nano_url = getattr(self.config, 'nano_qwen3tts_url', 'http://localhost:8091')
        self._nano_url = nano_url
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{nano_url}/health")
                if resp.status_code == 200:
                    logger.info(f"nano-qwen3tts connected at {nano_url}")
                    # Get available voices
                    voices_resp = await client.get(f"{nano_url}/voices")
                    if voices_resp.status_code == 200:
                        voices = voices_resp.json()
                        logger.info(f"nano-qwen3tts voices: {voices.get('default', [])}")
                else:
                    logger.warning(f"nano-qwen3tts returned {resp.status_code}")
        except Exception as e:
            logger.warning(f"nano-qwen3tts not available at {nano_url}: {e}")

    async def _synthesize_nano_qwen3tts(
        self, text: str, language: str = "zh-TW", emotion: str = "neutral"
    ) -> tuple[str, list[dict], str]:
        """Synthesize via nano-qwen3tts HTTP server (fast, WSL2)."""
        import uuid
        import httpx
        import struct

        synth_text, sentences, instruct, tts_language = await self._prepare_tts_qwen3tts(
            text, language, emotion
        )
        if not sentences:
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], ""

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = self.output_dir / output_filename

        try:
            speaker = getattr(self.config, 'qwen3tts_speaker', 'Ono_Anna')
            all_pcm = b''

            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
                for i, sent in enumerate(sentences):
                    payload = {
                        "text": sent,
                        "language": tts_language,
                        "speaker": speaker,
                        "instruct": instruct,
                    }
                    logger.info(f"nano-qwen3tts [{i+1}/{len(sentences)}]: {sent[:40]}...")
                    async with session.post(f"{self._nano_url}/v1/audio/speech", json=payload) as resp:
                        resp.raise_for_status()
                        pcm_data = await resp.read()
                    if pcm_data:
                        all_pcm += pcm_data
                        logger.info(f"nano-qwen3tts [{i+1}]: got {len(pcm_data)} bytes PCM")
                    else:
                        logger.warning(f"nano-qwen3tts [{i+1}]: empty response")

            if not all_pcm:
                raise RuntimeError("No audio data received from nano-qwen3tts")

            # Convert raw PCM 16-bit mono 24kHz to WAV
            sample_rate = 24000

            with open(str(output_path), "wb") as f:
                data_size = len(all_pcm)
                f.write(b"RIFF")
                f.write(struct.pack("<I", 36 + data_size))
                f.write(b"WAVE")
                f.write(b"fmt ")
                f.write(struct.pack("<I", 16))
                f.write(struct.pack("<H", 1))  # PCM
                f.write(struct.pack("<H", 1))  # mono
                f.write(struct.pack("<I", sample_rate))
                f.write(struct.pack("<I", sample_rate * 2))
                f.write(struct.pack("<H", 2))  # block align
                f.write(struct.pack("<H", 16))  # bits per sample
                f.write(b"data")
                f.write(struct.pack("<I", data_size))
                f.write(all_pcm)

            logger.info(f"nano-qwen3tts synthesized: {output_filename} ({len(sentences)} parts, {len(all_pcm)} bytes)")
            visemes = self._generate_visemes_from_audio(str(output_path), synth_text)
            return output_filename, visemes, synth_text

        except Exception as e:
            import traceback
            logger.error(f"nano-qwen3tts synthesis failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], synth_text

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

    INSTRUCT_BASE_JA = ""
    INSTRUCT_MODIFIER_JA = {
        "neutral": (
            "pitch: Female mid-range, natural and stable intonation. "
            "speed: Moderate pace, relaxed rhythm. "
            "volume: Normal conversational level. "
            "texture: Soft, clear, and warm vocal quality. "
            "emotion: Calm, gentle, and friendly. "
            "fluency: Smooth and natural delivery."
        ),
        "happy": (
            "pitch: Female mid-high range, intonation rising with excitement, upward inflections at phrase ends. "
            "speed: Brisk and lively pace with bouncy rhythm. "
            "volume: Slightly louder than normal, bright projection. "
            "texture: Bright, crisp vocal quality with audible smile. "
            "emotion: Genuinely joyful, radiating warmth, with light laughter. "
            "fluency: Fluent and energetic, occasionally speeding up with excitement."
        ),
        "sad": (
            "pitch: Female low range, intonation descending, sentences trailing off softly. "
            "speed: Slow pace with pauses for sighing. "
            "volume: Quiet, speaking softly. "
            "texture: Breathy, slightly trembling voice with a hint of crying. "
            "emotion: Sorrowful and subdued, carrying suppressed grief in every word. "
            "fluency: Occasional pauses from emotional weight."
        ),
        "angry": (
            "pitch: Female mid-high range, sharp and forceful intonation with strong stress. "
            "speed: Fast and clipped pace, tight rhythm. "
            "volume: Notably loud, approaching a scolding tone. "
            "texture: Sharp, tense vocal quality with intensity. "
            "emotion: Frustrated and indignant, conveying irritation and displeasure. "
            "fluency: Continuous and forceful, each word clearly articulated."
        ),
        "surprised": (
            "pitch: Female high range, sudden sharp rise in pitch, wide intonation swings. "
            "speed: Initially fast, then slowing to process. "
            "volume: Suddenly louder. "
            "texture: Bright with breathiness from shock. "
            "emotion: Genuine surprise and astonishment, eyes-wide feeling. "
            "fluency: Brief initial pause of shock, then fluent."
        ),
        "relaxed": (
            "pitch: Female low range, gentle and flat intonation. "
            "speed: Very slow, unhurried pace. "
            "volume: Very quiet, close to a whisper. "
            "texture: Silky smooth with light breathiness, like whispering by the ear. "
            "emotion: Deeply relaxed and drowsy, peaceful comfort. "
            "fluency: Extremely smooth and flowing."
        ),
        "horny": (
            "pitch: Female low range with magnetic, husky quality. "
            "speed: Extremely slow, each syllable drawn out. "
            "volume: Very quiet with prominent breath sounds. "
            "texture: Low, breathy voice with slight rasp and tremor, "
            "audible breathing between phrases, trailing ends with soft moans. "
            "emotion: Shy yet immersed, quickened breathing, voice quivering, hesitant. "
            "fluency: Natural pauses from breathlessness."
        ),
    }

    def get_instruct(self, emotion: str, language: str = "Japanese") -> str:
        """Build instruct string from base + modifier. Supports runtime overrides."""
        # Check for user-customized prompts first
        custom = getattr(self, '_custom_prompts', {})
        custom_key = f"{language}_{emotion}"
        if custom_key in custom:
            return custom[custom_key]

        if language == "Chinese":
            base = self.INSTRUCT_BASE_ZH
            modifier = self.INSTRUCT_MODIFIER_ZH.get(emotion, "")
        else:
            base = self.INSTRUCT_BASE_JA
            modifier = self.INSTRUCT_MODIFIER_JA.get(emotion, "")
        return (base + modifier).strip()

    def set_custom_prompt(self, language: str, emotion: str, prompt: str):
        """Set a custom instruct prompt for a specific language+emotion."""
        if not hasattr(self, '_custom_prompts'):
            self._custom_prompts = {}
        self._custom_prompts[f"{language}_{emotion}"] = prompt

    def clear_custom_prompt(self, language: str, emotion: str):
        """Reset a custom prompt back to default."""
        if hasattr(self, '_custom_prompts'):
            self._custom_prompts.pop(f"{language}_{emotion}", None)

    def get_all_prompts(self) -> dict:
        """Return all current prompts (default + custom overrides)."""
        result = {}
        for lang, base, modifiers in [
            ("Japanese", self.INSTRUCT_BASE_JA, self.INSTRUCT_MODIFIER_JA),
            ("Chinese", self.INSTRUCT_BASE_ZH, self.INSTRUCT_MODIFIER_ZH),
        ]:
            result[lang] = {
                "base": base,
                "emotions": {},
            }
            for emo in modifiers:
                result[lang]["emotions"][emo] = {
                    "modifier": modifiers[emo],
                    "full": self.get_instruct(emo, lang),
                    "is_custom": f"{lang}_{emo}" in getattr(self, '_custom_prompts', {}),
                }
        return result

    async def synthesize(
        self, text: str, language: str = "zh-TW", emotion: str = "neutral"
    ) -> tuple[str, list[dict], str]:
        """Returns (audio_filename, visemes, ja_text)."""
        if self.provider == "voicebox":
            return await self._synthesize_voicebox(text, language, emotion)
        if self.provider == "qwen3tts":
            return await self._synthesize_qwen3tts(text, language, emotion)
        if self.provider == "nano_qwen3tts":
            return await self._synthesize_nano_qwen3tts(text, language, emotion)
        if not self._model:
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], ""

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
            visemes = self._generate_visemes_from_audio(str(output_path), text)
            return output_filename, visemes, ""

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], ""

    _TRANSLATE_BASE = (
        "あなたは中国語→日本語の翻訳者です。\n"
        "【絶対ルール】出力は100%日本語のみ。中国語を一文字でも残してはいけません。\n"
        "【キャラ設定】アニメ風の可愛い妻キャラ「アイ」のセリフです。\n"
        "【翻訳ルール】\n"
        "- 「小愛」「我」「人家」→「あたし」（自称は必ず「あたし」）\n"
        "- 「老公」「親愛的」→「あなた」「ダーリン」\n"
        "- 括弧内の動作描写（*臉紅*、（低下頭）等）→ 全て削除\n"
        "- 絵文字 → 全て削除\n"
        "- 「小愛」という名前が出る場合→「アイ」に置換\n"
        "- 可愛く甘えた口調を保つ（よ、ね、の、かな、なの）\n"
        "翻訳のみ出力。説明不要。"
    )

    _TRANSLATE_HORNY = (
        "あなたは中国語→日本語の翻訳者です。\n"
        "【絶対ルール】出力は100%日本語のみ。中国語を一文字でも残してはいけません。\n"
        "【キャラ設定】アニメ風の可愛い妻キャラ「アイ」の、親密シーンのセリフです。\n"
        "【翻訳ルール】\n"
        "- 「小愛」「我」「人家」→「あたし」（自称は必ず「あたし」）\n"
        "- 「老公」「親愛的」→「あなた」「ダーリン」\n"
        "- 括弧内の動作描写 → 全て削除\n"
        "- 絵文字 → 全て削除\n"
        "- 「小愛」→「アイ」\n"
        "【重要：擬声語・喘ぎ声を追加すること】\n"
        "- セリフの間に自然な擬声語を挿入する：\n"
        "  んっ…、はぁ…、あっ…、ちゅぷ…、じゅる…、んむ…、くちゅ…、れろ…\n"
        "- 吐息混じりの甘い声を表現する\n"
        "- 恥ずかしそうだけど感じている雰囲気を出す\n"
        "- 長い吸い付き音（ちゅぱ…じゅるる…）を適度に入れる\n"
        "翻訳のみ出力。説明不要。"
    )

    async def _translate_to_ja(self, text: str, language: str, emotion: str = "neutral") -> str:
        """Translate text to Japanese for voice synthesis.
        Always uses primary provider (not fallback) since translation won't trigger content filters."""
        if language == "ja":
            return text
        try:
            if not self._llm_client:
                logger.warning("No LLM client for translation, using original text")
                return text

            prompt = self._TRANSLATE_HORNY if emotion == "horny" else self._TRANSLATE_BASE

            # If primary is Ollama (local), prefer fallback (cloud) for better translation
            # If primary is cloud, use primary directly
            use_fb = self._llm_client._is_ollama and self._llm_client.has_fallback
            result = await self._llm_client.chat(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=2048,
                temperature=0.3,
                think=False,
                use_fallback=use_fb,
            )
            ja_text = result.strip() if isinstance(result, str) else str(result).strip()
            return ja_text
        except Exception as e:
            logger.warning(f"Translation to Japanese failed: {e}, using original text")
            return text

    @staticmethod
    def _strip_emoji(text: str) -> str:
        """Remove emoji and special symbols from text."""
        import re
        return re.sub(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
            r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F'
            r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
            r'\U00002600-\U000026FF\U0000200D\U00002640\U00002642]+', '', text
        ).strip()

    def _concat_wav(self, parts: list[Path], output_path: Path):
        """Concatenate multiple WAV files, trimming trailing silence."""
        import wave
        import struct

        def trim_silence(frames_bytes: bytes, sample_width: int, threshold: int = 300) -> bytes:
            """Trim trailing silence from raw PCM frames."""
            if sample_width != 2:
                return frames_bytes
            samples = struct.unpack(f"<{len(frames_bytes)//2}h", frames_bytes)
            end = len(samples)
            # Walk backwards to find last audible sample
            while end > 0 and abs(samples[end - 1]) < threshold:
                end -= 1
            # Keep a natural tail (~200ms at 22050Hz ≈ 4400 samples)
            end = min(len(samples), end + 4400)
            return struct.pack(f"<{end}h", *samples[:end])

        with wave.open(str(output_path), "wb") as out:
            params_set = False
            for p in parts:
                with wave.open(str(p), "rb") as inp:
                    if not params_set:
                        out.setparams(inp.getparams())
                        params_set = True
                    raw = inp.readframes(inp.getnframes())
                    trimmed = trim_silence(raw, inp.getsampwidth())
                    out.writeframes(trimmed)

    async def _prepare_tts(
        self, text: str, language: str, emotion: str
    ) -> tuple[str, list[str], str, str]:
        """Shared preprocessing: translate, split sentences, build instruct.
        Returns (ja_text, sentences, instruct, profile_id)."""
        import re as _re

        # Strip emoji before translation
        clean_text = self._strip_emoji(text)
        if not clean_text:
            return "", [], "", ""

        # Strip JSON/code blocks that LLM sometimes outputs in chat mode
        clean_text = _re.sub(r'```json\s*\{[\s\S]*?\}\s*```', '', clean_text)
        clean_text = _re.sub(r'```[\s\S]*?```', '', clean_text)
        clean_text = _re.sub(r'\{["\s]*tool[\s\S]*?\}', '', clean_text)
        clean_text = clean_text.strip()
        if not clean_text:
            return "", [], "", ""

        # Translate to Japanese for voice synthesis
        ja_text = await self._translate_to_ja(clean_text, language, emotion)
        # Clean special characters that cause TTS glitch
        ja_text = ja_text.replace("～", "ー")
        ja_text = ja_text.replace("…", "、").replace("...", "、")
        ja_text = ja_text.replace("♡", "").replace("♪", "").replace("☆", "").replace("★", "")
        ja_text = ja_text.replace("→", "").replace("←", "").replace("↑", "").replace("↓", "")
        ja_text = ja_text.replace("《", "").replace("》", "").replace("【", "").replace("】", "")
        ja_text = ja_text.replace("「", "").replace("」", "").replace("『", "").replace("』", "")
        ja_text = ja_text.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
        ja_text = _re.sub(r'[*#_`~|<>{}\\\/\[\]]', '', ja_text)  # markdown/code symbols
        ja_text = _re.sub(r'\s+', ' ', ja_text).strip()
        logger.info(f"TTS text (ja): {ja_text[:80]}...")

        # Split on sentence-ending punctuation and clause boundaries
        # Primary split: 。！？ (sentence end)
        # Secondary split: 、 ー after 8+ chars (clause boundary for emotional pacing)
        raw = _re.split(r'(?<=[。！？])\s*', ja_text)
        # Further split long segments on clause boundaries
        fine = []
        for seg in raw:
            seg = seg.strip()
            if not seg or len(seg) <= 1:
                continue
            if len(seg) > 25:
                # Split on 、 but keep the delimiter with the left part
                parts = _re.split(r'(?<=、)', seg)
                merged_part = ""
                for p in parts:
                    if merged_part and len(merged_part) >= 8:
                        fine.append(merged_part)
                        merged_part = p
                    else:
                        merged_part += p
                if merged_part:
                    fine.append(merged_part)
            else:
                fine.append(seg)
        # Merge short fragments (< 10 chars) into previous — prevents voice instability on tiny segments
        sentences = []
        for s in fine:
            s = s.strip()
            if not s:
                continue
            if len(s) < 10 and sentences:
                sentences[-1] += s
            else:
                sentences.append(s)
        if not sentences:
            sentences = [ja_text]

        instruct = self.get_instruct(emotion, "Japanese")

        # Select profile based on emotion
        if emotion == "horny" and self.config.voicebox_horny_profile_id:
            profile_id = self.config.voicebox_horny_profile_id
        else:
            profile_id = self.config.voicebox_profile_id or ""

        return ja_text, sentences, instruct, profile_id

    async def _voicebox_generate_one(
        self, client, sentence: str, profile_id: str, instruct: str,
        emotion: str = "neutral"
    ) -> Optional[Path]:
        """Generate a single sentence via Voicebox HTTP. Returns audio Path or None."""
        import uuid

        payload = {
            "text": sentence,
            "profile_id": profile_id,
            "language": "ja",
        }
        if instruct:
            payload["instruct"] = instruct
        model_size = getattr(self.config, "voicebox_model_size", None)
        if model_size:
            payload["model_size"] = model_size

        logger.info(f"Voicebox generating: {sentence[:40]}...")
        try:
            resp = await client.post(
                f"{self.config.voicebox_api_url}/generate",
                json=payload,
            )
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Voicebox segment failed: {e}")
            return None

        data = resp.json()
        if "audio_path" not in data:
            return None

        source = Path(data["audio_path"])
        if not source.is_absolute():
            from config import config as _cfg
            _vb = Path(_cfg.tts.voicebox_path) if _cfg.tts.voicebox_path else Path.home() / "voicebox"
            source = _vb / source
        if not source.exists():
            return None

        # Copy to output dir with unique name, prepend short silence
        import shutil
        import wave
        import struct
        out_name = f"{uuid.uuid4()}.wav"
        out_path = self.output_dir / out_name

        # Prepend ~80ms silence to prevent browser audio clipping on play start
        try:
            with wave.open(str(source), "rb") as src:
                params = src.getparams()
                raw = src.readframes(src.getnframes())
            pad_samples = int(params.framerate * 0.08)  # 80ms
            silence = struct.pack(f"<{pad_samples * params.nchannels}h",
                                  *([0] * pad_samples * params.nchannels))
            with wave.open(str(out_path), "wb") as out:
                out.setparams(params)
                out.writeframes(silence + raw)
        except Exception:
            shutil.copy2(str(source), str(out_path))

        # Apply audio post-processing based on emotion
        if getattr(self.config, "audio_fx_enabled", True):
            try:
                from audio_fx import process_wav
                process_wav(out_path, emotion)
            except Exception as e:
                logger.warning(f"Audio FX failed: {e}")

        return out_path

    async def synthesize_stream(
        self, text: str, language: str = "zh-TW", emotion: str = "neutral"
    ):
        """Async generator yielding SSE event dicts for streaming TTS.
        Uses parallel generation with ordered yield for minimal latency."""

        if self.provider == "nano_qwen3tts":
            # nano-qwen3tts: HTTP to WSL2 server, sentence by sentence
            synth_text, sentences, instruct, tts_lang = await self._prepare_tts_qwen3tts(
                text, language, emotion
            )
            if not sentences:
                return
            yield {"type": "ja_text", "data": synth_text}
            import httpx, uuid as _uuid, struct as _struct
            speaker = getattr(self.config, 'qwen3tts_speaker', 'Ono_Anna')
            import aiohttp as _aiohttp
            async with _aiohttp.ClientSession(timeout=_aiohttp.ClientTimeout(total=300)) as session:
                for i, sent in enumerate(sentences):
                    try:
                        async with session.post(f"{self._nano_url}/v1/audio/speech",
                                                json={"text": sent, "language": tts_lang, "speaker": speaker, "instruct": instruct}) as resp:
                            resp.raise_for_status()
                            pcm = await resp.read()
                        out_name = f"{_uuid.uuid4()}.wav"
                        out_path = self.output_dir / out_name
                        sr = 24000
                        with open(str(out_path), "wb") as f:
                            f.write(b"RIFF")
                            f.write(_struct.pack("<I", 36 + len(pcm)))
                            f.write(b"WAVEfmt ")
                            f.write(_struct.pack("<IHHIIHH", 16, 1, 1, sr, sr*2, 2, 16))
                            f.write(b"data")
                            f.write(_struct.pack("<I", len(pcm)))
                            f.write(pcm)
                        yield {"type": "audio", "index": i, "url": f"/audio/{out_name}", "total": len(sentences)}
                    except Exception as e:
                        logger.error(f"nano-qwen3tts stream segment {i} failed: {e}")
            return

        if self.provider == "qwen3tts":
            # Qwen3-TTS: use mode-aware preprocessing
            synth_text, sentences, instruct, tts_lang = await self._prepare_tts_qwen3tts(
                text, language, emotion
            )
            if not sentences:
                return
            yield {"type": "ja_text", "data": synth_text}
            for i, sent in enumerate(sentences):
                part = await self._qwen3tts_generate_one(
                    sent, emotion, tts_language=tts_lang, instruct=instruct,
                )
                if part:
                    yield {
                        "type": "audio",
                        "index": i,
                        "url": f"/audio/{part.name}",
                        "total": len(sentences),
                    }
            return

        # Voicebox / other providers
        ja_text, sentences, instruct, profile_id = await self._prepare_tts(
            text, language, emotion
        )
        if not sentences:
            return
        yield {"type": "ja_text", "data": ja_text}

        # Voicebox: parallel HTTP generation with ordered yield
        import httpx

        concurrency = getattr(self.config, "voicebox_concurrency", 2)
        semaphore = asyncio.Semaphore(concurrency)
        results = [None] * len(sentences)
        events = [asyncio.Event() for _ in sentences]

        async def gen_one(idx, sent):
            try:
                async with semaphore:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        results[idx] = await self._voicebox_generate_one(
                            client, sent, profile_id, instruct, emotion=emotion
                        )
            except Exception as e:
                logger.error(f"Sentence {idx} generation failed: {e}")
                results[idx] = None
            finally:
                events[idx].set()

        tasks = [asyncio.create_task(gen_one(i, s)) for i, s in enumerate(sentences)]

        for i in range(len(sentences)):
            await events[i].wait()
            if results[i]:
                yield {
                    "type": "audio",
                    "index": i,
                    "url": f"/audio/{results[i].name}",
                    "total": len(sentences),
                }

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _synthesize_voicebox(
        self, text: str, language: str = "zh-TW", emotion: str = "neutral"
    ) -> tuple[str, list[dict], str]:
        """Synthesize speech using Voicebox API (non-streaming path).
        Returns (audio_filename, visemes, ja_text)."""
        import uuid
        import httpx

        ja_text, sentences, instruct, profile_id = await self._prepare_tts(
            text, language, emotion
        )
        if not sentences:
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], ""

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = self.output_dir / output_filename

        try:
            concurrency = getattr(self.config, "voicebox_concurrency", 2)
            semaphore = asyncio.Semaphore(concurrency)
            results = [None] * len(sentences)
            events = [asyncio.Event() for _ in sentences]

            async def gen_one(idx, sent):
                try:
                    async with semaphore:
                        async with httpx.AsyncClient(timeout=120.0) as client:
                            results[idx] = await self._voicebox_generate_one(
                                client, sent, profile_id, instruct, emotion=emotion
                            )
                except Exception as e:
                    logger.error(f"Sentence {idx} generation failed: {e}")
                finally:
                    events[idx].set()

            tasks = [asyncio.create_task(gen_one(i, s)) for i, s in enumerate(sentences)]
            await asyncio.gather(*tasks, return_exceptions=True)

            audio_parts = [r for r in results if r is not None]

            if not audio_parts:
                raise RuntimeError("No audio generated")

            if len(audio_parts) == 1:
                import shutil
                shutil.copy2(str(audio_parts[0]), str(output_path))
            else:
                self._concat_wav(audio_parts, output_path)

            logger.info(f"Voicebox TTS synthesized: {output_filename} ({len(sentences)} parts)")
            visemes = self._generate_visemes_from_audio(str(output_path), ja_text)
            return output_filename, visemes, ja_text

        except Exception as e:
            logger.error(f"Voicebox synthesis failed: {e}")
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], ja_text

    def _get_speaker_language(self) -> str:
        """Return the language string for the current speaker."""
        speaker = getattr(self.config, "qwen3tts_speaker", "Ono_Anna")
        info = self.PRESET_SPEAKERS.get(speaker, {})
        return info.get("language", "Japanese")

    async def _qwen3tts_generate_one(
        self, sentence: str, emotion: str = "neutral",
        tts_language: str = "Japanese", instruct: str = "",
    ) -> Optional[Path]:
        """Generate a single sentence via Qwen3-TTS in-process. Returns audio Path or None."""
        import uuid
        import numpy as np
        import soundfile as sf

        try:
            loop = asyncio.get_event_loop()

            if self._qwen3tts_mode == "custom_voice":
                # CustomVoice: preset speaker + instruct for emotion
                speaker = getattr(self.config, "qwen3tts_speaker", "Ono_Anna")
                wavs, sr = await loop.run_in_executor(
                    None,
                    lambda: self._model.generate_custom_voice(
                        text=sentence,
                        language=tts_language,
                        speaker=speaker,
                        instruct=instruct or "",
                    ),
                )
            else:
                # VoiceClone: use pre-computed emotion prompt
                prompt = self._emotion_prompts.get(emotion)
                if not prompt:
                    prompt = self._emotion_prompts.get("neutral")
                if not prompt:
                    logger.error("No voice clone prompt available")
                    return None
                wavs, sr = await loop.run_in_executor(
                    None,
                    lambda: self._model.generate_voice_clone(
                        text=sentence,
                        language=tts_language,
                        voice_clone_prompt=prompt,
                    ),
                )

            # wavs is a list of tensors/arrays; take the first one
            wav = wavs[0] if isinstance(wavs, (list, tuple)) else wavs
            if hasattr(wav, "cpu"):
                wav = wav.cpu().numpy()
            wav = np.squeeze(wav)

            out_name = f"{uuid.uuid4()}.wav"
            out_path = self.output_dir / out_name

            # Prepend ~80ms silence to prevent browser audio clipping
            pad_samples = int(sr * 0.08)
            silence = np.zeros(pad_samples, dtype=wav.dtype)
            wav_padded = np.concatenate([silence, wav])

            sf.write(str(out_path), wav_padded, sr)

            # Apply audio post-processing based on emotion
            if getattr(self.config, "audio_fx_enabled", True):
                try:
                    from audio_fx import process_wav
                    process_wav(out_path, emotion)
                except Exception as e:
                    logger.warning(f"Audio FX failed: {e}")

            return out_path

        except Exception as e:
            logger.error(f"Qwen3-TTS generation failed: {e}")
            return None

    async def _prepare_tts_qwen3tts(
        self, text: str, language: str, emotion: str
    ) -> tuple[str, list[str], str, str]:
        """Preprocessing for Qwen3-TTS: decides whether to translate based on speaker language.
        Returns (synth_text, sentences, instruct, tts_language)."""
        speaker_lang = self._get_speaker_language() if self._qwen3tts_mode == "custom_voice" else "Japanese"

        if speaker_lang == "Chinese":
            # Chinese speaker: skip translation, use Chinese instruct
            instruct = self.get_instruct(emotion, "Chinese")
            # Still need to clean text
            import re as _re
            clean_text = self._strip_emoji(text)
            if not clean_text:
                return "", [], "", "Chinese"
            clean_text = _re.sub(r'```json\s*\{[\s\S]*?\}\s*```', '', clean_text)
            clean_text = _re.sub(r'```[\s\S]*?```', '', clean_text)
            clean_text = _re.sub(r'\{["\s]*tool[\s\S]*?\}', '', clean_text)
            clean_text = clean_text.strip()
            if not clean_text:
                return "", [], "", "Chinese"
            # Clean symbols
            for ch in "♡♪☆★→←↑↓《》【】「」『』（）()":
                clean_text = clean_text.replace(ch, "")
            clean_text = _re.sub(r'[*#_`~|<>{}\\\/\[\]]', '', clean_text)
            clean_text = _re.sub(r'\s+', ' ', clean_text).strip()
            logger.info(f"TTS text (zh): {clean_text[:80]}...")
            # Split on Chinese punctuation
            raw = _re.split(r'(?<=[。！？])\s*', clean_text)
            sentences = [s.strip() for s in raw if s.strip() and len(s.strip()) > 1]
            # Merge short fragments
            merged = []
            for s in sentences:
                if len(s) < 6 and merged:
                    merged[-1] += s
                else:
                    merged.append(s)
            return clean_text, merged or [clean_text], instruct, "Chinese"
        else:
            # Japanese / other: use existing translate pipeline
            ja_text, sentences, instruct, _ = await self._prepare_tts(text, language, emotion)
            return ja_text, sentences, instruct, speaker_lang

    async def _synthesize_qwen3tts(
        self, text: str, language: str = "zh-TW", emotion: str = "neutral"
    ) -> tuple[str, list[dict], str]:
        """Synthesize speech using Qwen3-TTS directly (non-streaming path)."""
        import uuid

        synth_text, sentences, instruct, tts_language = await self._prepare_tts_qwen3tts(
            text, language, emotion
        )
        if not sentences:
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], ""

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = self.output_dir / output_filename

        try:
            # Generate sentences sequentially (GPU model, parallelism managed by batch)
            audio_parts = []
            for sent in sentences:
                part = await self._qwen3tts_generate_one(
                    sent, emotion, tts_language=tts_language, instruct=instruct
                )
                if part:
                    audio_parts.append(part)

            if not audio_parts:
                raise RuntimeError("No audio generated")

            if len(audio_parts) == 1:
                import shutil
                shutil.copy2(str(audio_parts[0]), str(output_path))
            else:
                self._concat_wav(audio_parts, output_path)

            logger.info(f"Qwen3-TTS synthesized: {output_filename} ({len(sentences)} parts)")
            visemes = self._generate_visemes_from_audio(str(output_path), synth_text)
            return output_filename, visemes, synth_text

        except Exception as e:
            logger.error(f"Qwen3-TTS synthesis failed: {e}")
            result = await self._mock_synthesize(text, language)
            return result[0], result[1], synth_text

    async def _mock_synthesize(
        self, text: str, language: str = "zh-TW"
    ) -> tuple[str, list[dict]]:
        import uuid
        import struct

        output_filename = f"{uuid.uuid4()}.wav"
        output_path = self.output_dir / output_filename

        sample_rate = self.sample_rate
        duration = 0.5
        num_samples = int(sample_rate * duration)

        with open(output_path, "wb") as f:
            data_size = num_samples * 2  # 16-bit samples
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + data_size))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))
            f.write(struct.pack("<H", 1))
            f.write(struct.pack("<H", 1))
            f.write(struct.pack("<I", sample_rate))
            f.write(struct.pack("<I", sample_rate * 2))
            f.write(struct.pack("<H", 2))
            f.write(struct.pack("<H", 16))
            f.write(b"data")
            f.write(struct.pack("<I", data_size))
            f.write(b"\x00" * data_size)

        logger.warning(f"Using mock TTS output (silence generated): {output_filename}")
        return output_filename, []

    def _generate_visemes_from_audio(
        self, audio_path: str, text: str = ""
    ) -> list[dict]:
        """Generate viseme data from audio file and text using a phoneme map."""
        PHONEME_VISEME_MAP = {
            "a": "aa",
            "o": "oh",
            "u": "ou",
            "e": "ee",
            "i": "ih",
            "b": "oh",
            "p": "oh",
            "m": "oh",
            "f": "ih",
            "v": "ih",
            "s": "ee",
            "z": "ee",
            "sh": "ee",
            "t": "ih",
            "d": "ih",
            "n": "ih",
            "l": "ih",
            "k": "aa",
            "g": "aa",
            "r": "oh",
            "w": "ou",
            "y": "ee",
        }

        try:
            import wave
            import struct

            with wave.open(audio_path, "r") as wf:
                n_frames = wf.getnframes()
                framerate = wf.getframerate()
                raw = wf.readframes(n_frames)
                samples = struct.unpack(f"<{n_frames}h", raw)

            chunk_size = max(1, framerate // 20)  # ~50ms windows
            visemes = []
            mouth_shapes = ["aa", "oh", "ee", "ih", "ou"]

            # Map text to shape indices
            text_chars = [c.lower() for c in text if c.lower() in PHONEME_VISEME_MAP]

            for i in range(0, len(samples), chunk_size):
                chunk = samples[i : i + chunk_size]
                if not chunk:
                    break
                amplitude = sum(abs(s) for s in chunk) / len(chunk) / 32768.0
                time_sec = i / framerate

                if amplitude < 0.02:
                    continue

                weight = min(1.0, amplitude * 5)

                if text_chars:
                    char_idx = min(
                        int((i / len(samples)) * len(text_chars)), len(text_chars) - 1
                    )
                    mapped_shape = PHONEME_VISEME_MAP.get(text_chars[char_idx], "aa")
                else:
                    shape_idx = (i // chunk_size) % len(mouth_shapes)
                    mapped_shape = mouth_shapes[shape_idx]

                visemes.append(
                    {
                        "time": round(time_sec, 3),
                        "viseme": mapped_shape,
                        "weight": round(weight, 2),
                    }
                )

            return visemes
        except Exception as e:
            logger.warning(f"Viseme generation failed: {e}")
            return []

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
