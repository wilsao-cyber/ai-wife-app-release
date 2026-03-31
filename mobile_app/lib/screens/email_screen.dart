import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../models/email.dart';
import '../widgets/email_list_item.dart';
import '../utils/theme.dart';

class EmailScreen extends StatefulWidget {
  const EmailScreen({super.key});

  @override
  State<EmailScreen> createState() => _EmailScreenState();
}

class _EmailScreenState extends State<EmailScreen> {
  List<EmailListItem> _emails = [];
  bool _isLoading = true;
  bool _unreadOnly = false;

  @override
  void initState() {
    super.initState();
    _loadEmails();
  }

  Future<void> _loadEmails() async {
    setState(() => _isLoading = true);
    final apiService = context.read<ApiService>();
    final result = await apiService.sendEmailAction('list', {
      'limit': 20,
      'unread_only': _unreadOnly,
    });
    if (result['emails'] != null) {
      setState(() {
        _emails = (result['emails'] as List)
            .map((e) => EmailListItem.fromJson(e))
            .toList();
        _isLoading = false;
      });
    } else {
      setState(() {
        _emails = _getMockEmails();
        _isLoading = false;
      });
    }
  }

  List<EmailListItem> _getMockEmails() {
    return [
      EmailListItem(
        id: '1',
        subject: '老公，今天的行程提醒',
        from: 'AI Wife <wife@ai.com>',
        date: '2026-03-31 09:00',
        snippet: '今天下午 3 點有會議，記得準備資料喔～',
        isUnread: true,
      ),
      EmailListItem(
        id: '2',
        subject: '工作進度報告',
        from: 'Boss <boss@company.com>',
        date: '2026-03-30 18:30',
        snippet: '請確認本週交付項目...',
      ),
      EmailListItem(
        id: '3',
        subject: '週末約會計畫',
        from: 'AI Wife <wife@ai.com>',
        date: '2026-03-30 12:00',
        snippet: '老公～週末想去哪裡玩呢？我幫你查了天氣...',
        isUnread: true,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Email'),
        actions: [
          IconButton(
            icon: Icon(_unreadOnly ? Icons.mark_email_read : Icons.mark_email_unread),
            onPressed: () {
              setState(() => _unreadOnly = !_unreadOnly);
              _loadEmails();
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadEmails,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _emails.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.email_outlined, size: 64, color: AppTheme.textSecondaryColor),
                      const SizedBox(height: 16),
                      Text('沒有郵件', style: TextStyle(color: AppTheme.textSecondaryColor)),
                    ],
                  ),
                )
              : ListView.builder(
                  itemCount: _emails.length,
                  itemBuilder: (context, index) {
                    final email = _emails[index];
                    return EmailListItemWidget(email: email);
                  },
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: _composeEmail,
        child: const Icon(Icons.edit),
      ),
    );
  }

  void _composeEmail() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _ComposeEmailSheet(),
    );
  }
}

class _ComposeEmailSheet extends StatefulWidget {
  const _ComposeEmailSheet();

  @override
  State<_ComposeEmailSheet> createState() => _ComposeEmailSheetState();
}

class _ComposeEmailSheetState extends State<_ComposeEmailSheet> {
  final _toController = TextEditingController();
  final _subjectController = TextEditingController();
  final _bodyController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
        left: 16,
        right: 16,
        top: 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(controller: _toController, decoration: const InputDecoration(labelText: '收件人')),
          TextField(controller: _subjectController, decoration: const InputDecoration(labelText: '主旨')),
          TextField(
            controller: _bodyController,
            decoration: const InputDecoration(labelText: '內容'),
            maxLines: 5,
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('郵件已發送')),
              );
            },
            child: const Text('發送'),
          ),
        ],
      ),
    );
  }
}
