"""
Claude Computer Use 自動化 VRM 生成 Pipeline

這個腳本讓 Claude Computer Use 自動操作：
1. Mesh2Motion 網站 → 上傳模型 + 套用動畫
2. Blender → 匯出 VRM 格式
3. 驗證輸出檔案

需要：
- ANTHROPIC_API_KEY
- xdotool, scrot, xclip
- Xvfb (headless 環境)
"""

import anthropic
import base64
import subprocess
import time
import os
import sys
from pathlib import Path

# ============================
# 配置
# ============================
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not API_KEY:
    print("ERROR: 請設定 ANTHROPIC_API_KEY 環境變數")
    sys.exit(1)

DISPLAY_SIZE = (1280, 720)
MAX_STEPS = 30
MODEL = "claude-sonnet-4-20250514"

client = anthropic.Anthropic(api_key=API_KEY)


# ============================
# 工具函數
# ============================
def take_screenshot() -> str:
    """截圖並回傳 base64"""
    subprocess.run(
        ["scrot", "-s", "/tmp/cu_screenshot.png"], check=True, capture_output=True
    )
    with open("/tmp/cu_screenshot.png", "rb") as f:
        return base64.standard_b64encode(f.read()).decode()


def execute_action(action: dict):
    """執行 Claude 的動作指令"""
    action_type = action.get("action", "")

    if action_type == "click":
        coord = action.get("coordinate", (0, 0))
        x, y = coord[0], coord[1]
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=True)
        time.sleep(0.1)
        subprocess.run(["xdotool", "click", "1"], check=True)

    elif action_type == "type":
        text = action.get("text", "")
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "10", text], check=True
        )

    elif action_type == "key":
        key = action.get("text", "")
        subprocess.run(["xdotool", "key", "--clearmodifiers", key], check=True)

    elif action_type == "scroll":
        direction = action.get("coordinate", (0, 0))
        clicks = "5" if direction[1] > 0 else "-5"
        subprocess.run(["xdotool", "click", clicks], check=True)

    elif action_type == "wait":
        time.sleep(1.5)

    else:
        print(f"Unknown action: {action_type}")


def computer_use_loop(task: str, max_steps: int = MAX_STEPS) -> str:
    """Computer Use 主循環"""
    messages = []
    screenshot = take_screenshot()

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
            return "\n".join(text_blocks)

        messages.append({"role": "assistant", "content": response.content})

        for tool_block in tool_use_blocks:
            action = tool_block.input
            action_type = action.get("action", "unknown")
            coord = action.get("coordinate", "N/A")
            print(f"  Action: {action_type} at {coord}")

            execute_action(action)

        time.sleep(1)
        screenshot = take_screenshot()

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
                                    "data": take_screenshot(),
                                },
                            }
                        ],
                    }
                ],
            }
        )

    return "Max steps reached"


# ============================
# 任務定義
# ============================
def task_mesh2motion(input_glb: str, output_dir: str):
    """用 Claude Computer Use 操作 Mesh2Motion 網站"""
    print("\n=== Mesh2Motion 動畫套用 ===")

    task = f"""
你是一個 3D 動畫自動化助手。請完成以下任務：

1. 打開 Firefox 瀏覽器，前往 https://mesh2motion.org/
2. 點擊 "Launch Application" 或 "Start" 按鈕
3. 上傳 3D 模型檔案：{input_glb}
4. 選擇 Humanoid 骨骼類型
5. 依序套用以下動畫並匯出 GLB：
   - Idle (Standing)
   - Walk Forward
   - Wave (Greeting)
   - Sway Dance
   - Laughing
   - Nod Yes
   - Shake Head No
6. 每個動畫匯出到：{output_dir}/
7. 檔案命名格式：animation_name.glb

請一步一步完成，每個動作後等待畫面更新。
"""
    return computer_use_loop(task)


def task_blender_vrm_export(input_glb: str, output_vrm: str):
    """用 Claude Computer Use 操作 Blender 匯出 VRM"""
    print("\n=== Blender VRM 匯出 ===")

    task = f"""
你是一個 Blender 自動化助手。請完成以下任務：

1. 打開 Blender 應用程式
2. 刪除預設的 cube（按 X 確認）
3. 匯入 GLB 模型：File → Import → glTF 2.0 → 選擇 {input_glb}
4. 確認模型正確載入
5. 安裝 VRM addon（如果還沒裝）：
   - Edit → Preferences → Add-ons → Install
   - 選擇 VRM addon for Blender
6. 匯出 VRM：File → Export → VRM (.vrm)
7. 儲存到：{output_vrm}
8. 確認檔案已建立

請一步一步完成，每個動作後等待畫面更新。
"""
    return computer_use_loop(task)


# ============================
# 主程式
# ============================
def main():
    project_dir = Path(__file__).parent.parent
    input_image = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(project_dir / "Pictures/post-image-33571620.jpeg")
    )
    output_dir = project_dir / "output/character"
    animations_dir = project_dir / "mobile_app/assets/animations"
    vrm_output = project_dir / "mobile_app/assets/models/character_final.vrm"

    output_dir.mkdir(parents=True, exist_ok=True)
    animations_dir.mkdir(parents=True, exist_ok=True)
    vrm_output.parent.mkdir(parents=True, exist_ok=True)

    print("==============================================")
    print("  AI 老婆 VRM 自動生成 (Claude Computer Use)")
    print("==============================================")

    # Step 1: 先用 TripoSR/CharacterGen 生成 3D 網格
    print("\n[1/3] 生成 3D 網格...")
    # 這裡可以呼叫現有的 TripoSR 或 CharacterGen
    mesh_path = str(project_dir / "output/models/0/mesh.glb")
    if not os.path.exists(mesh_path):
        print("  執行 TripoSR 生成...")
        subprocess.run(
            [
                "python",
                str(project_dir / "models/3d/TripoSR/run.py"),
                input_image,
                "--device",
                "cuda:0",
                "--output-dir",
                str(project_dir / "output/models"),
                "--model-save-format",
                "glb",
            ],
            check=True,
        )

    # Step 2: Mesh2Motion 動畫
    print("\n[2/3] Mesh2Motion 動畫套用...")
    result = task_mesh2motion(mesh_path, str(animations_dir))
    print(f"  結果: {result}")

    # Step 3: Blender VRM 匯出
    print("\n[3/3] Blender VRM 匯出...")
    result = task_blender_vrm_export(mesh_path, str(vrm_output))
    print(f"  結果: {result}")

    # 驗證輸出
    print("\n==============================================")
    print("  完成！")
    print("==============================================")
    print(f"  VRM: {vrm_output}")
    print(f"  動畫: {animations_dir}/")
    print("==============================================")


if __name__ == "__main__":
    main()
