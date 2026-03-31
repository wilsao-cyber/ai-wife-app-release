"""
MCP Desktop Control Tool
讓 AI 老婆透過 ubuntu-desktop-control-mcp 控制桌面
"""

import asyncio
import logging
from typing import Optional
from services.mcp_desktop_control import MCPDesktopControl
from services.desktop_automation import DesktopAutomation

logger = logging.getLogger(__name__)


class MCPDesktopTool:
    """MCP 桌面控制工具"""

    def __init__(self):
        self.mcp = MCPDesktopControl()
        self.automation = DesktopAutomation()
        self._initialized = False

    async def initialize(self):
        """初始化 MCP 連線"""
        try:
            await self.mcp.initialize()
            screen_info = await self.mcp.get_screen_info()
            self._initialized = True
            logger.info(f"MCP Desktop Control initialized: {screen_info}")
            return {"success": True, "screen_info": screen_info}
        except Exception as e:
            logger.error(f"MCP init failed: {e}")
            return {"error": str(e)}

    async def screenshot(self, detect_elements: bool = True) -> dict:
        """截圖"""
        try:
            result = await self.mcp.take_screenshot(detect_elements)
            return {"success": True, "screenshot": result}
        except Exception as e:
            return {"error": str(e)}

    async def click(
        self, element_id: int = None, x: float = None, y: float = None
    ) -> dict:
        """點擊"""
        try:
            result = await self.mcp.click_screen(
                element_id=element_id, x_percent=x, y_percent=y
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def type(self, text: str) -> dict:
        """打字"""
        try:
            result = await self.mcp.type_text(text)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def key(self, key: str) -> dict:
        """按鍵"""
        try:
            result = await self.mcp.press_key(key)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def hotkey(self, keys: list[str]) -> dict:
        """組合鍵"""
        try:
            result = await self.mcp.press_hotkey(keys)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def open_browser(self, url: str) -> dict:
        """打開瀏覽器"""
        try:
            result = await self.automation.open_browser(url)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def vrm_pipeline(self, model_path: str) -> dict:
        """執行 VRM 生成 pipeline"""
        try:
            result = await self.automation.full_vrm_pipeline(model_path, "./output")
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def workflow(self, actions: list[dict]) -> dict:
        """批量操作"""
        try:
            result = await self.mcp.execute_workflow(actions)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def close(self):
        """關閉連線"""
        await self.mcp.stop()
        await self.automation.close()
