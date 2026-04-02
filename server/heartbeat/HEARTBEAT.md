# Heartbeat Schedule

## morning_greeting
- cron: "0 8 * * *"
- action: "根據天氣和用戶今天的行程，生成一句早安問候"
- enabled: true

## event_reminder
- cron: "*/30 * * * *"
- action: "檢查未來 30 分鐘內的行程，如果有則提醒用戶"
- enabled: true

## weekly_summary
- cron: "0 20 * * 0"
- action: "總結本週的對話重點和完成的事項"
- enabled: true
