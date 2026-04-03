class HeartbeatJob {
  final String id;
  final String cron;
  final String action;
  final bool enabled;

  HeartbeatJob({
    required this.id,
    required this.cron,
    required this.action,
    required this.enabled,
  });

  factory HeartbeatJob.fromJson(Map<String, dynamic> json) {
    return HeartbeatJob(
      id: json['id'] as String? ?? '',
      cron: json['cron'] as String? ?? '',
      action: json['action'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'cron': cron,
      'action': action,
      'enabled': enabled,
    };
  }
}
