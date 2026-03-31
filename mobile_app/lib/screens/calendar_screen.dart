import 'package:flutter/material.dart';
import 'package:table_calendar/table_calendar.dart';
import '../models/calendar_event.dart';
import '../utils/theme.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({super.key});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  List<CalendarEvent> _events = [];

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
    _loadEvents();
  }

  void _loadEvents() {
    setState(() {
      _events = _getMockEvents();
    });
  }

  List<CalendarEvent> _getMockEvents() {
    return [
      CalendarEvent(
        id: '1',
        title: '團隊會議',
        startTime: DateTime.now().add(const Duration(hours: 2)),
        endTime: DateTime.now().add(const Duration(hours: 3)),
        location: '會議室 A',
        description: '本週進度報告',
      ),
      CalendarEvent(
        id: '2',
        title: '和老婆的約會',
        startTime: DateTime.now().add(const Duration(days: 1, hours: 10)),
        endTime: DateTime.now().add(const Duration(days: 1, hours: 14)),
        location: '信義區',
        description: '週末約會計畫',
      ),
    ];
  }

  List<CalendarEvent> _getEventsForDay(DateTime day) {
    return _events.where((event) {
      return event.startTime.year == day.year &&
          event.startTime.month == day.month &&
          event.startTime.day == day.day;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Calendar'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _addEvent,
          ),
        ],
      ),
      body: Column(
        children: [
          TableCalendar<CalendarEvent>(
            firstDay: DateTime.utc(2020, 1, 1),
            lastDay: DateTime.utc(2030, 12, 31),
            focusedDay: _focusedDay,
            calendarFormat: _calendarFormat,
            selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
            onDaySelected: (selectedDay, focusedDay) {
              setState(() {
                _selectedDay = selectedDay;
                _focusedDay = focusedDay;
              });
            },
            onFormatChanged: (format) {
              setState(() => _calendarFormat = format);
            },
            eventLoader: _getEventsForDay,
            calendarStyle: CalendarStyle(
              todayDecoration: BoxDecoration(
                color: AppTheme.primaryColor,
                shape: BoxShape.circle,
              ),
              selectedDecoration: BoxDecoration(
                color: AppTheme.secondaryColor,
                shape: BoxShape.circle,
              ),
              markerDecoration: BoxDecoration(
                color: AppTheme.accentColor,
                shape: BoxShape.circle,
              ),
            ),
          ),
          const Divider(),
          Expanded(
            child: _getEventsForDay(_selectedDay ?? _focusedDay).isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.event_note, size: 48, color: AppTheme.textSecondaryColor),
                        const SizedBox(height: 8),
                        Text(
                          '這天沒有行程',
                          style: TextStyle(color: AppTheme.textSecondaryColor),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    itemCount: _getEventsForDay(_selectedDay ?? _focusedDay).length,
                    itemBuilder: (context, index) {
                      final event = _getEventsForDay(_selectedDay ?? _focusedDay)[index];
                      return _EventCard(event: event);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _addEvent() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _AddEventSheet(),
    );
  }
}

class _EventCard extends StatelessWidget {
  final CalendarEvent event;

  const _EventCard({required this.event});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        leading: Container(
          width: 4,
          height: 40,
          decoration: BoxDecoration(
            color: AppTheme.primaryColor,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        title: Text(event.title),
        subtitle: Text(
          '${_formatTime(event.startTime)} - ${_formatTime(event.endTime)}${event.location != null ? ' · ${event.location}' : ''}',
        ),
        trailing: IconButton(
          icon: const Icon(Icons.delete_outline),
          onPressed: () {},
        ),
      ),
    );
  }

  String _formatTime(DateTime time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }
}

class _AddEventSheet extends StatefulWidget {
  const _AddEventSheet();

  @override
  State<_AddEventSheet> createState() => _AddEventSheetState();
}

class _AddEventSheetState extends State<_AddEventSheet> {
  final _titleController = TextEditingController();
  final _locationController = TextEditingController();
  final _descController = TextEditingController();
  DateTime _startTime = DateTime.now();

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
          TextField(controller: _titleController, decoration: const InputDecoration(labelText: '行程標題')),
          TextField(controller: _locationController, decoration: const InputDecoration(labelText: '地點')),
          TextField(controller: _descController, decoration: const InputDecoration(labelText: '描述'), maxLines: 3),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('行程已新增')),
              );
            },
            child: const Text('新增行程'),
          ),
        ],
      ),
    );
  }
}
