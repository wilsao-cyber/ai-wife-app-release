"""
MCP 自動化桌面操作 - Mesh2Motion 動畫套用
使用 ubuntu-desktop-control-mcp 的 pyautogui + mss
"""

import asyncio
import time
import os
import sys
from pathlib import Path

try:
    import pyautogui
    import mss
    from PIL import Image
except ImportError:
    print("請安裝: pip install pyautogui mss pillow")
    sys.exit(1)

# 配置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

PROJECT_DIR = Path(__file__).parent.parent
MESH_PATH = PROJECT_DIR / "output/models/0/mesh.glb"


def screenshot(path="/tmp/mcp_step.png"):
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.save(path)
        return shot.width, shot.height


def wait(s=1):
    time.sleep(s)


def click(x, y):
    pyautogui.click(x, y)
    print(f"  click({x}, {y})")


def type_text(text, interval=0.05):
    pyautogui.typewrite(text, interval=interval)
    print(f"  type: {text[:60]}")


def press(key):
    pyautogui.press(key)
    print(f"  press: {key}")


def hotkey(*keys):
    pyautogui.hotkey(*keys)
    print(f"  hotkey: {'+'.join(keys)}")


def open_app(name):
    """打開應用程式"""
    # 先確保在桌面
    hotkey("super")
    wait(0.5)
    type_text(name, interval=0.1)
    wait(1)
    press("enter")
    print(f"  opening: {name}")


def open_browser(url):
    """打開 Firefox 並前往網址"""
    open_app("firefox")
    wait(3)
    hotkey("ctrl", "l")
    wait(0.5)
    type_text(url, interval=0.05)
    press("enter")
    wait(3)
    print(f"  browser: {url}")


def upload_file_via_dialog(file_path):
    """透過檔案選擇對話框上傳"""
    hotkey("ctrl", "o")
    wait(1)
    type_text(file_path, interval=0.05)
    wait(0.5)
    press("enter")
    wait(2)
    print(f"  uploaded: {file_path}")


def main():
    print("=" * 50)
    print("  MCP 自動化: Mesh2Motion 動畫套用")
    print("=" * 50)

    w, h = screenshot("/tmp/mcp_start.png")
    print(f"\n螢幕解析度: {w}x{h}")

    # Step 1: 打開 Mesh2Motion
    print("\n[1/4] 打開 Mesh2Motion 網站...")
    open_browser("https://mesh2motion.org/")
    screenshot("/tmp/mcp_mesh2motion.png")
    print("  截圖已儲存: /tmp/mcp_mesh2motion.png")

    # Step 2: 等待用戶確認頁面載入
    print("\n[2/4] 請確認 Mesh2Motion 頁面已載入")
    print("  如果頁面正確，按 Enter 繼續...")
    try:
        input("  按 Enter 繼續 (或 Ctrl+C 中止): ")
    except KeyboardInterrupt:
        print("\n中止")
        return

    # Step 3: 上傳模型
    print(f"\n[3/4] 上傳 3D 模型: {MESH_PATH}")
    if MESH_PATH.exists():
        print(f"  模型存在: {MESH_PATH.stat().st_size / 1024:.1f} KB")
        # 這裡需要用戶手動點擊上傳按鈕
        print("  請手動點擊網站的上傳按鈕")
        print("  然後按 Enter 讓腳本繼續...")
        try:
            input("  上傳完成後按 Enter: ")
        except KeyboardInterrupt:
            print("\n中止")
            return
    else:
        print(f"  模型不存在: {MESH_PATH}")
        return

    screenshot("/tmp/mcp_model_uploaded.png")
    print("  截圖已儲存: /tmp/mcp_model_uploaded.png")

    # Step 4: 套用動畫
    print("\n[4/4] 套用動畫")
    animations = ["Idle", "Walk", "Wave", "Dance", "Laugh", "Nod", "Shake"]
    for anim in animations:
        print(f"  請選擇動畫: {anim}")
        print("  套用後按 Enter 繼續下一個...")
        try:
            input(f"  {anim} 完成後按 Enter: ")
        except KeyboardInterrupt:
            print("\n中止")
            return
        screenshot(f"/tmp/mcp_anim_{anim.lower()}.png")
        print(f"  截圖已儲存: /tmp/mcp_anim_{anim.lower()}.png")

    print("\n" + "=" * 50)
    print("  自動化流程完成！")
    print("=" * 50)
    print("\n所有截圖儲存在 /tmp/mcp_*.png")
    print("請手動下載動畫檔案到:")
    print(f"  {PROJECT_DIR / 'mobile_app/assets/animations/'}")


if __name__ == "__main__":
    main()
