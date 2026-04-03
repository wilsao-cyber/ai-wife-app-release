import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../models/vrm_model.dart';

/// Copies bundled vrm_viewer assets to a temp directory and starts a local
/// HTTP server so that ES module imports work correctly in the WebView.
class _LocalAssetServer {
  HttpServer? _server;
  String? _baseUrl;

  String? get baseUrl => _baseUrl;

  Future<void> start() async {
    if (_server != null) return;

    // Copy assets to a temp directory
    final tempDir = await getTemporaryDirectory();
    final assetDir = Directory('${tempDir.path}/vrm_viewer');
    await assetDir.create(recursive: true);
    await Directory('${assetDir.path}/js').create(recursive: true);
    await Directory('${assetDir.path}/utils').create(recursive: true);

    // List of asset files to copy
    const assets = [
      'assets/vrm_viewer/vrm_viewer.html',
      'assets/vrm_viewer/js/vrm_controller.js',
      'assets/vrm_viewer/js/lip_sync.js',
      'assets/vrm_viewer/js/ar_session.js',
      'assets/vrm_viewer/js/three.module.min.js',
      'assets/vrm_viewer/js/three-vrm.module.min.js',
      'assets/vrm_viewer/js/OrbitControls.js',
      'assets/vrm_viewer/js/GLTFLoader.js',
      'assets/vrm_viewer/utils/BufferGeometryUtils.js',
    ];

    for (final asset in assets) {
      try {
        final data = await rootBundle.load(asset);
        final relativePath = asset.replaceFirst('assets/vrm_viewer/', '');
        final file = File('${assetDir.path}/$relativePath');
        await file.writeAsBytes(data.buffer.asUint8List(), flush: true);
      } catch (e) {
        debugPrint('Failed to copy asset $asset: $e');
      }
    }

    // Also copy model files
    try {
      final modelsDir = Directory('${tempDir.path}/models');
      if (!await modelsDir.exists()) {
        await modelsDir.create(recursive: true);
      }
      final modelData = await rootBundle.load('assets/models/character.vrm');
      await File('${modelsDir.path}/character.vrm')
          .writeAsBytes(modelData.buffer.asUint8List(), flush: true);
    } catch (e) {
      debugPrint('Failed to copy model: $e');
    }

    _server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    _baseUrl = 'http://localhost:${_server!.port}';

    _server!.listen((request) async {
      var path = request.uri.path;
      if (path == '/') path = '/vrm_viewer.html';

      // Determine the file path
      String filePath;
      if (path.startsWith('/models/')) {
        filePath = '${tempDir.path}$path';
      } else {
        filePath = '${assetDir.path}$path';
      }

      final file = File(filePath);
      if (await file.exists()) {
        final ext = path.split('.').last.toLowerCase();
        final contentType = switch (ext) {
          'html' => 'text/html',
          'js' => 'application/javascript',
          'json' => 'application/json',
          'vrm' || 'glb' || 'gltf' => 'model/gltf-binary',
          'png' => 'image/png',
          _ => 'application/octet-stream',
        };

        request.response
          ..headers.set('Content-Type', contentType)
          ..headers.set('Access-Control-Allow-Origin', '*');
        await request.response.addStream(file.openRead());
        await request.response.close();
      } else {
        request.response.statusCode = 404;
        request.response.write('Not found: $path');
        await request.response.close();
      }
    });
  }

  Future<void> stop() async {
    await _server?.close();
    _server = null;
    _baseUrl = null;
  }
}

// ---------------------------------------------------------------------------
// VrmViewerController
// ---------------------------------------------------------------------------

class VrmViewerController {
  WebViewController? _webViewController;

  final StreamController<VrmEvent> _eventController =
      StreamController<VrmEvent>.broadcast();

  bool isARSupported = false;

  /// Broadcast stream of events sent from the JavaScript side.
  Stream<VrmEvent> get events => _eventController.stream;

  // -------------------------------------------------------------------------
  // Internal helpers
  // -------------------------------------------------------------------------

  /// Called by [_VrmViewerWidgetState] once the WebViewController is ready.
  void _attach(WebViewController controller) {
    _webViewController = controller;
  }

  /// Called by [_VrmViewerWidgetState] when a message arrives on FlutterBridge.
  void _handleMessage(String message) {
    try {
      final json = jsonDecode(message) as Map<String, dynamic>;
      final event = VrmEvent.fromJson(json);
      if (event.type == VrmEventType.arSupported) {
        isARSupported = event.data['supported'] == true;
      }
      if (!_eventController.isClosed) {
        _eventController.add(event);
      }
    } catch (_) {
      // Silently ignore malformed messages from JS.
    }
  }

  /// Runs arbitrary JavaScript in the WebView, if attached.
  Future<void> _runJs(String script) async {
    if (_webViewController == null) return;
    await _webViewController!.runJavaScript(script);
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /// Tells the VRM controller to load a model from [url].
  Future<void> loadModel(String url) async {
    final escaped = url.replaceAll("'", "\\'");
    await _runJs("VrmController.loadModel('$escaped');");
  }

  /// Sets a facial expression with an optional [intensity] (0.0–1.0).
  Future<void> setExpression(
    VrmExpression expression, {
    double intensity = 1.0,
  }) async {
    final name = expression.name; // e.g. 'happy'
    await _runJs("VrmController.setExpression('$name', $intensity);");
  }

  /// Starts the built-in idle animation loop.
  Future<void> startIdleAnimation() async {
    await _runJs('VrmController.startIdleAnimation();');
  }

  /// Stops the idle animation loop.
  Future<void> stopIdleAnimation() async {
    await _runJs('VrmController.stopIdleAnimation();');
  }

  /// Plays a lip-sync sequence described by [frames].
  Future<void> startLipSync(List<VisemeFrame> frames) async {
    final encoded = jsonEncode(frames.map((f) => f.toJson()).toList());
    await _runJs('VrmController.startLipSync($encoded);');
  }

  /// Stops any running lip-sync animation.
  Future<void> stopLipSync() async {
    await _runJs('VrmController.stopLipSync();');
  }

  /// Resets the character to a neutral expression.
  Future<void> resetPose() async {
    await setExpression(VrmExpression.neutral, intensity: 1.0);
  }

  /// Repositions the camera.
  Future<void> setCameraPosition(double x, double y, double z) async {
    await _runJs('VrmController.setCameraPosition($x, $y, $z);');
  }

  /// Enables or disables auto-rotation of the model.
  Future<void> setAutoRotate(bool enabled) async {
    await _runJs('VrmController.setAutoRotate($enabled);');
  }

  /// Requests a PNG frame capture from the renderer.
  Future<void> captureFrame() async {
    await _runJs('VrmController.captureFrame();');
  }

  /// Enters WebXR AR mode.
  Future<void> enterAR() async {
    await _runJs('VrmController.enterAR();');
  }

  /// Exits WebXR AR mode.
  Future<void> exitAR() async {
    await _runJs('VrmController.exitAR();');
  }

  /// Disposes the controller, shutting down the JS side and closing the stream.
  Future<void> dispose() async {
    await _runJs('VrmController.dispose();');
    await _eventController.close();
    _webViewController = null;
  }
}

// ---------------------------------------------------------------------------
// VrmViewerWidget
// ---------------------------------------------------------------------------

class VrmViewerWidget extends StatefulWidget {
  /// Source of the VRM model to display.
  final VrmModelSource modelSource;

  /// Allow the user to interact with the 3-D view (pan/zoom).
  final bool enableInteraction;

  /// Automatically rotate the model around the Y axis.
  final bool autoRotate;

  /// Play the built-in idle animation once the model is loaded.
  final bool enableIdleAnimation;

  /// Background color of the WebView viewport.
  final Color backgroundColor;

  /// Called when the renderer signals it is ready.
  final VoidCallback? onReady;

  /// Called with an error message when loading fails.
  final ValueChanged<String>? onError;

  /// Optional external controller. If omitted, the widget creates its own.
  final VrmViewerController? controller;

  const VrmViewerWidget({
    super.key,
    required this.modelSource,
    this.enableInteraction = true,
    this.autoRotate = false,
    this.enableIdleAnimation = true,
    this.backgroundColor = Colors.black,
    this.onReady,
    this.onError,
    this.controller,
  });

  @override
  State<VrmViewerWidget> createState() => _VrmViewerWidgetState();
}

class _VrmViewerWidgetState extends State<VrmViewerWidget> {
  late final VrmViewerController _controller;
  late final WebViewController _webViewController;
  final _LocalAssetServer _assetServer = _LocalAssetServer();

  bool _loading = true;
  String? _errorMessage;

  StreamSubscription<VrmEvent>? _eventSubscription;

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  @override
  void initState() {
    super.initState();

    _controller = widget.controller ?? VrmViewerController();

    _webViewController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(widget.backgroundColor)
      ..addJavaScriptChannel(
        'FlutterBridge',
        onMessageReceived: (JavaScriptMessage message) {
          _controller._handleMessage(message.message);
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (_) => _onPageFinished(),
          onWebResourceError: (WebResourceError error) {
            _setError('WebView error: ${error.description}');
          },
        ),
      );

    _controller._attach(_webViewController);
    _eventSubscription = _controller.events.listen(_handleEvent);

    // Start the local asset server and load the page via HTTP
    _startAndLoad();
  }

  Future<void> _startAndLoad() async {
    try {
      await _assetServer.start();
      final url = '${_assetServer.baseUrl}/vrm_viewer.html';
      await _webViewController.loadRequest(Uri.parse(url));
    } catch (e) {
      _setError('Failed to start asset server: $e');
    }
  }

  @override
  void didUpdateWidget(VrmViewerWidget oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Reload the model if the source changed after the initial build.
    if (oldWidget.modelSource.type != widget.modelSource.type ||
        oldWidget.modelSource.path != widget.modelSource.path) {
      _controller.loadModel(_resolveModelUrl(widget.modelSource));
    }
  }

  @override
  void dispose() {
    _eventSubscription?.cancel();
    _assetServer.stop();
    // Only dispose the controller if we created it internally.
    if (widget.controller == null) {
      _controller.dispose();
    }
    super.dispose();
  }

  // -------------------------------------------------------------------------
  // Event handling
  // -------------------------------------------------------------------------

  void _handleEvent(VrmEvent event) {
    switch (event.type) {
      case VrmEventType.ready:
        widget.onReady?.call();
        _controller.loadModel(_resolveModelUrl(widget.modelSource));
        if (widget.autoRotate) {
          _controller.setAutoRotate(true);
        }

      case VrmEventType.modelLoaded:
        if (mounted) {
          setState(() => _loading = false);
        }
        if (widget.enableIdleAnimation) {
          _controller.startIdleAnimation();
        }

      case VrmEventType.error:
        final msg = (event.data['message'] as String?) ?? 'Unknown error';
        _setError(msg);

      case VrmEventType.arSupported:
      case VrmEventType.animationEnd:
      case VrmEventType.frameCaptured:
        // Handled by external listeners via the events stream.
        break;
    }
  }

  void _onPageFinished() {
    // Page has loaded; wait for the JS 'ready' event before doing anything.
  }

  void _setError(String message) {
    widget.onError?.call(message);
    if (mounted) {
      setState(() {
        _loading = false;
        _errorMessage = message;
      });
    }
  }

  // -------------------------------------------------------------------------
  // URL resolution
  // -------------------------------------------------------------------------

  String _resolveModelUrl(VrmModelSource source) {
    switch (source.type) {
      case VrmModelSourceType.asset:
        final filename = source.path.split('/').last;
        final base = _assetServer.baseUrl;
        if (base != null) {
          return '$base/models/$filename';
        }
        return '../models/$filename';

      case VrmModelSourceType.file:
        return 'file://${source.path}';

      case VrmModelSourceType.network:
        return source.path;
    }
  }

  // -------------------------------------------------------------------------
  // Retry
  // -------------------------------------------------------------------------

  void _retry() {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    _webViewController.reload();
  }

  // -------------------------------------------------------------------------
  // Build
  // -------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // The WebView is always present so the JS context survives state changes.
        WebViewWidget(
          controller: _webViewController,
          gestureRecognizers: const <Factory<OneSequenceGestureRecognizer>>{},
        ),

        // Loading overlay
        if (_loading && _errorMessage == null)
          const _LoadingOverlay(),

        // Error overlay with retry button
        if (_errorMessage != null)
          _ErrorOverlay(
            message: _errorMessage!,
            onRetry: _retry,
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Private UI helpers
// ---------------------------------------------------------------------------

class _LoadingOverlay extends StatelessWidget {
  const _LoadingOverlay();

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black54,
      child: const Center(
        child: CircularProgressIndicator(
          color: Color(0xFFFF69B4), // hotpink – matches the HTML spinner
        ),
      ),
    );
  }
}

class _ErrorOverlay extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorOverlay({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black87,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Colors.redAccent, size: 48),
              const SizedBox(height: 12),
              Text(
                message,
                style: const TextStyle(color: Colors.white70, fontSize: 14),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFF69B4),
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
