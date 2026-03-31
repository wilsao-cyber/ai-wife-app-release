"""
AI 老婆 3D 美少女自動生成 Pipeline
使用 ubuntu-desktop-control-mcp 自動化操作桌面
從單張圖片 → 高品質 3D 動漫美少女
"""

import asyncio
import json
import time
import os
import sys
import base64
from pathlib import Path

try:
    import pyautogui
    import mss
    from PIL import Image
except ImportError:
    print("請安裝: pip install pyautogui mss pillow")
    sys.exit(1)

# ============================
# 配置
# ============================
PROJECT_DIR = Path(__file__).parent.parent
INPUT_IMAGE = (
    sys.argv[1]
    if len(sys.argv) > 1
    else str(PROJECT_DIR.parent / "Pictures/post-image-33571620.jpeg")
)
OUTPUT_DIR = PROJECT_DIR / "output/character"
ANIMATIONS_DIR = PROJECT_DIR / "mobile_app/assets/animations"
MODELS_DIR = PROJECT_DIR / "mobile_app/assets/models"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

pyautogui.FAILSAFE = True  # 移到左上角可中止
pyautogui.PAUSE = 0.5


# ============================
# 工具函數
# ============================
def screenshot(save_path: str = "/tmp/mcp_screenshot.png") -> dict:
    """截圖"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.save(save_path)
        return {"width": shot.width, "height": shot.height, "path": save_path}


def wait(seconds: float = 1):
    """等待"""
    time.sleep(seconds)


def click_at(x: int, y: int, clicks: int = 1):
    """點擊座標"""
    pyautogui.click(x, y, clicks=clicks)
    print(f"  Click ({x}, {y})")


def type_text(text: str, interval: float = 0.05):
    """輸入文字"""
    pyautogui.typewrite(text, interval=interval)
    print(f"  Type: {text[:50]}...")


def press_key(key: str):
    """按鍵"""
    pyautogui.press(key)
    print(f"  Press: {key}")


def hotkey(*keys):
    """組合鍵"""
    pyautogui.hotkey(*keys)
    print(f"  Hotkey: {'+'.join(keys)}")


def find_element_on_screen(template_path: str, confidence: float = 0.8):
    """在畫面上尋找元素"""
    try:
        import cv2
        import numpy as np

        screen = pyautogui.screenshot()
        screen_cv = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
        template = cv2.imread(template_path)
        if template is None:
            return None
        result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= confidence:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return {"x": center_x, "y": center_y, "confidence": max_val}
    except Exception as e:
        print(f"  Element detection failed: {e}")
    return None


def open_app(app_name: str):
    """打開應用程式"""
    hotkey("super")
    wait(0.5)
    type_text(app_name)
    wait(1)
    press_key("enter")
    print(f"  Opening: {app_name}")


def open_browser(url: str):
    """打開瀏覽器前往網址"""
    open_app("firefox")
    wait(3)
    hotkey("ctrl", "l")
    wait(0.5)
    type_text(url)
    press_key("enter")
    wait(3)
    print(f"  Browser opened: {url}")


def upload_file(file_path: str):
    """上傳檔案（使用檔案選擇對話框）"""
    hotkey("ctrl", "o")
    wait(1)
    type_text(file_path)
    wait(0.5)
    press_key("enter")
    wait(2)
    print(f"  File uploaded: {file_path}")


# ============================
# 工作流程
# ============================
def step1_generate_3d_mesh():
    """Step 1: 用 TripoSR 生成 3D 網格"""
    print("\n" + "=" * 50)
    print("Step 1: TripoSR 3D 網格生成")
    print("=" * 50)

    mesh_path = PROJECT_DIR / "output/models/0/mesh.glb"
    if mesh_path.exists():
        print(f"  已存在: {mesh_path}")
        return str(mesh_path)

    print("  執行 TripoSR...")
    import subprocess

    result = subprocess.run(
        [
            "python3.12",
            str(PROJECT_DIR / "models/3d/TripoSR/run.py"),
            INPUT_IMAGE,
            "--device",
            "cuda:0",
            "--output-dir",
            str(PROJECT_DIR / "output/models"),
            "--model-save-format",
            "glb",
        ],
        capture_output=True,
        text=True,
    )

    if mesh_path.exists():
        print(f"  OK: {mesh_path}")
        return str(mesh_path)
    else:
        print(f"  ERROR: TripoSR 生成失敗")
        print(result.stderr[-500:] if result.stderr else "Unknown error")
        return None


def step2_mesh2motion_animation():
    """Step 2: 用 Mesh2Motion 網站套用動畫"""
    print("\n" + "=" * 50)
    print("Step 2: Mesh2Motion 動畫套用")
    print("=" * 50)

    mesh_path = step1_generate_3d_mesh()
    if not mesh_path:
        print("  SKIP: 沒有 3D 模型")
        return False

    print("  打開 Mesh2Motion 網站...")
    open_browser("https://mesh2motion.org/")
    wait(5)

    # 截圖確認頁面載入
    info = screenshot("/tmp/mesh2motion_loaded.png")
    print(f"  畫面截圖: {info}")

    print("  等待用戶手動操作或繼續自動化...")
    print("  提示: Mesh2Motion 需要手動上傳模型和選擇動畫")
    print("  自動化需要更精確的 UI 元素偵測")

    return True


def step3_download_and_convert():
    """Step 3: 下載結果並轉換"""
    print("\n" + "=" * 50)
    print("Step 3: 下載和轉換")
    print("=" * 50)

    print("  檢查下載目錄...")
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        files = list(downloads.glob("*.glb")) + list(downloads.glob("*.fbx"))
        if files:
            print(f"  找到 {len(files)} 個檔案:")
            for f in files:
                print(f"    - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
                # 複製到專案
                if "animation" in f.name.lower() or "anim" in f.name.lower():
                    dest = ANIMATIONS_DIR / f.name
                    import shutil

                    shutil.copy2(f, dest)
                    print(f"    → 複製到 {dest}")
                else:
                    dest = MODELS_DIR / f.name
                    import shutil

                    shutil.copy2(f, dest)
                    print(f"    → 複製到 {dest}")
        else:
            print("  沒有找到下載的 3D 檔案")
    else:
        print("  Downloads 目錄不存在")


def step4_prepare_for_flutter():
    """Step 4: 準備 Flutter 資源"""
    print("\n" + "=" * 50)
    print("Step 4: 準備 Flutter 資源")
    print("=" * 50)

    # 確保模型在 assets 中
    src = PROJECT_DIR / "output/models/0/mesh.glb"
    dest = MODELS_DIR / "character.glb"
    if src.exists():
        import shutil

        shutil.copy2(src, dest)
        print(f"  模型已複製: {dest}")
        print(f"  大小: {dest.stat().st_size / 1024:.1f} KB")

    # 列出所有資源
    print("\n  可用資源:")
    for d in [MODELS_DIR, ANIMATIONS_DIR]:
        if d.exists():
            files = list(d.iterdir())
            print(f"  {d.name}/: {len(files)} 個檔案")
            for f in files:
                print(f"    - {f.name} ({f.stat().st_size / 1024:.1f} KB)")


# ============================
# 主程式
# ============================
def main():
    print("=" * 60)
    print("  AI 老婆 3D 美少女自動生成 Pipeline")
    print("  使用 ubuntu-desktop-control-mcp")
    print("=" * 60)
    print(f"  輸入圖片: {INPUT_IMAGE}")
    print(f"  輸出目錄: {OUTPUT_DIR}")
    print(f"  螢幕解析度: {pyautogui.size()}")
    print("=" * 60)

    # Step 1: TripoSR 生成
    step1_generate_3d_mesh()

    # Step 2: Mesh2Motion 動畫
    step2_mesh2motion_animation()

    # Step 3: 下載結果
    step3_download_and_convert()

    # Step 4: 準備 Flutter
    step4_prepare_for_flutter()

    print("\n" + "=" * 60)
    print("  Pipeline 完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 安裝 Flutter: https://flutter.dev")
    print("  2. cd mobile_app && flutter pub get && flutter run")
    print("  3. AI 老婆就可以在手機上顯示了！")
    print()


if __name__ == "__main__":
    main()
