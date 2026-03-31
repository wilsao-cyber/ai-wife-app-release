import 'package:flutter/material.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';

class ModelViewer3D extends StatelessWidget {
  final String? modelUrl;
  final String? vrmUrl;
  final bool enableInteraction;
  final VoidCallback? onTap;

  const ModelViewer3D({
    super.key,
    this.modelUrl,
    this.vrmUrl,
    this.enableInteraction = true,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final modelPath = vrmUrl ?? modelUrl ?? 'assets/models/character.vrm';
    return GestureDetector(
      onTap: onTap,
      child: ModelViewer(
        src: modelPath,
        alt: 'AI Wife 3D Model',
        autoRotate: true,
        disableZoom: !enableInteraction,
        cameraControls: enableInteraction,
        backgroundColor: const Color(0x00000000),
        shadowIntensity: 0.5,
        environmentImage: 'neutral',
        loading: Loading.eager,
        reveal: Reveal.auto,
        debugLogging: true,
        innerModelViewerHtml: '<script type="module" src="model-viewer.min.js" defer></script>',
      ),
    );
  }
}
