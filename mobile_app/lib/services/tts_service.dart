import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

class TTSService {
  final FlutterTts _flutterTts = FlutterTts();
  String _language = 'zh-TW';

  TTSService() {
    _flutterTts.setLanguage(_language);
    _flutterTts.setSpeechRate(0.5);
    _flutterTts.setPitch(1.2);
  }

  Future<void> setLanguage(String lang) async {
    _language = lang;
    await _flutterTts.setLanguage(lang);
  }

  Future<void> speak(String text) async {
    await _flutterTts.speak(text);
  }

  Future<void> stop() async {
    await _flutterTts.stop();
  }
}

class STTService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isInitialized = false;

  Future<bool> initialize() async {
    _isInitialized = await _speech.initialize();
    return _isInitialized;
  }

  Future<void> listen({Function(String)? onResult}) async {
    if (!_isInitialized) await initialize();
    _speech.listen(
      onResult: (result) {
        onResult?.call(result.recognizedWords);
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
    );
  }

  Future<void> stop() async {
    await _speech.stop();
  }
}
