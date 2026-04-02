class Memory {
  final int id;
  final String content;
  final String category;
  final double importance;
  final DateTime createdAt;
  final DateTime lastAccessed;
  final int accessCount;

  Memory({
    required this.id,
    required this.content,
    required this.category,
    required this.importance,
    required this.createdAt,
    required this.lastAccessed,
    required this.accessCount,
  });

  factory Memory.fromJson(Map<String, dynamic> json) {
    return Memory(
      id: json['id'] as int? ?? 0,
      content: json['content'] as String? ?? '',
      category: json['category'] as String? ?? '',
      importance: (json['importance'] as num?)?.toDouble() ?? 0.5,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
      lastAccessed: json['last_accessed'] != null
          ? DateTime.tryParse(json['last_accessed']) ?? DateTime.now()
          : DateTime.now(),
      accessCount: json['access_count'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'content': content,
      'category': category,
      'importance': importance,
      'created_at': createdAt.toIso8601String(),
      'last_accessed': lastAccessed.toIso8601String(),
      'access_count': accessCount,
    };
  }
}
