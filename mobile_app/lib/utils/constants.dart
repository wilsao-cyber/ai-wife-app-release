class Constants {
  static const String serverUrl = 'http://192.168.1.100:8000';
  static const String wsUrl = 'ws://192.168.1.100:8000';
  static const String defaultLanguage = 'zh-TW';
  static const List<String> supportedLanguages = ['zh-TW', 'ja', 'en'];
  static const int maxChatHistory = 50;
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration requestTimeout = Duration(seconds: 60);
}
