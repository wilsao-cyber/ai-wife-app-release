import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../services/chat_provider.dart';
import '../utils/constants.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/voice_input_button.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = false;
  String _language = Constants.defaultLanguage;
  String _mode = 'chat';
  Map<String, dynamic>? _pendingPlan;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _loadLanguage();
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    final lang = prefs.getString('language') ?? Constants.defaultLanguage;
    if (mounted) {
      setState(() => _language = lang);
    }
  }

  void _sendMessage(String text) {
    if (text.trim().isEmpty) return;
    final now = DateTime.now().toIso8601String();
    final chatProvider = context.read<ChatProvider>();
    chatProvider.addMessage({'role': 'user', 'content': text, 'timestamp': now});
    setState(() {
      _isLoading = true;
      _pendingPlan = null;
    });
    _controller.clear();
    _sendToServer(text);
  }

  Future<void> _sendToServer(String text) async {
    try {
      final apiService = context.read<ApiService>();
      final result = await apiService.sendChat(text, _language);
      _handleChatResponse(result);
    } catch (e) {
      final chatProvider = context.read<ChatProvider>();
      final now = DateTime.now().toIso8601String();
      chatProvider.addMessage({
        'role': 'assistant',
        'content': Constants.getError('send_failed', _language),
        'timestamp': now,
      });
      setState(() => _isLoading = false);
    }
  }

  void _handleChatResponse(Map<String, dynamic> response) {
    final text = response['text'] as String? ?? response['content'] as String? ?? '';
    final emotion = response['emotion'] as String? ?? 'neutral';
    final mode = response['mode'] as String? ?? 'chat';
    final awaitingConfirm = response['awaiting_confirmation'] as bool? ?? false;

    final chatProvider = context.read<ChatProvider>();
    final now = DateTime.now().toIso8601String();

    if (awaitingConfirm && response['tool_calls'] != null) {
      setState(() {
        _mode = 'assist';
        _pendingPlan = response;
        _isLoading = false;
      });
      chatProvider.addMessage({
        'role': 'assistant',
        'content': text,
        'timestamp': now,
        'isPlan': true,
      });
    } else {
      chatProvider.addMessage({
        'role': 'assistant',
        'content': text,
        'timestamp': now,
      });
      chatProvider.setExpression(emotion);
      setState(() {
        _mode = mode;
        _isLoading = false;
      });

      Future.delayed(const Duration(seconds: 5), () {
        if (mounted) {
          chatProvider.setExpression('neutral');
        }
      });
    }
  }

  Future<void> _confirmPlan() async {
    if (_pendingPlan == null) return;
    setState(() => _isLoading = true);

    try {
      final apiService = context.read<ApiService>();
      final clientId = apiService.currentClientId.isNotEmpty
          ? apiService.currentClientId
          : 'mobile_client';
      final result = await apiService.confirmPlan(clientId);

      final text = result['text'] as String? ?? result['content'] as String? ?? '執行完成';
      final emotion = result['emotion'] as String? ?? 'neutral';
      final chatProvider = context.read<ChatProvider>();
      final now = DateTime.now().toIso8601String();
      chatProvider.addMessage({
        'role': 'assistant',
        'content': text,
        'timestamp': now,
        'isToolResult': true,
      });
      chatProvider.setExpression(emotion);

      setState(() {
        _pendingPlan = null;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(Constants.getError('send_failed', _language))),
        );
      }
    }
  }

  Future<void> _denyPlan() async {
    if (_pendingPlan == null) return;
    setState(() => _isLoading = true);

    try {
      final apiService = context.read<ApiService>();
      final clientId = apiService.currentClientId.isNotEmpty
          ? apiService.currentClientId
          : 'mobile_client';
      final result = await apiService.denyPlan(clientId, _language);

      final text = result['text'] as String? ?? '已取消';
      final chatProvider = context.read<ChatProvider>();
      final now = DateTime.now().toIso8601String();
      chatProvider.addMessage({
        'role': 'assistant',
        'content': text,
        'timestamp': now,
        'isNotice': true,
      });

      setState(() {
        _pendingPlan = null;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('與老婆聊天'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _mode = _mode == 'chat' ? 'assist' : 'chat';
                });
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _mode == 'assist' ? Colors.orange : Colors.green,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _mode == 'chat' ? '聊天' : '協助',
                  style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Consumer<ChatProvider>(
              builder: (context, chatProvider, child) {
                final messages = chatProvider.messages;
                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  reverse: true,
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final msg = messages[messages.length - 1 - index];
                    if (msg['isPlan'] == true) {
                      return _buildPlanCard(msg);
                    }
                    if (msg['isNotice'] == true) {
                      return _buildNoticeBubble(msg);
                    }
                    if (msg['isToolResult'] == true) {
                      return _buildToolResultBubble(msg);
                    }
                    final timestamp = msg['timestamp'] != null
                        ? DateTime.tryParse(msg['timestamp']) ?? DateTime.now()
                        : DateTime.now();
                    return ChatBubble(
                      text: msg['content'] ?? '',
                      isUser: msg['role'] == 'user',
                      timestamp: timestamp,
                    );
                  },
                );
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: CircularProgressIndicator(),
            ),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildPlanCard(Map<String, dynamic> msg) {
    final toolCalls = (msg['tool_calls'] as List?) ?? [];
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.orange.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb, color: Colors.orange, size: 18),
              const SizedBox(width: 6),
              Text(
                '執行計畫',
                style: TextStyle(color: Colors.orange, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(msg['content'] ?? '', style: const TextStyle(fontSize: 14)),
          if (toolCalls.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...toolCalls.map<Widget>((tc) {
              final tool = tc as Map<String, dynamic>;
              return Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  '• ${tool['name']}: ${tool['arguments']}',
                  style: TextStyle(fontSize: 12, color: Colors.grey[400]),
                ),
              );
            }).toList(),
          ],
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: _isLoading ? null : _denyPlan,
                child: const Text('取消', style: TextStyle(color: Colors.red)),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _isLoading ? null : _confirmPlan,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                ),
                child: const Text('確認'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNoticeBubble(Map<String, dynamic> msg) {
    return Center(
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.grey.withOpacity(0.15),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          msg['content'] ?? '',
          style: TextStyle(fontSize: 12, color: Colors.grey[500]),
        ),
      ),
    );
  }

  Widget _buildToolResultBubble(Map<String, dynamic> msg) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.blue.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Icon(Icons.check_circle, color: Colors.blue, size: 18),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              msg['content'] ?? '',
              style: const TextStyle(fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(8),
      child: Row(
        children: [
          VoiceInputButton(
            language: _language,
            onResult: _sendMessage,
          ),
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: '輸入訊息...',
                border: OutlineInputBorder(),
              ),
              onSubmitted: _sendMessage,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.send),
            onPressed: () => _sendMessage(_controller.text),
          ),
        ],
      ),
    );
  }
}
