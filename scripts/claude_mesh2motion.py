"""
Claude Computer Use - Mesh2Motion 自動化
自動上傳 3D 模型、套用動畫、下載結果
"""

import anthropic
import base64
import time
import os
import sys
from pathlib import Path

try:
    import pyautogui
    import mss
except ImportError:
    print("請安裝: pip install pyautogui mss")
    sys.exit(1)

# ============================
# 配置
# ============================
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not API_KEY:
    print("ERROR: 請設定 ANTHROPIC_API_KEY")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

DISPLAY_SIZE = (1280, 720)
MAX_STEPS = 50
MODEL = "claude-sonnet-4-20250514"


# ============================
# 截圖 + 操作
# ============================
def take_screenshot() -> str:
    """用 mss 截圖"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        import cv2
        import numpy as np

        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        _, buffer = cv2.encode(".png", img)
        return base64.b64encode(buffer).decode()


def take_screenshot_pil() -> str:
    """用 PIL 截圖 (不需要 cv2)"""
    from PIL import Image
    import io

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


def execute_action(action: dict):
    """執行 Claude 的動作"""
    action_type = action.get("action", "")

    if action_type == "click":
        coord = action.get("coordinate", [0, 0])
        x, y = coord[0], coord[1]
        pyautogui.click(x, y)
        print(f"  -> Click ({x}, {y})")

    elif action_type == "type":
        text = action.get("text", "")
        pyautogui.typewrite(text, interval=0.05)
        print(f"  -> Type: {text[:30]}...")

    elif action_type == "key":
        key = action.get("text", "")
        if "+" in key:
            keys = key.split("+")
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key.lower())
        print(f"  -> Key: {key}")

    elif action_type == "scroll":
        coord = action.get("coordinate", [0, 0])
        pyautogui.scroll(coord[1])
        print(f"  -> Scroll: {coord[1]}")

    elif action_type == "wait":
        time.sleep(2)
        print("  -> Wait 2s")

    elif action_type == "drag":
        coord = action.get("coordinate", [0, 0])
        pyautogui.moveTo(coord[0], coord[1])
        pyautogui.drag(0, -100, duration=0.5)
        print(f"  -> Drag to ({coord[0]}, {coord[1]})")

    else:
        print(f"  -> Unknown action: {action_type}")


def computer_use_loop(task: str, max_steps: int = MAX_STEPS) -> str:
    """主循環"""
    messages = []
    screenshot = take_screenshot_pil()

    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": task},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot,
                    },
                },
            ],
        }
    )

    for step in range(max_steps):
        print(f"\n[Step {step + 1}/{max_steps}]")

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                tools=[
                    {
                        "type": "computer_20241022",
                        "name": "computer",
                        "display_width_px": DISPLAY_SIZE[0],
                        "display_height_px": DISPLAY_SIZE[1],
                        "display_number": 1,
                    }
                ],
                messages=messages,
            )
        except Exception as e:
            print(f"API Error: {e}")
            return f"Error at step {step + 1}: {e}"

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return (
                "\n".join(text_blocks)
                if text_blocks
                else "Task completed (no text response)"
            )

        messages.append({"role": "assistant", "content": response.content})

        for tool_block in tool_use_blocks:
            action = tool_block.input
            execute_action(action)

        time.sleep(1.5)

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_blocks[0].id,
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": take_screenshot_pil(),
                                },
                            }
                        ],
                    }
                ],
            }
        )

    return "Max steps reached"


# ============================
# 主程式
# ============================
def main():
    project_dir = Path(__file__).parent.parent
    input_glb = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(project_dir / "output/models/0/mesh.glb")
    )
    output_dir = project_dir / "mobile_app/assets/animations"

    output_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(input_glb):
        print(f"ERROR: 找不到模型檔案: {input_glb}")
        print("請先執行 TripoSR 生成 3D 模型")
        sys.exit(1)

    print("==============================================")
    print("  AI 老婆 Mesh2Motion 動畫自動化")
    print("==============================================")
    print(f"  輸入模型: {input_glb}")
    print(f"  輸出目錄: {output_dir}")
    print(f"  解析度: {DISPLAY_SIZE[0]}x{DISPLAY_SIZE[1]}")
    print("==============================================")
    print()
    print("請確保:")
    print("  1. Firefox 已開啟並顯示在螢幕上")
    print("  2. 瀏覽器視窗大小約為 1280x720")
    print("  3. 5 秒後開始自動化...")
    print()

    time.sleep(5)

    task = f"""
你是一個 3D 動畫自動化助手。請完成以下任務：

1. 確保 Firefox 瀏覽器是當前活動視窗
2. 在網址列輸入: https://mesh2motion.org/
3. 按 Enter 前往網站
4. 找到並點擊 "Launch Application" 或 "Start" 按鈕
5. 等待應用載入完成
6. 找到上傳/Import 按鈕，上傳此 3D 模型檔案: {input_glb}
7. 選擇 Humanoid (人形) 骨骼類型
8. 等待模型載入完成
9. 依序套用以下動畫並匯出 GLB 檔案:
   - Idle (站立待機)
   - Walk (走路)
   - Wave (揮手打招呼)
   - Dance (跳舞)
   - Laugh (笑)
   - Nod (點頭)
   - Shake Head (搖頭)
10. 每個動畫匯出到下載資料夾，命名格式: animation_name.glb
11. 完成所有動畫後，在終端機輸出 "DONE"

請一步一步完成，每個動作後等待畫面更新。如果看到對話框，點擊確認。
如果上傳失敗，重試一次。
"""

    print("開始執行任務...")
    result = computer_use_loop(task)

    print(f"\n==============================================")
    print(f"  執行結果:")
    print(f"  {result}")
    print(f"==============================================")


if __name__ == "__main__":
    main()
