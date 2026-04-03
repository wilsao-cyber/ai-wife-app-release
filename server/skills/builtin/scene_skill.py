import json
import logging
from skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)


class SceneSkill(BaseSkill):
    """Skill for creating immersive audio scenes with TTS + SFX mixed together."""

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "scene_play",
                    "description": (
                        "創建沉浸式音頻場景，將語音和效果音混合成一個音檔播放。"
                        "適合親密場景、故事敘述、ASMR 等需要音效搭配的情境。\n"
                        "script 是一個 JSON 陣列，每個元素是一個步驟：\n"
                        '- {"type":"speech","text":"要說的台詞"} — 生成語音\n'
                        '- {"type":"sfx","query":"效果音描述","volume":0.3} — 開始播放效果音（持續到 sfx_stop）\n'
                        '- {"type":"pause","duration":5} — 暫停 N 秒（效果音繼續播放）\n'
                        '- {"type":"sfx_stop"} — 停止效果音\n'
                        "效果音類別：環境音、衣服・布・ベッド、ローション手コキ、ピストン音、射精音、お風呂系、生活音\n"
                        "範例：親密場景可以先 speech 說話 → sfx 開始背景音 → pause 讓音效持續 → speech 再說話 → sfx 切換更激烈的音效"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "script": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string", "enum": ["speech", "sfx", "pause", "sfx_stop"]},
                                        "text": {"type": "string"},
                                        "query": {"type": "string"},
                                        "volume": {"type": "number"},
                                        "duration": {"type": "number"},
                                        "fade_in": {"type": "number"},
                                    },
                                },
                                "description": "場景腳本步驟列表",
                            },
                        },
                        "required": ["script"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, **kwargs) -> dict:
        if tool_name != "scene_play":
            return {"error": f"Unknown tool: {tool_name}"}

        script = kwargs.get("script", [])
        if not script:
            return {"error": "Empty script"}

        try:
            from scene_mixer import mix_scene
            from sfx_catalog import sfx_catalog
            # Get tts_engine from the global scope (set during startup)
            import main as main_module
            tts_engine = main_module.tts_engine

            path = await mix_scene(
                script=script,
                tts_engine=tts_engine,
                sfx_catalog=sfx_catalog,
                language="zh-TW",
                emotion=kwargs.get("emotion", "horny"),
            )
            if not path:
                return {"error": "Scene mixing failed"}

            return {
                "content": "🎬 場景音頻已生成",
                "media": [{"type": "audio", "url": f"/audio/{path.name}"}],
                "scene_audio": f"/audio/{path.name}",
            }
        except Exception as e:
            logger.error(f"Scene mixing failed: {e}", exc_info=True)
            return {"error": str(e)}
