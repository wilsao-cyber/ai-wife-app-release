import 'package:flutter/material.dart';
import '../models/email.dart';
import '../utils/theme.dart';

class EmailListItemWidget extends StatelessWidget {
  final EmailListItem email;

  const EmailListItemWidget({super.key, required this.email});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: email.isUnread ? AppTheme.primaryColor : AppTheme.cardColor,
        child: Text(
          email.from[0].toUpperCase(),
          style: TextStyle(
            color: email.isUnread ? Colors.white : AppTheme.textSecondaryColor,
          ),
        ),
      ),
      title: Text(
        email.subject,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          fontWeight: email.isUnread ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      subtitle: Text(
        email.snippet,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            _formatDate(email.date),
            style: TextStyle(fontSize: 12, color: AppTheme.textSecondaryColor),
          ),
          if (email.isUnread)
            Container(
              margin: const EdgeInsets.only(top: 4),
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                color: AppTheme.primaryColor,
                shape: BoxShape.circle,
              ),
            ),
        ],
      ),
      onTap: () {},
    );
  }

  String _formatDate(String date) {
    try {
      final dt = DateTime.parse(date);
      return '${dt.month}/${dt.day}';
    } catch (e) {
      return date;
    }
  }
}
