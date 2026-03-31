import 'package:flutter/material.dart';

class VoiceInputButton extends StatefulWidget {
  final Function(String text)? onResult;

  const VoiceInputButton({super.key, this.onResult});

  @override
  State<VoiceInputButton> createState() => _VoiceInputButtonState();
}

class _VoiceInputButtonState extends State<VoiceInputButton> {
  bool _isListening = false;

  void _toggleListening() {
    setState(() => _isListening = !_isListening);
    if (_isListening) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('語音輸入尚未連線到伺服器')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: _toggleListening,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _isListening ? Colors.red : Colors.pink,
          boxShadow: _isListening
              ? [
                  BoxShadow(
                    color: Colors.red.withOpacity(0.5),
                    blurRadius: 16,
                    spreadRadius: 4,
                  ),
                ]
              : [],
        ),
        child: Icon(
          _isListening ? Icons.mic : Icons.mic_none,
          color: Colors.white,
          size: 28,
        ),
      ),
    );
  }
}
