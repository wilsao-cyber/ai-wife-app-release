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
            if (_isInitialized && _cameraController != null)
              RepaintBoundary(
                key: _captureKey,
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: CameraPreview(_cameraController!),
                    ),
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
