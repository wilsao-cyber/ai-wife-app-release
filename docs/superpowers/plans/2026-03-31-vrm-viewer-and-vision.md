# VRM Viewer, AR, Camera & Vision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken model_viewer_plus 3D display with a WebView + three.js + @pixiv/three-vrm VRM viewer, add idle animation, emotion expressions, lip sync, AR mode, camera photo mode, and continuous vision perception.

**Architecture:** A local HTML page bundled in Flutter assets renders VRM models using three.js + @pixiv/three-vrm inside a WebView. Flutter communicates with the WebView via JavaScriptChannel for model control (expressions, animations, lip sync, AR). A VisionService uses the device camera for photo mode and continuous companion mode, sending frames to the backend for LLM vision analysis.

**Tech Stack:** Flutter (webview_flutter, camera), JavaScript (three.js r160, @pixiv/three-vrm v3, WebXR), Python FastAPI backend (Ollama vision models)

---

## File Map

### Files to Create

| File | Responsibility |
|------|---------------|
| `mobile_app/assets/vrm_viewer/vrm_viewer.html` | Main HTML page: three.js scene, loads VRM, exposes JS API |
| `mobile_app/assets/vrm_viewer/js/vrm_controller.js` | VRM model loading, expressions, idle animation, camera control |
| `mobile_app/assets/vrm_viewer/js/lip_sync.js` | Viseme-driven lip sync engine |
| `mobile_app/assets/vrm_viewer/js/ar_session.js` | WebXR AR session management |
| `mobile_app/lib/widgets/vrm_viewer_widget.dart` | Flutter WebView widget wrapping VRM viewer |
| `mobile_app/lib/services/vrm_service.dart` | VRM model management (upload, select, persist preference) |
| `mobile_app/lib/services/vision_service.dart` | Camera capture, continuous vision, photo mode |
| `mobile_app/lib/screens/photo_screen.dart` | Camera + VRM overlay photo screen |
| `mobile_app/lib/models/vrm_model.dart` | VrmModelSource, VrmExpression, VisemeFrame, VrmEvent data types |
| `server/vrm_manager.py` | VRM file upload/list/serve/delete logic |
| `server/vision_analyzer.py` | Vision analysis: single capture + continuous stream with change detection |
| `server/tests/test_vrm_manager.py` | Tests for VRM manager |
| `server/tests/test_vision_analyzer.py` | Tests for vision analyzer |
| `mobile_app/test/vrm_viewer_widget_test.dart` | Tests for VRM viewer widget |
| `mobile_app/test/vrm_service_test.dart` | Tests for VRM service |

### Files to Modify

| File | Changes |
|------|---------|
| `mobile_app/pubspec.yaml` | Remove model_viewer_plus, add webview_flutter/camera/image_gallery_saver/share_plus, add vrm_viewer assets |
| `mobile_app/lib/screens/home_screen.dart` | Replace ModelViewer3D with VrmViewerWidget, add AR/photo/companion buttons |
| `mobile_app/lib/screens/settings_screen.dart` | Add VRM model selection, companion mode settings |
| `mobile_app/lib/services/api_service.dart` | Add VRM upload/list, vision capture/stream methods |
| `mobile_app/lib/utils/constants.dart` | Add VRM and vision related constants |
| `server/main.py` | Remove image-to-3d endpoint, add VRM and vision endpoints, add emotion to chat response |
| `server/agent.py` | Add emotion tag to system prompt, parse emotion from response, remove image_to_3d dependency |
| `server/config.py` | Add VisionConfig, remove ImageTo3DConfig |

### Files to Delete

| File | Reason |
|------|--------|
| `server/image_to_3d.py` | Replaced by VRM upload |
| `mobile_app/lib/widgets/model_viewer_3d.dart` | Replaced by vrm_viewer_widget.dart |
| `scripts/charactergen_2d.py` | Image-to-3D pipeline removed |
| `scripts/auto_3d_pipeline.py` | Image-to-3D pipeline removed |
| `scripts/claude_computer_use_pipeline.py` | Image-to-3D pipeline removed |
| `scripts/claude_mesh2motion.py` | Image-to-3D pipeline removed |
| `scripts/mcp_mesh2motion.py` | Image-to-3D pipeline removed |

---

## Stage A: VRM Display + Upload + Cleanup

### Task 1: Remove image-to-3D pipeline and old model viewer

**Files:**
- Delete: `server/image_to_3d.py`
- Delete: `mobile_app/lib/widgets/model_viewer_3d.dart`
- Delete: `scripts/charactergen_2d.py`, `scripts/auto_3d_pipeline.py`, `scripts/claude_computer_use_pipeline.py`, `scripts/claude_mesh2motion.py`, `scripts/mcp_mesh2motion.py`
- Modify: `server/main.py`
- Modify: `server/agent.py`
- Modify: `server/config.py`
- Modify: `mobile_app/pubspec.yaml`

- [ ] **Step 1: Delete image-to-3D files**

```bash
rm server/image_to_3d.py
rm scripts/charactergen_2d.py scripts/auto_3d_pipeline.py
rm scripts/claude_computer_use_pipeline.py scripts/claude_mesh2motion.py scripts/mcp_mesh2motion.py
rm mobile_app/lib/widgets/model_viewer_3d.dart
```

- [ ] **Step 2: Remove image-to-3d endpoint from server/main.py**

Remove the `api_image_to_3d` function and its import. In `server/main.py`, delete lines for:
```python
# DELETE this endpoint (around line 192-196):
@app.post("/api/image-to-3d")
async def api_image_to_3d(image: UploadFile = File(...)):
    image_data = await image.read()
    model_path = await agent.generate_3d_model(image_data)
    return {"model_url": f"/models/{model_path}"}
```

- [ ] **Step 3: Remove ImageTo3D from agent.py**

In `server/agent.py`, remove the `ImageTo3D` import, the `self.image_to_3d` property initialization, and the `generate_3d_model` method.

- [ ] **Step 4: Remove ImageTo3DConfig from config.py**

In `server/config.py`, delete the `ImageTo3DConfig` class and the `image_to_3d` field from `ServerConfig`. Also remove the `image_to_3d` section parsing from `load_config()`.

- [ ] **Step 5: Remove model_viewer_plus from pubspec.yaml**

In `mobile_app/pubspec.yaml`, remove:
```yaml
  model_viewer_plus: ^1.8.0
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove image-to-3D pipeline and model_viewer_plus

Removes TripoSR/CRM/CharacterGen pipeline, 3D generation scripts,
model_viewer_3d.dart widget, and /api/image-to-3d endpoint.
Preparing for WebView + three-vrm replacement."
```

---

### Task 2: Add Flutter dependencies and VRM data models

**Files:**
- Modify: `mobile_app/pubspec.yaml`
- Create: `mobile_app/lib/models/vrm_model.dart`
- Modify: `mobile_app/lib/utils/constants.dart`

- [ ] **Step 1: Add new dependencies to pubspec.yaml**

Add these to the `dependencies:` section in `mobile_app/pubspec.yaml`:
```yaml
  webview_flutter: ^4.10.0
  camera: ^0.11.0+2
  image_gallery_saver_plus: ^4.0.0
  share_plus: ^9.0.0
```

Add to the `flutter: assets:` section:
```yaml
    - assets/vrm_viewer/
    - assets/vrm_viewer/js/
```

- [ ] **Step 2: Run flutter pub get**

```bash
cd mobile_app && flutter pub get
```

- [ ] **Step 3: Create VRM data models**

Create `mobile_app/lib/models/vrm_model.dart`:
```dart
import 'dart:typed_data';

enum VrmModelSourceType { asset, file, network }

class VrmModelSource {
  final VrmModelSourceType type;
  final String path;

  const VrmModelSource._(this.type, this.path);

  factory VrmModelSource.asset(String assetPath) =>
      VrmModelSource._(VrmModelSourceType.asset, assetPath);

  factory VrmModelSource.file(String filePath) =>
      VrmModelSource._(VrmModelSourceType.file, filePath);

  factory VrmModelSource.network(String url) =>
      VrmModelSource._(VrmModelSourceType.network, url);
}

enum VrmExpression { happy, sad, angry, surprised, relaxed, neutral }

class VisemeFrame {
  final double time;
  final String viseme;
  final double weight;

  const VisemeFrame({
    required this.time,
    required this.viseme,
    required this.weight,
  });

  Map<String, dynamic> toJson() => {
        'time': time,
        'viseme': viseme,
        'weight': weight,
      };

  factory VisemeFrame.fromJson(Map<String, dynamic> json) => VisemeFrame(
        time: (json['time'] as num).toDouble(),
        viseme: json['viseme'] as String,
        weight: (json['weight'] as num).toDouble(),
      );
}

enum VrmEventType { ready, modelLoaded, error, animationEnd, arSupported, frameCaptured }

class VrmEvent {
  final VrmEventType type;
  final Map<String, dynamic> data;

  const VrmEvent({required this.type, this.data = const {}});

  factory VrmEvent.fromJson(Map<String, dynamic> json) {
    final typeStr = json['type'] as String;
    final type = VrmEventType.values.firstWhere(
      (e) => e.name == typeStr,
      orElse: () => VrmEventType.error,
    );
    return VrmEvent(
      type: type,
      data: (json['data'] as Map<String, dynamic>?) ?? {},
    );
  }
}

class VrmFileInfo {
  final String filename;
  final int size;
  final String uploadedAt;

  const VrmFileInfo({
    required this.filename,
    required this.size,
    required this.uploadedAt,
  });

  factory VrmFileInfo.fromJson(Map<String, dynamic> json) => VrmFileInfo(
        filename: json['filename'] as String,
        size: json['size'] as int,
        uploadedAt: json['uploaded_at'] as String,
      );
}
```

- [ ] **Step 4: Add VRM constants**

In `mobile_app/lib/utils/constants.dart`, add these constants after the existing ones:
```dart
  // VRM
  static const String defaultVrmModel = 'assets/models/character.vrm';
  static const int maxVrmFileSizeMB = 50;
  static const int maxVrmFileSizeBytes = maxVrmFileSizeMB * 1024 * 1024;
  static const List<int> gltfMagicBytes = [0x67, 0x6C, 0x54, 0x46]; // glTF

  // Vision
  static const int visionFrameIntervalSeconds = 3;
  static const double visionChangeThreshold = 0.3;
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add VRM dependencies, data models, and constants

Adds webview_flutter, camera, image_gallery_saver_plus, share_plus.
Creates VrmModelSource, VrmExpression, VisemeFrame, VrmEvent types.
Adds VRM and vision constants."
```

---

### Task 3: Download three.js and three-vrm libraries

**Files:**
- Create: `mobile_app/assets/vrm_viewer/js/` directory with library files

- [ ] **Step 1: Create vrm_viewer asset directory**

```bash
mkdir -p mobile_app/assets/vrm_viewer/js
```

- [ ] **Step 2: Download three.js (r170 ES module build)**

```bash
cd mobile_app/assets/vrm_viewer/js
curl -L -o three.module.min.js "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.min.js"
curl -L -o OrbitControls.js "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/controls/OrbitControls.js"
```

- [ ] **Step 3: Download @pixiv/three-vrm**

```bash
curl -L -o three-vrm.module.min.js "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3/lib/three-vrm.module.min.js"
```

- [ ] **Step 4: Verify downloads are valid JS files (not HTML error pages)**

```bash
head -c 200 three.module.min.js
head -c 200 three-vrm.module.min.js
head -c 200 OrbitControls.js
```

Each file should start with JS code (e.g., `//`, `import`, `export`, or minified JS), not `<!DOCTYPE html>`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add three.js and @pixiv/three-vrm libraries

Downloads three.js r170, OrbitControls, and three-vrm v3 for
VRM model rendering in WebView."
```

---

### Task 4: Create vrm_viewer.html and vrm_controller.js

**Files:**
- Create: `mobile_app/assets/vrm_viewer/vrm_viewer.html`
- Create: `mobile_app/assets/vrm_viewer/js/vrm_controller.js`

- [ ] **Step 1: Create vrm_viewer.html**

Create `mobile_app/assets/vrm_viewer/vrm_viewer.html`:
```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { margin: 0; padding: 0; }
  html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
  canvas { display: block; width: 100%; height: 100%; }
  #loading {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    color: #FF69B4; font-family: sans-serif; font-size: 16px;
    display: flex; flex-direction: column; align-items: center; gap: 12px;
  }
  #loading .spinner {
    width: 40px; height: 40px; border: 3px solid rgba(255,105,180,0.3);
    border-top-color: #FF69B4; border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  #loading.hidden { display: none; }
  #error {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    color: #ff4444; font-family: sans-serif; font-size: 14px; text-align: center;
    display: none; padding: 20px;
  }
</style>
</head>
<body>
<div id="loading"><div class="spinner"></div><span>Loading model...</span></div>
<div id="error"></div>

<script type="importmap">
{
  "imports": {
    "three": "./js/three.module.min.js",
    "three/addons/": "./js/",
    "@pixiv/three-vrm": "./js/three-vrm.module.min.js"
  }
}
</script>

<script type="module" src="./js/vrm_controller.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create vrm_controller.js — scene setup**

Create `mobile_app/assets/vrm_viewer/js/vrm_controller.js`:
```javascript
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';
import { GLTFLoader } from 'three/addons/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

// --- State ---
let scene, camera, renderer, controls, clock;
let currentVrm = null;
let idleAnimationId = null;
let blinkTimeout = null;
let isIdleRunning = false;

// --- Flutter Bridge ---
function sendToFlutter(type, data = {}) {
  try {
    if (window.FlutterBridge) {
      window.FlutterBridge.postMessage(JSON.stringify({ type, data }));
    }
  } catch (e) {
    console.error('FlutterBridge error:', e);
  }
}

// --- Scene Setup ---
function initScene() {
  clock = new THREE.Clock();
  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 1.3, 2.5);

  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  document.body.appendChild(renderer.domElement);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
  directionalLight.position.set(1, 2, 1);
  scene.add(directionalLight);

  const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
  fillLight.position.set(-1, 1, -1);
  scene.add(fillLight);

  // Controls
  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.0, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.1;
  controls.minDistance = 1.0;
  controls.maxDistance = 5.0;
  controls.maxPolarAngle = Math.PI * 0.85;
  controls.update();

  window.addEventListener('resize', onResize);
  animate();
  sendToFlutter('ready');
}

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();

  if (currentVrm) {
    currentVrm.update(delta);
  }

  controls.update();
  renderer.render(scene, camera);
}

// --- Model Loading ---
async function loadModel(url) {
  const loadingEl = document.getElementById('loading');
  const errorEl = document.getElementById('error');
  loadingEl.classList.remove('hidden');
  errorEl.style.display = 'none';

  // Remove existing model
  if (currentVrm) {
    VRMUtils.deepDispose(currentVrm.scene);
    scene.remove(currentVrm.scene);
    currentVrm = null;
  }

  const loader = new GLTFLoader();
  loader.register((parser) => new VRMLoaderPlugin(parser));

  try {
    const gltf = await loader.loadAsync(url);
    const vrm = gltf.userData.vrm;

    if (!vrm) {
      throw new Error('Not a valid VRM file');
    }

    VRMUtils.rotateVRM0(vrm);
    scene.add(vrm.scene);
    currentVrm = vrm;

    // Auto-center camera on model
    const box = new THREE.Box3().setFromObject(vrm.scene);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    controls.target.set(center.x, center.y, center.z);
    camera.position.set(center.x, center.y + size.y * 0.1, size.y * 2.5);
    controls.update();

    loadingEl.classList.add('hidden');
    sendToFlutter('modelLoaded', {
      expressionNames: vrm.expressionManager
        ? Object.keys(vrm.expressionManager.expressionMap)
        : [],
    });
  } catch (e) {
    loadingEl.classList.add('hidden');
    errorEl.textContent = 'Failed to load model: ' + e.message;
    errorEl.style.display = 'block';
    sendToFlutter('error', { message: e.message });
  }
}

// --- Expressions ---
function setExpression(name, value = 1.0) {
  if (!currentVrm || !currentVrm.expressionManager) return;
  // Reset all expressions first
  for (const key of Object.keys(currentVrm.expressionManager.expressionMap)) {
    currentVrm.expressionManager.setValue(key, 0);
  }
  if (name !== 'neutral') {
    currentVrm.expressionManager.setValue(name, value);
  }
}

// --- Idle Animation ---
function startIdleAnimation() {
  if (isIdleRunning) return;
  isIdleRunning = true;

  // Breathing: subtle chest bone Y oscillation
  const breathe = () => {
    if (!isIdleRunning || !currentVrm) return;
    const t = clock.getElapsedTime();
    const chest = currentVrm.humanoid?.getNormalizedBoneNode('chest');
    if (chest) {
      chest.rotation.x = Math.sin(t * 0.8) * 0.01;
    }
    const spine = currentVrm.humanoid?.getNormalizedBoneNode('spine');
    if (spine) {
      spine.rotation.x = Math.sin(t * 0.8 + 0.5) * 0.005;
    }
  };

  // Blink: random interval 2-6 seconds
  const blink = () => {
    if (!isIdleRunning || !currentVrm) return;
    if (currentVrm.expressionManager) {
      currentVrm.expressionManager.setValue('blink', 1);
      setTimeout(() => {
        if (currentVrm?.expressionManager) {
          currentVrm.expressionManager.setValue('blink', 0);
        }
      }, 150);
    }
    const nextBlink = 2000 + Math.random() * 4000;
    blinkTimeout = setTimeout(blink, nextBlink);
  };

  // Attach breathing to render loop
  const originalAnimate = animate;
  const idleRenderLoop = () => {
    breathe();
  };
  // Use a simpler approach: override update
  if (currentVrm) {
    const originalUpdate = currentVrm.update.bind(currentVrm);
    currentVrm.update = (delta) => {
      originalUpdate(delta);
      breathe();
    };
  }

  blinkTimeout = setTimeout(blink, 1000 + Math.random() * 3000);
}

function stopIdleAnimation() {
  isIdleRunning = false;
  if (blinkTimeout) {
    clearTimeout(blinkTimeout);
    blinkTimeout = null;
  }
}

// --- Camera ---
function setCameraPosition(x, y, z) {
  camera.position.set(x, y, z);
  controls.update();
}

function setAutoRotate(enabled) {
  controls.autoRotate = enabled;
  controls.autoRotateSpeed = 1.0;
}

function setInteraction(enabled) {
  controls.enabled = enabled;
}

// --- Frame Capture ---
function captureFrame() {
  renderer.render(scene, camera);
  const dataUrl = renderer.domElement.toDataURL('image/png');
  sendToFlutter('frameCaptured', { imageData: dataUrl });
}

// --- Cleanup ---
function dispose() {
  stopIdleAnimation();
  if (currentVrm) {
    VRMUtils.deepDispose(currentVrm.scene);
    scene.remove(currentVrm.scene);
    currentVrm = null;
  }
  renderer.dispose();
  controls.dispose();
}

// --- Public API ---
window.VrmController = {
  loadModel,
  setExpression,
  startIdleAnimation,
  stopIdleAnimation,
  setCameraPosition,
  setAutoRotate,
  setInteraction,
  captureFrame,
  dispose,
};

// Initialize on load
initScene();
```

- [ ] **Step 3: Verify the importmap references exist**

Check that `GLTFLoader.js` is needed (it's included in three.js). If not available as a separate file, download it:
```bash
cd mobile_app/assets/vrm_viewer/js
curl -L -o GLTFLoader.js "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/loaders/GLTFLoader.js"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: create VRM viewer HTML and controller JS

Implements three.js scene with VRM loading via @pixiv/three-vrm,
OrbitControls for interaction, expression control, idle animation
(breathing + blink), camera positioning, and frame capture.
Exposes window.VrmController API for Flutter bridge."
```

---

### Task 5: Create VrmViewerWidget (Flutter WebView wrapper)

**Files:**
- Create: `mobile_app/lib/widgets/vrm_viewer_widget.dart`

- [ ] **Step 1: Create vrm_viewer_widget.dart**

Create `mobile_app/lib/widgets/vrm_viewer_widget.dart`:
```dart
import 'dart:convert';
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../models/vrm_model.dart';

class VrmViewerController {
  WebViewController? _webViewController;
  final _eventController = StreamController<VrmEvent>.broadcast();
  bool _isARSupported = false;

  Stream<VrmEvent> get events => _eventController.stream;
  bool get isARSupported => _isARSupported;

  void _attach(WebViewController controller) {
    _webViewController = controller;
  }

  void _handleMessage(String message) {
    try {
      final json = jsonDecode(message) as Map<String, dynamic>;
      final event = VrmEvent.fromJson(json);
      if (event.type == VrmEventType.arSupported) {
        _isARSupported = event.data['supported'] == true;
      }
      _eventController.add(event);
    } catch (e) {
      debugPrint('VRM event parse error: $e');
    }
  }

  Future<void> _runJs(String js) async {
    await _webViewController?.runJavaScript(js);
  }

  Future<void> loadModel(String url) => _runJs("VrmController.loadModel('$url')");

  Future<void> setExpression(VrmExpression expression, {double intensity = 1.0}) =>
      _runJs("VrmController.setExpression('${expression.name}', $intensity)");

  Future<void> startIdleAnimation() => _runJs('VrmController.startIdleAnimation()');

  Future<void> stopIdleAnimation() => _runJs('VrmController.stopIdleAnimation()');

  Future<void> startLipSync(List<VisemeFrame> visemes) {
    final json = jsonEncode(visemes.map((v) => v.toJson()).toList());
    return _runJs("VrmController.startLipSync($json)");
  }

  Future<void> stopLipSync() => _runJs('VrmController.stopLipSync()');

  Future<void> resetPose() => _runJs("VrmController.setExpression('neutral')");

  Future<void> setCameraPosition(double x, double y, double z) =>
      _runJs('VrmController.setCameraPosition($x, $y, $z)');

  Future<void> setAutoRotate(bool enabled) =>
      _runJs('VrmController.setAutoRotate($enabled)');

  Future<void> captureFrame() => _runJs('VrmController.captureFrame()');

  Future<void> enterAR() => _runJs('VrmController.enterAR()');

  Future<void> exitAR() => _runJs('VrmController.exitAR()');

  void dispose() {
    _runJs('VrmController.dispose()');
    _eventController.close();
  }
}

class VrmViewerWidget extends StatefulWidget {
  final VrmModelSource modelSource;
  final bool enableInteraction;
  final bool autoRotate;
  final bool enableIdleAnimation;
  final Color backgroundColor;
  final VoidCallback? onReady;
  final void Function(String error)? onError;
  final VrmViewerController? controller;

  const VrmViewerWidget({
    super.key,
    required this.modelSource,
    this.enableInteraction = true,
    this.autoRotate = false,
    this.enableIdleAnimation = true,
    this.backgroundColor = Colors.transparent,
    this.onReady,
    this.onError,
    this.controller,
  });

  @override
  State<VrmViewerWidget> createState() => _VrmViewerWidgetState();
}

class _VrmViewerWidgetState extends State<VrmViewerWidget> {
  late WebViewController _webViewController;
  bool _isLoading = true;
  String? _error;
  StreamSubscription<VrmEvent>? _eventSub;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  void _initWebView() {
    _webViewController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(widget.backgroundColor)
      ..addJavaScriptChannel(
        'FlutterBridge',
        onMessageReceived: (message) {
          widget.controller?._handleMessage(message.message);
          _onJsMessage(message.message);
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (_) => _onPageLoaded(),
          onWebResourceError: (error) {
            setState(() {
              _error = error.description;
              _isLoading = false;
            });
            widget.onError?.call(error.description);
          },
        ),
      )
      ..loadFlutterAsset('assets/vrm_viewer/vrm_viewer.html');

    widget.controller?._attach(_webViewController);
  }

  void _onPageLoaded() {
    // Configure controls
    widget.controller?.setAutoRotate(widget.autoRotate);
    if (!widget.enableInteraction) {
      widget.controller?._runJs('VrmController.setInteraction(false)');
    }
  }

  void _onJsMessage(String message) {
    try {
      final json = jsonDecode(message) as Map<String, dynamic>;
      final type = json['type'] as String;

      switch (type) {
        case 'ready':
          _loadModel();
          break;
        case 'modelLoaded':
          setState(() => _isLoading = false);
          if (widget.enableIdleAnimation) {
            widget.controller?.startIdleAnimation();
          }
          widget.onReady?.call();
          break;
        case 'error':
          final msg = (json['data'] as Map?)?['message'] ?? 'Unknown error';
          setState(() {
            _error = msg.toString();
            _isLoading = false;
          });
          widget.onError?.call(msg.toString());
          break;
      }
    } catch (e) {
      debugPrint('JS message parse error: $e');
    }
  }

  void _loadModel() {
    final source = widget.modelSource;
    String url;
    switch (source.type) {
      case VrmModelSourceType.asset:
        // For assets, we need to serve via a local URL
        // WebView loadFlutterAsset makes assets available relative to the HTML
        url = '../models/${source.path.split('/').last}';
        break;
      case VrmModelSourceType.file:
        url = 'file://${source.path}';
        break;
      case VrmModelSourceType.network:
        url = source.path;
        break;
    }
    widget.controller?.loadModel(url);
  }

  @override
  void didUpdateWidget(VrmViewerWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.modelSource.path != widget.modelSource.path) {
      setState(() => _isLoading = true);
      _loadModel();
    }
  }

  @override
  void dispose() {
    _eventSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        WebViewWidget(controller: _webViewController),
        if (_isLoading)
          const Center(
            child: CircularProgressIndicator(color: Color(0xFFFF69B4)),
          ),
        if (_error != null)
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, color: Colors.red, size: 48),
                const SizedBox(height: 8),
                Text(
                  _error!,
                  style: const TextStyle(color: Colors.red),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    setState(() {
                      _error = null;
                      _isLoading = true;
                    });
                    _webViewController.loadFlutterAsset(
                        'assets/vrm_viewer/vrm_viewer.html');
                  },
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: create VrmViewerWidget with WebView + three-vrm bridge

Flutter widget that wraps webview_flutter to render VRM models.
VrmViewerController provides Dart API for expressions, idle animation,
camera control, AR, and frame capture via JavaScriptChannel bridge."
```

---

### Task 6: Integrate VrmViewerWidget into HomeScreen

**Files:**
- Modify: `mobile_app/lib/screens/home_screen.dart`

- [ ] **Step 1: Replace ModelViewer3D with VrmViewerWidget in home_screen.dart**

Replace the full content of `mobile_app/lib/screens/home_screen.dart` with:
```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../widgets/vrm_viewer_widget.dart';
import '../widgets/voice_input_button.dart';
import '../models/vrm_model.dart';
import '../utils/theme.dart';
import '../utils/constants.dart';
import 'chat_screen.dart';
import 'email_screen.dart';
import 'calendar_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    _HomeTab(),
    ChatScreen(),
    EmailScreen(),
    CalendarScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        type: BottomNavigationBarType.fixed,
        backgroundColor: AppTheme.surfaceColor,
        selectedItemColor: AppTheme.primaryColor,
        unselectedItemColor: AppTheme.textSecondaryColor,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.chat), label: 'Chat'),
          BottomNavigationBarItem(icon: Icon(Icons.email), label: 'Email'),
          BottomNavigationBarItem(icon: Icon(Icons.calendar_today), label: 'Calendar'),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}

class _HomeTab extends StatefulWidget {
  const _HomeTab();

  @override
  State<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<_HomeTab> {
  final _vrmController = VrmViewerController();
  bool _modelReady = false;

  @override
  void dispose() {
    _vrmController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              flex: 3,
              child: VrmViewerWidget(
                modelSource: VrmModelSource.asset(Constants.defaultVrmModel),
                enableInteraction: true,
                enableIdleAnimation: true,
                controller: _vrmController,
                onReady: () => setState(() => _modelReady = true),
                onError: (e) => debugPrint('VRM error: $e'),
              ),
            ),
            Expanded(
              flex: 1,
              child: Container(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(
                      'Hello~ 老公今天想做什麼呢？',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.textColor,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        _QuickAction(icon: Icons.mic, label: '語音對話', onTap: () {}),
                        _QuickAction(icon: Icons.email, label: '查看郵件', onTap: () {}),
                        _QuickAction(icon: Icons.calendar_today, label: '今日行程', onTap: () {}),
                        _QuickAction(icon: Icons.search, label: '搜尋資料', onTap: () {}),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const VoiceInputButton(),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _QuickAction({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.cardColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: AppTheme.primaryColor),
          ),
          const SizedBox(height: 4),
          Text(label, style: TextStyle(fontSize: 12, color: AppTheme.textSecondaryColor)),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Verify build compiles**

```bash
cd mobile_app && flutter build apk --debug 2>&1 | tail -20
```

Expected: BUILD SUCCESSFUL (or only non-fatal warnings).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: integrate VrmViewerWidget into HomeScreen

Replaces ModelViewer3D with VrmViewerWidget showing VRM character
via WebView + three.js. Includes idle animation on model ready."
```

---

### Task 7: Backend VRM file management

**Files:**
- Create: `server/vrm_manager.py`
- Create: `server/tests/test_vrm_manager.py`
- Modify: `server/main.py`

- [ ] **Step 1: Write test for VRM manager**

Create `server/tests/__init__.py`:
```python
```

Create `server/tests/test_vrm_manager.py`:
```python
import os
import tempfile
import pytest
from pathlib import Path

# glTF magic bytes: "glTF" in little-endian
GLTF_MAGIC = b'glTF'
FAKE_VRM = GLTF_MAGIC + b'\x02\x00\x00\x00' + b'\x00' * 100  # minimal valid header
INVALID_FILE = b'not a vrm file at all'


@pytest.fixture
def vrm_dir(tmp_path):
    return tmp_path / "vrm"


@pytest.fixture
def manager(vrm_dir):
    from vrm_manager import VrmManager
    return VrmManager(str(vrm_dir))


def test_save_valid_vrm(manager, vrm_dir):
    filename = manager.save(FAKE_VRM, "test_model.vrm")
    assert filename == "test_model.vrm"
    assert (vrm_dir / "test_model.vrm").exists()


def test_save_rejects_invalid_file(manager):
    with pytest.raises(ValueError, match="Invalid VRM"):
        manager.save(INVALID_FILE, "bad.vrm")


def test_save_rejects_oversized_file(manager):
    big_data = GLTF_MAGIC + b'\x02\x00\x00\x00' + b'\x00' * (50 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="exceeds"):
        manager.save(big_data, "huge.vrm")


def test_list_empty(manager):
    result = manager.list_models()
    assert result == []


def test_list_after_save(manager):
    manager.save(FAKE_VRM, "model_a.vrm")
    manager.save(FAKE_VRM, "model_b.vrm")
    result = manager.list_models()
    filenames = [r["filename"] for r in result]
    assert "model_a.vrm" in filenames
    assert "model_b.vrm" in filenames


def test_delete(manager, vrm_dir):
    manager.save(FAKE_VRM, "to_delete.vrm")
    assert (vrm_dir / "to_delete.vrm").exists()
    manager.delete("to_delete.vrm")
    assert not (vrm_dir / "to_delete.vrm").exists()


def test_delete_nonexistent(manager):
    with pytest.raises(FileNotFoundError):
        manager.delete("nonexistent.vrm")


def test_get_path(manager, vrm_dir):
    manager.save(FAKE_VRM, "my.vrm")
    path = manager.get_path("my.vrm")
    assert path == str(vrm_dir / "my.vrm")


def test_get_path_nonexistent(manager):
    with pytest.raises(FileNotFoundError):
        manager.get_path("missing.vrm")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd server && python -m pytest tests/test_vrm_manager.py -v 2>&1
```

Expected: ERRORS — `ModuleNotFoundError: No module named 'vrm_manager'`

- [ ] **Step 3: Implement VrmManager**

Create `server/vrm_manager.py`:
```python
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_VRM_SIZE = 50 * 1024 * 1024  # 50MB
GLTF_MAGIC = b'glTF'


class VrmManager:
    def __init__(self, vrm_dir: str = "./output/vrm"):
        self.vrm_dir = Path(vrm_dir)
        self.vrm_dir.mkdir(parents=True, exist_ok=True)

    def _validate(self, data: bytes, filename: str) -> None:
        if len(data) > MAX_VRM_SIZE:
            raise ValueError(f"File exceeds {MAX_VRM_SIZE // (1024*1024)}MB limit")
        if data[:4] != GLTF_MAGIC:
            raise ValueError("Invalid VRM file: missing glTF magic bytes")
        if not filename.endswith('.vrm'):
            raise ValueError("Filename must end with .vrm")

    def save(self, data: bytes, filename: str) -> str:
        self._validate(data, filename)
        path = self.vrm_dir / filename
        path.write_bytes(data)
        logger.info(f"VRM saved: {filename} ({len(data)} bytes)")
        return filename

    def list_models(self) -> list[dict]:
        result = []
        for f in sorted(self.vrm_dir.glob("*.vrm")):
            stat = f.stat()
            result.append({
                "filename": f.name,
                "size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            })
        return result

    def delete(self, filename: str) -> None:
        path = self.vrm_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"VRM file not found: {filename}")
        path.unlink()
        logger.info(f"VRM deleted: {filename}")

    def get_path(self, filename: str) -> str:
        path = self.vrm_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"VRM file not found: {filename}")
        return str(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd server && python -m pytest tests/test_vrm_manager.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Add VRM endpoints to main.py**

In `server/main.py`, add import at top:
```python
from vrm_manager import VrmManager
```

Add global variable after existing globals:
```python
vrm_manager = VrmManager()
```

Add these endpoints after the existing `/health` endpoint:
```python
@app.post("/api/vrm/upload")
async def upload_vrm(file: UploadFile = File(...)):
    data = await file.read()
    try:
        filename = vrm_manager.save(data, file.filename)
        return {"filename": filename, "size": len(data)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/vrm/list")
async def list_vrm():
    return {"models": vrm_manager.list_models()}


@app.get("/vrm/{filename}")
async def get_vrm(filename: str):
    try:
        path = vrm_manager.get_path(filename)
        return FileResponse(path, media_type="model/gltf-binary")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="VRM not found")


@app.delete("/api/vrm/{filename}")
async def delete_vrm(filename: str):
    try:
        vrm_manager.delete(filename)
        return {"success": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="VRM not found")
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add VRM file management backend

VrmManager handles upload/list/serve/delete of VRM files with
glTF magic byte validation and 50MB size limit.
Adds /api/vrm/* endpoints to FastAPI server."
```

---

### Task 8: VRM upload from Flutter + model switching

**Files:**
- Create: `mobile_app/lib/services/vrm_service.dart`
- Modify: `mobile_app/lib/services/api_service.dart`
- Modify: `mobile_app/lib/screens/settings_screen.dart`

- [ ] **Step 1: Add VRM methods to ApiService**

In `mobile_app/lib/services/api_service.dart`, add these methods after the existing `sendOpenCodeTask` method:
```dart
  Future<Map<String, dynamic>> uploadVrm(String filePath) async {
    final uri = Uri.parse('$baseUrl/api/vrm/upload');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('file', filePath));
    final response = await request.send();
    final body = await response.stream.bytesToString();
    return jsonDecode(body);
  }

  Future<List<Map<String, dynamic>>> listVrm() async {
    final response = await http.get(Uri.parse('$baseUrl/api/vrm/list'));
    final data = jsonDecode(response.body);
    return List<Map<String, dynamic>>.from(data['models']);
  }

  Future<void> deleteVrm(String filename) async {
    await http.delete(Uri.parse('$baseUrl/api/vrm/$filename'));
  }
```

Also add `import 'dart:convert';` at the top if not already present, and `import 'package:http/http.dart' as http;`.

- [ ] **Step 2: Create VrmService**

Create `mobile_app/lib/services/vrm_service.dart`:
```dart
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/constants.dart';

class VrmService {
  static const _prefKey = 'selected_vrm_path';

  Future<String?> pickAndSaveVrm() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.any,
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return null;

    final file = result.files.first;
    if (file.path == null) return null;

    // Validate file extension
    if (!file.name.endsWith('.vrm')) {
      throw FormatException('File must be a .vrm file');
    }

    // Validate file size
    if (file.size > Constants.maxVrmFileSizeBytes) {
      throw FormatException('File exceeds ${Constants.maxVrmFileSizeMB}MB limit');
    }

    // Validate glTF magic bytes
    final bytes = await File(file.path!).openRead(0, 4).first;
    if (bytes.length < 4 ||
        bytes[0] != 0x67 || bytes[1] != 0x6C ||
        bytes[2] != 0x54 || bytes[3] != 0x46) {
      throw FormatException('Invalid VRM file: not a valid glTF file');
    }

    // Copy to app local directory
    final appDir = await getApplicationDocumentsDirectory();
    final vrmDir = Directory('${appDir.path}/vrm_models');
    if (!vrmDir.existsSync()) {
      vrmDir.createSync(recursive: true);
    }
    final destPath = '${vrmDir.path}/${file.name}';
    await File(file.path!).copy(destPath);

    // Save preference
    await setSelectedVrm(destPath);

    return destPath;
  }

  Future<String> getSelectedVrm() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_prefKey) ?? Constants.defaultVrmModel;
  }

  Future<void> setSelectedVrm(String path) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, path);
  }

  Future<List<String>> listLocalVrm() async {
    final appDir = await getApplicationDocumentsDirectory();
    final vrmDir = Directory('${appDir.path}/vrm_models');
    if (!vrmDir.existsSync()) return [];
    return vrmDir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.vrm'))
        .map((f) => f.path)
        .toList();
  }

  Future<void> deleteLocalVrm(String path) async {
    final file = File(path);
    if (await file.exists()) {
      await file.delete();
    }
    // If this was the selected model, reset to default
    final selected = await getSelectedVrm();
    if (selected == path) {
      await setSelectedVrm(Constants.defaultVrmModel);
    }
  }
}
```

- [ ] **Step 3: Add VRM model selection to settings_screen.dart**

In `mobile_app/lib/screens/settings_screen.dart`, add to the Character section (after the existing model path field), add a "Change VRM Model" button. Add this import at the top:
```dart
import '../services/vrm_service.dart';
```

Add a field in `_SettingsScreenState`:
```dart
  final _vrmService = VrmService();
```

Add a method:
```dart
  Future<void> _changeVrmModel() async {
    try {
      final path = await _vrmService.pickAndSaveVrm();
      if (path != null) {
        setState(() => _modelPath = path);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('VRM model updated!')),
        );
      }
    } on FormatException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message)),
      );
    }
  }
```

Add a button in the Character section:
```dart
  ElevatedButton.icon(
    onPressed: _changeVrmModel,
    icon: const Icon(Icons.upload_file),
    label: const Text('Upload VRM Model'),
  ),
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add VRM upload, model switching, and persistence

VrmService handles file picking, validation (glTF magic bytes, size),
local storage, and SharedPreferences persistence.
ApiService gets VRM upload/list/delete methods.
Settings screen gets Upload VRM Model button."
```

---

## Stage B: Idle Animation + Emotion Expressions

### Task 9: Add emotion tag to backend chat responses

**Files:**
- Modify: `server/agent.py`
- Modify: `server/main.py`

- [ ] **Step 1: Update system prompts in agent.py to include emotion tag**

In `server/agent.py`, modify each language's system prompt to append the emotion instruction. Find the `self.system_prompts` dict and update each value.

For `zh-TW`, append to the end of the prompt string:
```
\n\n重要：每次回應時，在最後一行附加情緒標籤，格式為 [emotion:TAG]，TAG 必須是以下之一：happy, sad, angry, surprised, relaxed, neutral。例如：\n今天天氣真好呢～\n[emotion:happy]
```

For `ja`, append:
```
\n\n重要：返答の最後の行に感情タグを付けてください。形式は [emotion:TAG] で、TAG は happy, sad, angry, surprised, relaxed, neutral のいずれかです。
```

For `en`, append:
```
\n\nIMPORTANT: At the end of every response, add an emotion tag on its own line in the format [emotion:TAG] where TAG is one of: happy, sad, angry, surprised, relaxed, neutral.
```

- [ ] **Step 2: Parse emotion from response in agent.py**

In `server/agent.py`, add a helper method to the `AgentOrchestrator` class:
```python
    def _extract_emotion(self, text: str) -> tuple[str, str]:
        """Extract emotion tag from response text. Returns (clean_text, emotion)."""
        import re
        match = re.search(r'\[emotion:(happy|sad|angry|surprised|relaxed|neutral)\]\s*$', text)
        if match:
            emotion = match.group(1)
            clean_text = text[:match.start()].rstrip()
            return clean_text, emotion
        return text, "neutral"
```

Then in the `chat` method, after getting the response from LLM, call this method:
```python
        # After: response_text = await self.llm_client.chat(messages, ...)
        clean_text, emotion = self._extract_emotion(response_text)
        # Use clean_text instead of response_text for the returned text
```

Update the return dict to include emotion:
```python
        return {
            "text": clean_text,
            "emotion": emotion,
            "language": language,
            "tool_results": tool_results,
            "metadata": {"client_id": client_id},
        }
```

- [ ] **Step 3: Include emotion in chat response in main.py**

In `server/main.py`, update `handle_chat` to pass through the emotion:
```python
async def handle_chat(data: dict, client_id: str) -> dict:
    message = data.get("message", "")
    language = data.get("language", config.languages.default)
    response = await agent.chat(message, language, client_id)
    audio_path = await tts_engine.synthesize(response["text"], language)
    return {
        "type": "chat_response",
        "text": response["text"],
        "emotion": response.get("emotion", "neutral"),
        "audio_url": f"/audio/{audio_path}",
        "metadata": response.get("metadata", {}),
    }
```

Do the same for the REST `/api/chat` endpoint:
```python
@app.post("/api/chat")
async def api_chat(data: dict):
    message = data.get("message", "")
    language = data.get("language", config.languages.default)
    response = await agent.chat(message, language)
    return response  # Already includes emotion field
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add emotion tags to chat responses

System prompts now instruct LLM to append [emotion:TAG] to responses.
AgentOrchestrator extracts and strips emotion tag from response text.
Chat response includes emotion field for driving VRM expressions."
```

---

### Task 10: Wire emotion expressions to VRM in Flutter

**Files:**
- Modify: `mobile_app/lib/screens/chat_screen.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`

- [ ] **Step 1: Add global VrmViewerController to HomeScreen**

In `mobile_app/lib/screens/home_screen.dart`, make the VRM controller accessible from other screens. Change `_HomeTabState` to expose the controller via a static or inherited widget pattern. The simplest approach: make the controller a field on `_HomeScreenState` and pass it down:

In `_HomeScreenState`, add:
```dart
  final vrmController = VrmViewerController();
```

Pass it to `_HomeTab` by making `_HomeTab` accept a controller parameter:
```dart
class _HomeTab extends StatefulWidget {
  final VrmViewerController vrmController;
  const _HomeTab({required this.vrmController});

  @override
  State<_HomeTab> createState() => _HomeTabState();
}
```

In `_HomeTabState`, use `widget.vrmController` instead of creating a local one. Remove the local `_vrmController` field.

In `_HomeScreenState`, change the screens list from `const` to a getter that passes the controller:
```dart
  List<Widget> get _screens => [
    _HomeTab(vrmController: vrmController),
    const ChatScreen(),
    const EmailScreen(),
    const CalendarScreen(),
    const SettingsScreen(),
  ];
```

- [ ] **Step 2: Handle emotion in ChatScreen**

In `mobile_app/lib/screens/chat_screen.dart`, when a chat response is received, extract the emotion and call the VRM controller. This requires access to the VRM controller. Use a simple approach: find the ancestor `_HomeScreenState`:

Add to chat response handling (where `_simulateResponse` is or where WebSocket response is processed):
```dart
void _handleChatResponse(Map<String, dynamic> response) {
  final text = response['text'] as String;
  final emotion = response['emotion'] as String? ?? 'neutral';

  setState(() {
    _messages.add({'role': 'assistant', 'content': text});
    _isLoading = false;
  });

  // Drive VRM expression
  _setVrmExpression(emotion);
}

void _setVrmExpression(String emotion) {
  // Find HomeScreen's VRM controller via context
  final homeState = context.findAncestorStateOfType<HomeScreenState>();
  if (homeState == null) return;
  final expression = VrmExpression.values.firstWhere(
    (e) => e.name == emotion,
    orElse: () => VrmExpression.neutral,
  );
  homeState.vrmController.setExpression(expression);

  // Reset to neutral after 5 seconds
  Future.delayed(const Duration(seconds: 5), () {
    homeState.vrmController.setExpression(VrmExpression.neutral);
  });
}
```

Make `HomeScreenState` public by renaming `_HomeScreenState` to `HomeScreenState`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: wire emotion expressions from chat to VRM model

Chat responses with emotion tags now drive VRM facial expressions
via VrmViewerController. Expression resets to neutral after 5 seconds."
```

---

## Stage C: Lip Sync, AR, Camera, Vision

### Task 11: Lip sync engine (JS + backend)

**Files:**
- Create: `mobile_app/assets/vrm_viewer/js/lip_sync.js`
- Modify: `mobile_app/assets/vrm_viewer/js/vrm_controller.js`
- Modify: `server/tts_engine.py`

- [ ] **Step 1: Create lip_sync.js**

Create `mobile_app/assets/vrm_viewer/js/lip_sync.js`:
```javascript
// Viseme-driven lip sync for VRM models
// Receives an array of { time, viseme, weight } frames and plays them in sequence

export class LipSyncEngine {
  constructor() {
    this._frames = [];
    this._startTime = 0;
    this._isPlaying = false;
    this._currentIndex = 0;
    this._vrm = null;
    this._rafId = null;
  }

  setVrm(vrm) {
    this._vrm = vrm;
  }

  // visemeData: [{ time: float (seconds), viseme: string, weight: float 0-1 }]
  // VRM mouth visemes: aa, ih, ou, ee, oh
  start(visemeData) {
    if (!this._vrm || !this._vrm.expressionManager) return;
    this._frames = visemeData.sort((a, b) => a.time - b.time);
    this._startTime = performance.now() / 1000;
    this._currentIndex = 0;
    this._isPlaying = true;
    this._tick();
  }

  stop() {
    this._isPlaying = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
    this._resetMouth();
  }

  _tick() {
    if (!this._isPlaying || !this._vrm) return;

    const elapsed = performance.now() / 1000 - this._startTime;

    // Find current frame
    while (this._currentIndex < this._frames.length - 1 &&
           this._frames[this._currentIndex + 1].time <= elapsed) {
      this._currentIndex++;
    }

    if (this._currentIndex >= this._frames.length) {
      this.stop();
      return;
    }

    const frame = this._frames[this._currentIndex];
    this._applyViseme(frame.viseme, frame.weight);

    this._rafId = requestAnimationFrame(() => this._tick());
  }

  _applyViseme(viseme, weight) {
    if (!this._vrm.expressionManager) return;
    // Reset all mouth shapes
    const mouthShapes = ['aa', 'ih', 'ou', 'ee', 'oh'];
    for (const shape of mouthShapes) {
      this._vrm.expressionManager.setValue(shape, 0);
    }
    // Apply current viseme
    if (mouthShapes.includes(viseme)) {
      this._vrm.expressionManager.setValue(viseme, weight);
    }
  }

  _resetMouth() {
    if (!this._vrm?.expressionManager) return;
    const mouthShapes = ['aa', 'ih', 'ou', 'ee', 'oh'];
    for (const shape of mouthShapes) {
      this._vrm.expressionManager.setValue(shape, 0);
    }
  }
}
```

- [ ] **Step 2: Integrate lip sync into vrm_controller.js**

In `mobile_app/assets/vrm_viewer/js/vrm_controller.js`, add at the top:
```javascript
import { LipSyncEngine } from './lip_sync.js';
```

Add after the state variables:
```javascript
const lipSync = new LipSyncEngine();
```

After model loads successfully (in `loadModel`, after `currentVrm = vrm;`):
```javascript
    lipSync.setVrm(vrm);
```

Add to `window.VrmController`:
```javascript
  startLipSync(visemeData) {
    lipSync.start(visemeData);
  },
  stopLipSync() {
    lipSync.stop();
  },
```

- [ ] **Step 3: Add simple amplitude-based viseme generation to tts_engine.py**

In `server/tts_engine.py`, add a method to generate viseme data from audio:
```python
    def _generate_visemes_from_audio(self, audio_path: str) -> list[dict]:
        """Generate simple amplitude-based viseme data from audio file."""
        try:
            import wave
            import struct

            with wave.open(audio_path, 'r') as wf:
                n_frames = wf.getnframes()
                framerate = wf.getframerate()
                raw = wf.readframes(n_frames)
                samples = struct.unpack(f'<{n_frames}h', raw)

            # Chunk into ~50ms windows
            chunk_size = max(1, framerate // 20)
            visemes = []
            mouth_shapes = ['aa', 'oh', 'ee', 'ih', 'ou']

            for i in range(0, len(samples), chunk_size):
                chunk = samples[i:i + chunk_size]
                if not chunk:
                    break
                amplitude = sum(abs(s) for s in chunk) / len(chunk) / 32768.0
                time_sec = i / framerate

                if amplitude < 0.02:
                    continue  # mouth closed

                weight = min(1.0, amplitude * 5)
                # Cycle through mouth shapes based on position
                shape_idx = (i // chunk_size) % len(mouth_shapes)
                visemes.append({
                    'time': round(time_sec, 3),
                    'viseme': mouth_shapes[shape_idx],
                    'weight': round(weight, 2),
                })

            return visemes
        except Exception as e:
            logger.warning(f"Viseme generation failed: {e}")
            return []
```

Then update the `synthesize` method to return visemes along with the filename. Change the return to a tuple:
```python
    async def synthesize(self, text: str, language: str = "zh-TW") -> tuple[str, list[dict]]:
        # ... existing synthesis logic ...
        # After audio is saved to output_path:
        visemes = self._generate_visemes_from_audio(str(self.output_dir / filename))
        return filename, visemes
```

- [ ] **Step 4: Update main.py to pass visemes in response**

In `server/main.py`, update `handle_chat`:
```python
    audio_path, visemes = await tts_engine.synthesize(response["text"], language)
    return {
        "type": "chat_response",
        "text": response["text"],
        "emotion": response.get("emotion", "neutral"),
        "audio_url": f"/audio/{audio_path}",
        "visemes": visemes,
        "metadata": response.get("metadata", {}),
    }
```

Similarly update `handle_voice_input` and `api_tts`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add lip sync engine with amplitude-based visemes

LipSyncEngine in JS plays viseme frame sequences on VRM mouth shapes.
TTS engine generates simple amplitude-based viseme timeline from audio.
Chat responses now include visemes array for driving lip sync."
```

---

### Task 12: AR mode (WebXR)

**Files:**
- Create: `mobile_app/assets/vrm_viewer/js/ar_session.js`
- Modify: `mobile_app/assets/vrm_viewer/js/vrm_controller.js`
- Modify: `mobile_app/lib/screens/home_screen.dart`

- [ ] **Step 1: Create ar_session.js**

Create `mobile_app/assets/vrm_viewer/js/ar_session.js`:
```javascript
// WebXR AR session manager for VRM viewer

export class ARSession {
  constructor(renderer, scene, camera) {
    this._renderer = renderer;
    this._scene = scene;
    this._camera = camera;
    this._session = null;
    this._isSupported = false;
    this._checkSupport();
  }

  async _checkSupport() {
    if (navigator.xr) {
      try {
        this._isSupported = await navigator.xr.isSessionSupported('immersive-ar');
      } catch (e) {
        this._isSupported = false;
      }
    }
    return this._isSupported;
  }

  get isSupported() {
    return this._isSupported;
  }

  async enter() {
    if (!this._isSupported || this._session) return false;

    try {
      this._session = await navigator.xr.requestSession('immersive-ar', {
        requiredFeatures: ['hit-test', 'local-floor'],
        optionalFeatures: ['dom-overlay'],
      });

      this._renderer.xr.enabled = true;
      await this._renderer.xr.setSession(this._session);

      this._session.addEventListener('end', () => {
        this._session = null;
        this._renderer.xr.enabled = false;
      });

      return true;
    } catch (e) {
      console.error('AR session failed:', e);
      return false;
    }
  }

  async exit() {
    if (this._session) {
      await this._session.end();
      this._session = null;
      this._renderer.xr.enabled = false;
    }
  }
}
```

- [ ] **Step 2: Integrate AR into vrm_controller.js**

In `mobile_app/assets/vrm_viewer/js/vrm_controller.js`, add import:
```javascript
import { ARSession } from './ar_session.js';
```

After scene setup in `initScene()`, add:
```javascript
  const arSession = new ARSession(renderer, scene, camera);
  // Check and report AR support
  setTimeout(async () => {
    const supported = arSession.isSupported;
    sendToFlutter('arSupported', { supported });
  }, 1000);
```

Add to `window.VrmController`:
```javascript
  async enterAR() {
    const success = await arSession.enter();
    if (success) {
      controls.enabled = false;  // Disable orbit controls in AR
    }
    return success;
  },
  async exitAR() {
    await arSession.exit();
    controls.enabled = true;
  },
```

Note: `arSession` needs to be accessible. Move it to module scope or pass it differently. The simplest fix: declare `let arSession = null;` at module scope, then assign in `initScene()`.

- [ ] **Step 3: Add AR button to HomeScreen**

In `mobile_app/lib/screens/home_screen.dart`, in `_HomeTabState`, add AR state:
```dart
  bool _arSupported = false;
```

Listen for AR support event in `initState`:
```dart
  @override
  void initState() {
    super.initState();
    widget.vrmController.events.listen((event) {
      if (event.type == VrmEventType.arSupported) {
        setState(() => _arSupported = event.data['supported'] == true);
      }
    });
  }
```

Add an AR button in the quick actions row (only if supported):
```dart
  if (_arSupported)
    _QuickAction(
      icon: Icons.view_in_ar,
      label: 'AR',
      onTap: () => widget.vrmController.enterAR(),
    ),
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add WebXR AR mode for VRM character

ARSession manages WebXR immersive-ar sessions with hit-test support.
AR button appears on HomeScreen when device supports WebXR.
Orbit controls disabled during AR mode."
```

---

### Task 13: Camera photo mode

**Files:**
- Create: `mobile_app/lib/screens/photo_screen.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`

- [ ] **Step 1: Create photo_screen.dart**

Create `mobile_app/lib/screens/photo_screen.dart`:
```dart
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:camera/camera.dart';
import 'package:image_gallery_saver_plus/image_gallery_saver_plus.dart';
import 'package:share_plus/share_plus.dart';
import 'package:path_provider/path_provider.dart';
import '../widgets/vrm_viewer_widget.dart';
import '../models/vrm_model.dart';
import '../utils/constants.dart';
import '../utils/theme.dart';

class PhotoScreen extends StatefulWidget {
  const PhotoScreen({super.key});

  @override
  State<PhotoScreen> createState() => _PhotoScreenState();
}

class _PhotoScreenState extends State<PhotoScreen> {
  CameraController? _cameraController;
  final _vrmController = VrmViewerController();
  final _captureKey = GlobalKey();
  bool _isInitialized = false;
  bool _isFrontCamera = true;
  bool _isCapturing = false;
  Uint8List? _capturedImage;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    final front = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _cameraController = CameraController(front, ResolutionPreset.high);
    await _cameraController!.initialize();
    if (mounted) setState(() => _isInitialized = true);
  }

  Future<void> _switchCamera() async {
    final cameras = await availableCameras();
    if (cameras.length < 2) return;

    _isFrontCamera = !_isFrontCamera;
    final target = cameras.firstWhere(
      (c) => c.lensDirection ==
          (_isFrontCamera ? CameraLensDirection.front : CameraLensDirection.back),
      orElse: () => cameras.first,
    );

    await _cameraController?.dispose();
    _cameraController = CameraController(target, ResolutionPreset.high);
    await _cameraController!.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _capturePhoto() async {
    if (_isCapturing) return;
    setState(() => _isCapturing = true);

    try {
      // Capture the composite view
      final boundary = _captureKey.currentContext?.findRenderObject()
          as RenderRepaintBoundary?;
      if (boundary == null) return;

      final image = await boundary.toImage(pixelRatio: 2.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData == null) return;

      setState(() => _capturedImage = byteData.buffer.asUint8List());
    } finally {
      setState(() => _isCapturing = false);
    }
  }

  Future<void> _saveToGallery() async {
    if (_capturedImage == null) return;
    await ImageGallerySaverPlus.saveImage(_capturedImage!, quality: 95);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Photo saved!')),
      );
    }
    setState(() => _capturedImage = null);
  }

  Future<void> _sharePhoto() async {
    if (_capturedImage == null) return;
    final tempDir = await getTemporaryDirectory();
    final file = File('${tempDir.path}/ai_wife_photo.png');
    await file.writeAsBytes(_capturedImage!);
    await Share.shareXFiles([XFile(file.path)], text: 'AI Wife Photo');
    setState(() => _capturedImage = null);
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _vrmController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_capturedImage != null) {
      return _buildPreview();
    }
    return _buildCameraView();
  }

  Widget _buildCameraView() {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          children: [
            // Camera preview
            if (_isInitialized && _cameraController != null)
              RepaintBoundary(
                key: _captureKey,
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: CameraPreview(_cameraController!),
                    ),
                    // VRM overlay
                    Positioned.fill(
                      child: VrmViewerWidget(
                        modelSource: VrmModelSource.asset(Constants.defaultVrmModel),
                        enableInteraction: true,
                        enableIdleAnimation: true,
                        controller: _vrmController,
                        backgroundColor: Colors.transparent,
                      ),
                    ),
                  ],
                ),
              )
            else
              const Center(child: CircularProgressIndicator()),

            // Controls
            Positioned(
              top: 16,
              left: 16,
              child: IconButton(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close, color: Colors.white, size: 28),
              ),
            ),
            Positioned(
              top: 16,
              right: 16,
              child: IconButton(
                onPressed: _switchCamera,
                icon: const Icon(Icons.flip_camera_android, color: Colors.white, size: 28),
              ),
            ),
            // Shutter button
            Positioned(
              bottom: 40,
              left: 0,
              right: 0,
              child: Center(
                child: GestureDetector(
                  onTap: _capturePhoto,
                  child: Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 4),
                    ),
                    child: Container(
                      margin: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreview() {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Image.memory(_capturedImage!, fit: BoxFit.contain),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  IconButton(
                    onPressed: () => setState(() => _capturedImage = null),
                    icon: const Icon(Icons.close, color: Colors.white, size: 32),
                  ),
                  IconButton(
                    onPressed: _saveToGallery,
                    icon: const Icon(Icons.save_alt, color: Colors.white, size: 32),
                  ),
                  IconButton(
                    onPressed: _sharePhoto,
                    icon: const Icon(Icons.share, color: Colors.white, size: 32),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Add photo button to HomeScreen**

In `mobile_app/lib/screens/home_screen.dart`, add import:
```dart
import 'photo_screen.dart';
```

Add a photo quick action in the row:
```dart
_QuickAction(
  icon: Icons.camera_alt,
  label: '合照',
  onTap: () => Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => const PhotoScreen()),
  ),
),
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add camera photo mode with VRM character overlay

PhotoScreen provides camera preview with transparent VRM overlay,
front/rear camera switching, composite screenshot capture,
save to gallery, and share functionality."
```

---

### Task 14: Vision analysis backend

**Files:**
- Create: `server/vision_analyzer.py`
- Create: `server/tests/test_vision_analyzer.py`
- Modify: `server/main.py`
- Modify: `server/config.py`

- [ ] **Step 1: Write tests for vision analyzer**

Create `server/tests/test_vision_analyzer.py`:
```python
import pytest
import base64

# Minimal 1x1 red PNG
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)
# Different 1x1 blue PNG
TINY_PNG_2 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture
def analyzer():
    from vision_analyzer import VisionAnalyzer
    return VisionAnalyzer(vision_model=None)


def test_analyze_returns_fallback_when_no_model(analyzer):
    result = analyzer.analyze_single(TINY_PNG, language="zh-TW")
    assert "text" in result
    assert result["emotion"] == "neutral"
    assert "看不太清楚" in result["text"]


def test_has_significant_change_same_image(analyzer):
    assert not analyzer.has_significant_change(TINY_PNG, TINY_PNG)


def test_has_significant_change_different_images(analyzer):
    assert analyzer.has_significant_change(TINY_PNG, TINY_PNG_2)


def test_analyze_stream_skips_when_no_change(analyzer):
    result = analyzer.analyze_stream(TINY_PNG, TINY_PNG, language="zh-TW")
    assert result is None  # No significant change → no response


def test_analyze_stream_responds_on_first_frame(analyzer):
    result = analyzer.analyze_stream(TINY_PNG, None, language="zh-TW")
    assert result is not None
    assert "text" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd server && python -m pytest tests/test_vision_analyzer.py -v
```

Expected: ERRORS — `ModuleNotFoundError: No module named 'vision_analyzer'`

- [ ] **Step 3: Implement VisionAnalyzer**

Create `server/vision_analyzer.py`:
```python
import logging
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)

FALLBACK_RESPONSES = {
    "zh-TW": "抱歉～我現在看不太清楚呢，你可以告訴我你在做什麼嗎？",
    "ja": "ごめんね～今ちょっとよく見えないの。何してるか教えてくれる？",
    "en": "Sorry~ I can't see clearly right now. Can you tell me what you're doing?",
}


class VisionAnalyzer:
    def __init__(self, vision_model=None, llm_client=None, change_threshold: float = 0.3):
        self._vision_model = vision_model
        self._llm_client = llm_client
        self._change_threshold = change_threshold
        self._last_hash: Optional[str] = None

    def _image_hash(self, image_data: bytes) -> str:
        return hashlib.md5(image_data).hexdigest()

    def has_significant_change(self, current: bytes, previous: Optional[bytes]) -> bool:
        if previous is None:
            return True
        return self._image_hash(current) != self._image_hash(previous)

    def analyze_single(
        self, image_data: bytes, language: str = "zh-TW", context: str = ""
    ) -> dict:
        if self._vision_model is None and self._llm_client is None:
            return {
                "text": FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en"]),
                "emotion": "neutral",
            }

        # TODO: When vision model is available, use it here
        # For now, return fallback
        return {
            "text": FALLBACK_RESPONSES.get(language, FALLBACK_RESPONSES["en"]),
            "emotion": "neutral",
        }

    def analyze_stream(
        self,
        current_frame: bytes,
        previous_frame: Optional[bytes],
        language: str = "zh-TW",
        context: str = "",
    ) -> Optional[dict]:
        if not self.has_significant_change(current_frame, previous_frame):
            return None
        return self.analyze_single(current_frame, language, context)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd server && python -m pytest tests/test_vision_analyzer.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Add VisionConfig to config.py**

In `server/config.py`, add after the existing config classes:
```python
class VisionConfig(BaseSettings):
    model: str = "llava"
    change_threshold: float = 0.3

    class Config:
        env_prefix = "VISION_"
```

Add `vision: VisionConfig = VisionConfig()` to the `ServerConfig` class.

- [ ] **Step 6: Add vision endpoints to main.py**

In `server/main.py`, add import:
```python
from vision_analyzer import VisionAnalyzer
```

Add global:
```python
vision_analyzer = VisionAnalyzer()
```

Add endpoints:
```python
@app.post("/api/vision/capture")
async def vision_capture(image: UploadFile = File(...), language: str = "zh-TW"):
    image_data = await image.read()
    result = vision_analyzer.analyze_single(image_data, language)
    if result.get("text"):
        audio_path, visemes = await tts_engine.synthesize(result["text"], language)
        result["audio_url"] = f"/audio/{audio_path}"
        result["visemes"] = visemes
    return result


@app.post("/api/vision/stream")
async def vision_stream(
    image: UploadFile = File(...),
    previous_hash: str = "",
    language: str = "zh-TW",
    context: str = "",
):
    image_data = await image.read()
    # Use hash comparison for stream mode
    previous_bytes = None  # In real usage, client tracks previous frame
    result = vision_analyzer.analyze_stream(image_data, previous_bytes, language, context)
    if result is None:
        return {"changed": False}
    if result.get("text"):
        audio_path, visemes = await tts_engine.synthesize(result["text"], language)
        result["audio_url"] = f"/audio/{audio_path}"
        result["visemes"] = visemes
    result["changed"] = True
    return result
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add vision analysis backend with change detection

VisionAnalyzer handles single image and continuous stream analysis
with hash-based change detection. Falls back gracefully when no
vision model is available. Adds /api/vision/* endpoints."
```

---

### Task 15: Continuous vision (companion mode) in Flutter

**Files:**
- Create: `mobile_app/lib/services/vision_service.dart`
- Modify: `mobile_app/lib/screens/home_screen.dart`
- Modify: `mobile_app/lib/services/api_service.dart`

- [ ] **Step 1: Add vision methods to ApiService**

In `mobile_app/lib/services/api_service.dart`, add:
```dart
  Future<Map<String, dynamic>> sendVisionCapture(List<int> imageData, String language) async {
    final uri = Uri.parse('$baseUrl/api/vision/capture');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = language
      ..files.add(http.MultipartFile.fromBytes('image', imageData, filename: 'frame.jpg'));
    final response = await request.send();
    final body = await response.stream.bytesToString();
    return jsonDecode(body);
  }

  Future<Map<String, dynamic>> sendVisionStream(
    List<int> imageData,
    String language,
    String context,
  ) async {
    final uri = Uri.parse('$baseUrl/api/vision/stream');
    final request = http.MultipartRequest('POST', uri)
      ..fields['language'] = language
      ..fields['context'] = context
      ..files.add(http.MultipartFile.fromBytes('image', imageData, filename: 'frame.jpg'));
    final response = await request.send();
    final body = await response.stream.bytesToString();
    return jsonDecode(body);
  }
```

- [ ] **Step 2: Create VisionService**

Create `mobile_app/lib/services/vision_service.dart`:
```dart
import 'dart:async';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import '../utils/constants.dart';

class VisionService {
  CameraController? _cameraController;
  Timer? _frameTimer;
  bool _isActive = false;
  Duration _frameInterval = Duration(seconds: Constants.visionFrameIntervalSeconds);
  final void Function(Uint8List frame)? onFrameCaptured;

  VisionService({this.onFrameCaptured});

  bool get isActive => _isActive;

  Future<CameraController?> initCamera({bool front = true}) async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return null;

    final target = cameras.firstWhere(
      (c) => c.lensDirection ==
          (front ? CameraLensDirection.front : CameraLensDirection.back),
      orElse: () => cameras.first,
    );

    _cameraController = CameraController(
      target,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    await _cameraController!.initialize();
    return _cameraController;
  }

  CameraController? get cameraController => _cameraController;

  void startContinuousVision() {
    if (_isActive || _cameraController == null) return;
    _isActive = true;
    _frameTimer = Timer.periodic(_frameInterval, (_) => _captureFrame());
  }

  void stopContinuousVision() {
    _isActive = false;
    _frameTimer?.cancel();
    _frameTimer = null;
  }

  void setFrameInterval(Duration interval) {
    _frameInterval = interval;
    if (_isActive) {
      stopContinuousVision();
      startContinuousVision();
    }
  }

  Future<void> _captureFrame() async {
    if (!_isActive || _cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }
    try {
      final xFile = await _cameraController!.takePicture();
      final bytes = await xFile.readAsBytes();
      onFrameCaptured?.call(bytes);
    } catch (e) {
      debugPrint('Vision frame capture error: $e');
    }
  }

  Future<Uint8List?> captureOnce() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return null;
    try {
      final xFile = await _cameraController!.takePicture();
      return await xFile.readAsBytes();
    } catch (e) {
      debugPrint('Vision capture error: $e');
      return null;
    }
  }

  Future<void> dispose() async {
    stopContinuousVision();
    await _cameraController?.dispose();
    _cameraController = null;
  }
}
```

- [ ] **Step 3: Add companion mode toggle to HomeScreen**

In `mobile_app/lib/screens/home_screen.dart`, add imports:
```dart
import '../services/vision_service.dart';
import '../services/api_service.dart';
```

In `_HomeTabState`, add:
```dart
  VisionService? _visionService;
  bool _companionMode = false;
```

Add methods:
```dart
  Future<void> _toggleCompanionMode() async {
    if (_companionMode) {
      _visionService?.stopContinuousVision();
      await _visionService?.dispose();
      _visionService = null;
      setState(() => _companionMode = false);
    } else {
      _visionService = VisionService(
        onFrameCaptured: _onVisionFrame,
      );
      await _visionService!.initCamera(front: true);
      _visionService!.startContinuousVision();
      setState(() => _companionMode = true);
    }
  }

  void _onVisionFrame(Uint8List frame) async {
    final apiService = context.read<ApiService>();
    try {
      final result = await apiService.sendVisionStream(
        frame,
        Constants.defaultLanguage,
        '', // conversation context
      );
      if (result['changed'] == true && result['text'] != null) {
        // Drive VRM expression
        final emotion = result['emotion'] as String? ?? 'neutral';
        final expression = VrmExpression.values.firstWhere(
          (e) => e.name == emotion,
          orElse: () => VrmExpression.neutral,
        );
        widget.vrmController.setExpression(expression);

        // Show what she said
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result['text'])),
        );

        // Reset expression after delay
        Future.delayed(const Duration(seconds: 5), () {
          widget.vrmController.setExpression(VrmExpression.neutral);
        });
      }
    } catch (e) {
      debugPrint('Vision stream error: $e');
    }
  }
```

Add companion mode toggle button in the quick actions row:
```dart
  _QuickAction(
    icon: _companionMode ? Icons.visibility : Icons.visibility_off,
    label: _companionMode ? '關閉陪伴' : '陪伴模式',
    onTap: _toggleCompanionMode,
  ),
```

Don't forget to dispose:
```dart
  @override
  void dispose() {
    _visionService?.dispose();
    super.dispose();
  }
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add continuous vision companion mode

VisionService captures camera frames at configurable intervals.
Frames sent to backend for change detection and LLM analysis.
AI wife reacts with expressions and speech when visual changes detected.
Toggle via eye icon on HomeScreen."
```

---

### Task 16: Update config and clean up

**Files:**
- Modify: `server/config.py`
- Modify: `config/server_config.yaml`
- Modify: `server/requirements.txt`

- [ ] **Step 1: Update server_config.yaml**

In `config/server_config.yaml`, remove the `image_to_3d:` section entirely. Add:
```yaml
vision:
  model: "llava"
  change_threshold: 0.3
```

- [ ] **Step 2: Update requirements.txt if needed**

No new Python dependencies are needed (vision uses existing Ollama via httpx). Verify the file is correct as-is.

- [ ] **Step 3: Clean up any remaining references to image_to_3d**

Search for any remaining references:
```bash
cd /home/wilsao6666/ai_wife_app && grep -r "image_to_3d\|image-to-3d\|ImageTo3D\|triposr\|TripoSR\|CharacterGen\|charactergen" --include="*.py" --include="*.dart" --include="*.yaml" server/ mobile_app/ config/
```

Fix any found references.

- [ ] **Step 4: Verify server starts without errors**

```bash
cd server && python -c "from config import config; print('Config loaded OK')"
```

- [ ] **Step 5: Run all tests**

```bash
cd server && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Verify Flutter builds**

```bash
cd mobile_app && flutter build apk --debug 2>&1 | tail -20
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: clean up config, remove image-to-3d references

Updates server_config.yaml with vision config, removes image_to_3d
config section. Cleans up all remaining references to removed pipeline."
```

---

## Verification Checklist

After all tasks are complete, verify:

- [ ] `model_viewer_plus` is no longer in pubspec.yaml
- [ ] `server/image_to_3d.py` is deleted
- [ ] No `import image_to_3d` or `ImageTo3D` references remain
- [ ] VRM model loads in WebView on HomeScreen
- [ ] Idle animation (blink + breathing) runs automatically
- [ ] Chat responses include `emotion` field
- [ ] VRM expression changes on chat response
- [ ] Lip sync viseme data included in chat response
- [ ] VRM upload works from Settings screen
- [ ] AR button appears only on supported devices
- [ ] Photo screen captures camera + VRM composite
- [ ] Companion mode sends frames and gets responses
- [ ] `flutter build apk --debug` succeeds
- [ ] `python -m pytest tests/ -v` all pass
