# AI Wife App 🌸

你的 AI 老婆 — 一個能自我進化、擁有個性和聲音的 AI 伴侶。
配備 3D 動漫角色、日語語音合成、沉浸式音效場景、自我學習系統，以及日常生活助手功能。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.2.0-green.svg)

---

## 功能亮點

### 🧠 自我進化系統 (v0.2.0)
- **Markdown 技能系統** — AI 自己創建行為技能（SKILL.md），隨互動逐步成長
- **程式碼執行** — AI 能撰寫並執行 Python 腳本（AST 安全檢查 + 沙盒）
- **人格自我更新** — 每日反思對話內容，自動微調性格和記憶
- **使用者畫像** — 主動記錄你的偏好、習慣，越用越了解你

### 🎙️ 語音系統
- **日語語音合成** — 基於 Qwen3-TTS 的聲音克隆，支援 7 種情感（開心、悲傷、撒嬌、親密等）
- **SenseVoice 語音辨識** — 阿里開源 STT，中文精度遠超 Whisper，附帶情緒偵測
- **多角色切換** — 內建多組語音角色，可在設定中一鍵切換或訓練自己的聲音
- **情感音效處理** — 根據情感自動調整語音效果（混響、溫暖度、壓縮等）
- **串流/完整播放** — 串流模式邊生成邊播放，完整模式等全部生成後一次播放

### 🔊 音效與音樂系統
- **SFX 語義搜尋** — 支援自帶音效庫，AI 根據場景自動選擇音效
- **BGM 系統** — 場景連動背景音樂，支援自訂上傳 BGM
- **環境音** — 每個場景可配獨立環境音循環
- **情緒 BGM 切換** — AI 回覆悲傷/開心/浪漫時自動切換對應曲目
- **場景混音** — AI 自動編排語音和音效的時間軸

### 🌸 3D 角色
- **全螢幕 VRM 角色** — 卡通渲染風格，聊天視窗覆蓋在角色上方
- **滑鼠頭部追蹤** — 角色的頭和眼睛跟隨你的游標
- **點擊互動** — 點擊角色不同部位觸發不同反應 + 愛心/星星粒子
- **12 種動畫** — Idle、揮手、思考、開心、悲傷、生氣、驚訝、害羞、大笑、點頭、飛吻
- **表情漸變** — 平滑過渡而非突然切換
- **VRM 模型管理** — 上傳/切換/刪除角色模型
- **PMX 轉 VRM** — Blender 自動轉換（骨骼映射 + 表情設定）
- **4 種場景** — 居家、櫻花、奇幻、夜景，各有獨立光照設定

### 💬 智能對話
- **多家 AI 供應商** — 支援 DashScope、OpenRouter、OpenAI、Ollama，自動切換
- **無審查模式** — 一鍵切換到無內容審查的模型
- **雙模式** — 聊天模式（快速回覆）+ 協助模式（可使用工具執行任務）

### 📧 生活助手
- **郵件** — 讀取、搜尋、發送 Gmail
- **行事曆** — 查看、新增、修改 Google Calendar 事件
- **網路搜尋** — SearXNG + Brave Search，支援圖片和影片搜尋
- **檔案管理** — 讀取、寫入、瀏覽電腦中的檔案
- **程式碼執行** — AI 撰寫並運行 Python 腳本解決問題

---

## 系統需求

| 項目 | 最低需求 | 建議配置 |
|------|---------|---------|
| **作業系統** | Ubuntu 22.04+ / Linux | Ubuntu 24.04 |
| **GPU** | NVIDIA 8GB VRAM | NVIDIA RTX 3090 (24GB) |
| **CPU** | 4 核心 | 8 核心以上 |
| **記憶體** | 16GB | 32GB |
| **硬碟** | 20GB 可用空間 | 50GB（含 AI 模型快取） |
| **Python** | 3.10+ | 3.12 |
| **Docker** | 已安裝 | 用於 SearXNG 搜尋引擎 |
| **網路** | 穩定連線 | 用於雲端 AI 模型 API |

### GPU VRAM 使用量參考

| 元件 | VRAM 使用 |
|------|----------|
| Qwen3-TTS 1.7B | ~6-8 GB |
| Qwen3-TTS 0.6B | ~3-4 GB |
| FlashAttention2 | 額外 ~0.5 GB |

> **注意**：如果使用雲端 LLM（DashScope/OpenRouter），GPU 僅用於 TTS 語音合成。如果使用本地 Ollama LLM，需要額外的 GPU 記憶體。

---

## 安裝

### 1. 下載專案

```bash
git clone https://github.com/wilsao-cyber/ai-wife-app.git
cd ai-wife-app
```

### 2. 安裝 Server

```bash
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. 安裝 Voicebox（語音合成引擎）

```bash
cd ~
git clone https://github.com/jamiepine/voicebox.git
cd voicebox
python -m venv backend/venv && source backend/venv/bin/activate
pip install -r backend/requirements.txt
pip install flash-attn --no-build-isolation  # 可選，提升 ~10% 速度
```

### 4. 安裝 SearXNG（搜尋引擎）

```bash
docker run -d --name searxng -p 8080:8080 searxng/searxng:latest
docker exec searxng sed -i '/^  formats:/,/^[^ ]/{s/    - html/    - html\n    - json/}' /etc/searxng/settings.yml
docker restart searxng
```

### 5. 設定 Google OAuth（選用，用於郵件和行事曆）

```bash
cd server
python setup_google_auth.py
```

### 6. 設定音效素材（選用）

將音效檔案放入 `sfx_library/` 目錄，或建立符號連結：

```bash
ln -s /path/to/your/sfx/folder sfx_library
```

---

## 啟動

### 一鍵啟動

```bash
./start.sh
```

會自動啟動 SearXNG → Voicebox TTS → 主伺服器 → 開啟瀏覽器。

桌面使用者也可以雙擊桌面上的 **AI Wife** 捷徑。

### 停止

```bash
./stop.sh
```

或在終端按 `Ctrl+C`。

### 手動啟動

```bash
# 終端 1: Voicebox TTS
cd ~/voicebox && source backend/venv/bin/activate
python -m backend.main --port 17493

# 終端 2: 主伺服器
cd ai-wife-app/server && source venv/bin/activate
python main.py
```

開啟 `http://localhost:8000`

---

## 初次設定

1. 開啟 `http://localhost:8000`
2. 在設定頁面選擇你的 AI 供應商：
   - **DashScope**（推薦） — 快速便宜，[申請 API Key](https://bailian.console.aliyun.com/)
   - **OpenRouter** — 無內容審查，[申請 API Key](https://openrouter.ai/)
   - **OpenAI** — GPT-4o，[申請 API Key](https://platform.openai.com/)
   - **Ollama** — 本地運行，不需要 API Key
3. 輸入 API Key，選擇模型
4. 測試連線
5. 進入聊天！

### API Keys 設定

在「設定 → LLM 供應商」頁面底部可以設定：

| Key | 用途 | 必要性 |
|-----|------|--------|
| LLM API Key | AI 對話 | 必要（雲端模式） |
| Fallback API Key | 無審查模式 | 選用 |
| Brave Search API Key | 網路搜尋備用 | 選用（有 SearXNG 即可） |
| Google OAuth | 郵件/行事曆 | 選用 |

---

## 語音訓練

你可以訓練自己的語音角色：

1. 準備 **10-15 秒**的乾淨語音片段（單人、無背景噪音）
2. 準備對應的文字稿
3. 在「設定 → 語音」中上傳，或使用 API：

```bash
# 建立角色
curl -X POST http://localhost:17493/profiles \
  -H "Content-Type: application/json" \
  -d '{"name": "my_voice", "language": "ja"}'

# 上傳語音樣本
curl -X POST "http://localhost:17493/profiles/{id}/samples" \
  -F "file=@sample.wav" \
  -F "reference_text=語音的文字稿內容"
```

> **重要**：單個語音樣本建議 10-15 秒。超過會導致 GPU 記憶體不足（attention 計算複雜度為 O(n^2)）。

---

## TTS 故障排除

如果語音生成卡住或出錯：

1. 打開「設定 → 語音 → TTS 服務管理」
2. 點擊「強制停止」殺掉 TTS 進程
3. 點擊「重新啟動」重新啟動 Voicebox
4. 等待約 30 秒讓模型載入

或使用指令：

```bash
pkill -9 -f "backend.main --port 17493"
cd ~/voicebox && source backend/venv/bin/activate && python -m backend.main --port 17493
```

---

## 致謝

本專案受以下優秀專案啟發並修改自：

- **[CoPaw](https://github.com/agentscope-ai/CoPaw)** — 雙模式 AI Agent 架構（聊天模式 + 協助模式）的設計靈感來源
- **[Voicebox](https://github.com/jamiepine/voicebox)** — 語音合成引擎，本專案基於此進行修改，加入 FlashAttention2 支援和多語音角色管理
- **[yuna0x0](https://github.com/yuna0x0)** — 特別感謝在開發過程中提供的技術支援與貢獻

### 使用的技術

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) — 阿里巴巴通義千問語音合成模型
- [Three.js](https://threejs.org/) + [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) — 3D VRM 角色渲染
- [FastAPI](https://fastapi.tiangolo.com/) — Python 後端框架
- [SearXNG](https://github.com/searxng/searxng) — 開源搜尋引擎
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) — 語音辨識 + 情緒偵測
- [FunASR](https://github.com/modelscope-audio/FunASR) — 語音辨識框架

---

## License

MIT
