# VRM Viewer, AR, Camera & Vision Design

## Overview

Replace the broken `model_viewer_plus` based 3D display with a WebView + three.js + @pixiv/three-vrm solution. Add AR mode, camera photo mode, and continuous vision perception. Remove the image-to-3D pipeline entirely.

**Target platforms:** Android, Web  
**VRM source:** VRoid Studio generated models  
**VRM format:** VRM 1.0 only

---

## Architecture

```
┌─────────────────────────────────────┐
│          Flutter App                │
│  ┌───────────────────────────────┐  │
│  │    VrmViewerWidget (WebView)  │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  vrm_viewer.html        │  │  │
│  │  │  ├── three.min.js       │  │  │
│  │  │  ├── three-vrm.min.js   │  │  │
│  │  │  ├── vrm_controller.js  │  │  │
│  │  │  ├── lip_sync.js        │  │  │
│  │  │  └── ar_session.js      │  │  │
│  │  └─────────────────────────┘  │  │
│  └──────────┬────────────────────┘  │
│             │ JavaScriptChannel     │
│  ┌──────────▼────────────────────┐  │
│  │    VrmService (Dart)          │  │
│  │    VrmController (Dart)       │  │
│  │    VisionService (Dart)       │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │    Backend API (FastAPI)      │  │
│  │    ├── VRM management APIs    │  │
│  │    ├── Vision analysis APIs   │  │
│  │    └── Emotion in chat API    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Component Details

### 1. WebView VRM Rendering Layer

**Files:**
```
mobile_app/assets/vrm_viewer/
├── vrm_viewer.html
├── js/
│   ├── three.min.js          # Three.js core (r160+)
│   ├── three-vrm.min.js      # @pixiv/three-vrm v3
│   ├── vrm_controller.js     # Model loading, expressions, animation
│   ├── lip_sync.js           # Viseme-driven lip sync
│   └── ar_session.js         # WebXR AR session management
```

**JS API (Flutter → JS):**
```javascript
window.VrmController = {
  loadModel(url),                    // Load VRM from URL or base64
  setExpression(name, value),        // Expressions: happy, sad, angry, surprised, relaxed, neutral
  startIdleAnimation(),              // Breathing + random blink
  stopIdleAnimation(),
  startLipSync(visemeData),          // Array of {time, viseme, weight}
  stopLipSync(),
  setCameraPosition(x, y, z),
  enterAR(),                         // Start WebXR AR session
  exitAR(),
  enterPhotoMode(),                  // Transparent background for camera overlay
  exitPhotoMode(),
  captureFrame(),                    // Returns base64 PNG of current VRM render
  dispose()
}
```

**JS → Flutter events (via JavaScriptChannel):**
```javascript
FlutterBridge.postMessage(JSON.stringify({
  type: 'ready' | 'modelLoaded' | 'error' | 'animationEnd' | 'arSupported' | 'frameCaptured',
  data: { ... }
}))
```

### 2. Animation Stages

**Stage A — Static display + interaction:**
- Three.js scene with camera, lighting, transparent background
- Load and render VRM model
- Touch rotate/zoom via OrbitControls
- Optional slow auto-rotate

**Stage B — Idle animation + expressions:**
- Breathing: programmatic chest bone micro-movement
- Blink: random interval `blink` BlendShape trigger (every 2-6 seconds)
- Expression switching: driven by emotion tag from chat response
- VRoid built-in BlendShape presets: `happy`, `angry`, `sad`, `relaxed`, `surprised`

**Stage C — Lip sync:**
- Backend TTS generates audio + viseme timeline simultaneously
- Viseme data sent to JS, drives mouth BlendShapes (`aa`, `ih`, `ou`, `ee`, `oh`)
- Fallback: frontend audio amplitude analysis for simple mouth open/close

### 3. Flutter Widget Layer

**VrmViewerWidget (replaces ModelViewer3D):**
```dart
VrmViewerWidget(
  modelSource: VrmModelSource.asset('assets/models/character.vrm'),
  // or: VrmModelSource.file('/path/to/uploaded.vrm')
  // or: VrmModelSource.network('http://server/vrm/model.vrm')
  enableInteraction: true,
  autoRotate: false,
  enableIdleAnimation: true,
  backgroundColor: Colors.transparent,
  onReady: () {},
  onError: (error) {},
  controller: VrmController(),
)
```

**VrmController (Dart):**
```dart
class VrmController {
  void setExpression(VrmExpression expression, {double intensity = 1.0});
  void startIdleAnimation();
  void stopIdleAnimation();
  void startLipSync(List<VisemeFrame> visemes);
  void stopLipSync();
  void resetPose();
  void enterAR();
  void exitAR();
  void enterPhotoMode();
  void exitPhotoMode();
  Future<Uint8List> captureFrame();
  Stream<VrmEvent> get events;
  bool get isARSupported;
}

enum VrmExpression { happy, sad, angry, surprised, relaxed, neutral }
```

### 4. User VRM Upload

**Flow:**
1. User taps "Change Character" button
2. `file_picker` selects `.vrm` file
3. Validate file (check glTF magic bytes `0x46546C67`)
4. Copy to app local directory via `path_provider`
5. Upload to backend `POST /api/vrm/upload` for backup/sync
6. WebView loads new model
7. `shared_preferences` remembers selected model path

**Constraints:**
- Max file size: 50MB
- VRM 1.0 format only
- Validate glTF magic bytes before loading

### 5. Emotion Analysis

Backend agent system prompt addition:
```
回應時，在結尾附加情緒標籤：[emotion:happy|sad|angry|surprised|relaxed|neutral]
```

Chat response format becomes:
```json
{
  "type": "chat_response",
  "text": "今天天氣真好呢～要不要一起出去走走？",
  "emotion": "happy",
  "audio_url": "/audio/xxx.wav",
  "visemes": [{"time": 0.0, "viseme": "aa", "weight": 0.8}, ...]
}
```

Flutter flow on response:
1. Play TTS audio
2. `vrmController.setExpression(emotion)`
3. `vrmController.startLipSync(visemes)`
4. Audio finished → `setExpression(neutral)` + `stopLipSync()`

### 6. AR Mode (WebXR)

- three.js native WebXR support (`renderer.xr.enabled = true`)
- User taps AR button → JS calls `navigator.xr.requestSession('immersive-ar')`
- VRM model placed on real-world surface, keeps idle animation + expressions
- Exit AR → return to normal WebView display

**Platform support:**
| Platform | Method | Requirement |
|----------|--------|-------------|
| Android | WebXR via WebView | ARCore-capable device + Chrome WebView 79+ |
| Web | WebXR via browser | Chrome/Edge with WebXR support |

- AR button hidden when `isARSupported` is false
- Touch rotation paused in AR; model positioned in real space

### 7. Camera Photo Mode

**Flow:**
1. User taps "Photo" button
2. Camera preview opens (full screen)
3. VRM character overlaid on camera feed (WebView transparent background)
4. Switch front/rear camera, adjust character position/size
5. Tap shutter → composite screenshot (camera frame + VRM layer)
6. Preview → save to gallery / share

**Dependencies:**
- `camera` — camera preview and capture
- `image_gallery_saver` — save to photo gallery
- `share_plus` — share functionality

### 8. Continuous Vision Perception (Companion Mode)

**Concept:** Camera stays on. AI wife "sees" the user continuously and reacts to visual changes proactively — like a real companion sitting across from you.

**Flow:**
```
Camera always on (front or rear)
       │
       ▼
  Extract one frame every N seconds (configurable: 2-5s)
       │
       ▼
  Send to backend POST /api/vision/stream
  Include recent conversation context
       │
       ▼
  Backend:
  1. Compare with previous frame (image embedding distance)
  2. Significant change → send to LLM Vision for analysis
  3. No change → skip silently
       │
       ▼
  If response generated:
  text + emotion + audio + visemes → VRM reacts
```

**Design principles:**
- **Not every frame gets a response** — only reacts when scene changes or user interaction intent detected. Otherwise, quiet companionship.
- **Battery-saving** — adjustable frame interval, pauses when app in background
- **Privacy** — frames analyzed in-memory only, never stored. User can disable at any time.

**VisionService (Dart):**
```dart
class VisionService {
  bool isActive = false;
  Duration frameInterval = Duration(seconds: 3);

  void startContinuousVision();    // Start companion mode
  void stopContinuousVision();     // Stop
  void setFrameInterval(Duration); // Adjust frequency
  void captureOnce();              // Single photo analysis
}
```

**Backend scene change detection:**
```python
# Compare consecutive frames via image embedding cosine distance
# Distance > threshold → scene changed → send to LLM Vision
# Distance < threshold → skip, don't disturb
```

**UI modes:**

| Mode | Description |
|------|-------------|
| Companion mode | Camera always on (small window or background), AI wife watches, speaks only when relevant |
| Photo mode | Camera full screen + VRM overlay, can capture/share |
| Off | Camera closed, text/voice interaction only |

HomeScreen: "eye" icon toggles companion mode.

---

## Backend API Changes

### Remove
- `image_to_3d.py` — delete entirely
- `POST /api/image-to-3d` endpoint — remove
- `models/3d/TripoSR/` — remove
- `models/3d/CharacterGen/` — remove
- `scripts/charactergen_2d.py`, `scripts/auto_3d_pipeline.py` — remove
- `scripts/claude_computer_use_pipeline.py`, `scripts/claude_mesh2motion.py`, `scripts/mcp_mesh2motion.py` — remove

### Add VRM management
```
POST   /api/vrm/upload       # Upload VRM file (multipart)
GET    /api/vrm/list          # List all uploaded VRM files
GET    /vrm/{filename}        # Download/serve VRM file
DELETE /api/vrm/{filename}    # Delete VRM file
```

Storage: `server/output/vrm/`

### Add Vision APIs
```
POST /api/vision/capture      # Single image analysis
POST /api/vision/stream       # Continuous vision (with change detection)
```

**LLM requirement:** Vision-capable model (e.g., `llava`, `qwen2-vl` via Ollama). Fallback response if no vision model: "抱歉～我現在看不太清楚呢"

### Modify chat response
Add `emotion` field and optional `visemes` field to all chat responses.

---

## Flutter Dependency Changes

### Remove
- `model_viewer_plus: ^1.8.0`

### Add
- `webview_flutter: ^4.x` — WebView for VRM rendering (uses `webview_flutter_android` on Android; on Web, the VRM viewer HTML runs directly in the browser via `HtmlElementView`)
- `camera: ^0.11.x` — Camera preview and capture
- `image_gallery_saver: ^2.x` — Save photos to gallery
- `share_plus: ^9.x` — Share photos

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| WebView fails to load | Show static 2D avatar fallback + retry button |
| VRM file corrupt/invalid | Validate glTF magic bytes, reject and show prompt |
| Upload file too large (>50MB) | Frontend intercept, show file-too-large message |
| Model load timeout (>10s) | Show timeout prompt + retry |
| JS execution error | JS → Flutter error event, display error message |
| WebView crash | Listen `onWebResourceError`, auto-rebuild WebView |
| Vision model unavailable | Fallback text response: "抱歉～我現在看不太清楚呢" |
| AR not supported | Hide AR button |
| Camera permission denied | Show permission explanation dialog |

---

## Out of Scope

- Model editing / custom clothing
- Multiple characters on screen simultaneously
- VRM 0.x backward compatibility (VRM 1.0 only)
- iOS platform
- Face tracking to drive VRM expressions

---

## Implementation Stages

| Feature | Stage |
|---------|-------|
| VRM model display + rotation interaction | A |
| User upload VRM | A |
| Remove image-to-3D pipeline | A |
| Idle animation (breathing + blink) | B |
| Emotion expression switching | B |
| Lip sync | C |
| AR mode (WebXR) | C |
| Photo with character / share | C |
| Continuous vision perception (companion mode) | C |
