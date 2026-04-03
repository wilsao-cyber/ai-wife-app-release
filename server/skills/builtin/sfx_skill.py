import logging
from skills.base_skill import BaseSkill
from sfx_catalog import sfx_catalog

logger = logging.getLogger(__name__)


class SfxSkill(BaseSkill):
    """Skill for playing sound effects alongside voice. LLM selects SFX based on scene context."""

    @property
    def tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "sfx_play",
                    "description": (
                        "効果音を再生する (Play sound effects alongside voice). "
                        "Use this to enhance immersion during intimate scenes, daily life, or ambient moments. "
                        "Available categories: "
                        "環境音 (rain, nature, wind), "
                        "動作系 (actions, doors, footsteps), "
                        "衣服・布・ベッド (clothing rustling, bedsheet sounds), "
                        "生活音 (daily life, cooking, typing), "
                        "お風呂系 (bath, shower, water), "
                        "耳かき系 (ear cleaning ASMR), "
                        "エッチな生活音 (intimate daily sounds), "
                        "ローション (lotion sounds), "
                        "ローション手コキ (lotion handjob sounds), "
                        "ピストン音 (piston/thrusting sounds), "
                        "射精音 (ejaculation sounds). "
                        "Describe the mood or specific sound in Japanese."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "What sound to play (e.g., '雨の音', 'ベッドのきしむ音', 'ゆっくりした手コキ')",
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional: specific category name",
                            },
                            "loop": {
                                "type": "boolean",
                                "description": "Whether to loop (for ambient/continuous sounds). Default false.",
                            },
                            "volume": {
                                "type": "number",
                                "description": "Volume 0.0-1.0. Default 0.3 for background, 0.6 for prominent.",
                            },
                        },
                        "required": ["description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "sfx_stop",
                    "description": "効果音を停止する (Stop all currently playing sound effects).",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    async def execute(self, tool_name: str, **kwargs) -> dict:
        if tool_name == "sfx_play":
            query = kwargs.get("description", "")
            category = kwargs.get("category", "")
            loop = kwargs.get("loop", False)
            volume = kwargs.get("volume", 0.3)

            results = sfx_catalog.search(query=query, category=category, limit=3)
            if not results:
                return {"content": "No matching sound effects found."}

            urls = [sfx_catalog.get_url(r) for r in results]
            desc = results[0].description
            return {
                "content": f"🔊 Playing: {desc}",
                "sfx": {
                    "urls": urls,
                    "loop": loop,
                    "volume": volume,
                },
            }

        elif tool_name == "sfx_stop":
            return {
                "content": "🔇 Sound effects stopped.",
                "sfx": {"stop": True},
            }

        return {"error": f"Unknown sfx tool: {tool_name}"}
