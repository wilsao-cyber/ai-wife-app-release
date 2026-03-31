ai_wife_app/
├── server/                      # Python Local Server
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Server configuration
│   ├── llm_client.py            # Ollama/Local LLM client
│   ├── tts_engine.py            # CosyVoice/GPT-SoVITS TTS
│   ├── stt_engine.py            # Whisper STT
│   ├── image_to_3d.py           # TripoSR/CRM image to 3D
│   ├── agent.py                 # LangChain agent orchestrator
│   ├── websocket_manager.py     # WebSocket connection manager
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── email_tool.py        # Gmail/IMAP email management
│   │   ├── calendar_tool.py     # Google Calendar management
│   │   ├── web_search_tool.py   # Web search (SearXNG/Tavily)
│   │   ├── file_ops_tool.py     # File operations
│   │   └── opencode_tool.py     # OpenCode auto-development
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── gmail_oauth.py       # Gmail OAuth2
│   │   └── google_calendar_oauth.py  # Google Calendar OAuth2
│   ├── models/
│   │   ├── __init__.py
│   │   ├── message.py           # Chat message models
│   │   └── character.py         # 3D character models
│   ├── services/
│   │   ├── __init__.py
│   │   └── notification_service.py  # Push notifications
│   └── utils/
│       ├── __init__.py
│       └── audio_utils.py       # Audio processing utilities
│
├── mobile_app/                  # Flutter App
│   ├── lib/
│   │   ├── main.dart            # App entry point
│   │   ├── app.dart             # App configuration
│   │   ├── screens/
│   │   │   ├── home_screen.dart           # 3D character home
│   │   │   ├── chat_screen.dart           # Chat interface
│   │   │   ├── email_screen.dart          # Email management
│   │   │   ├── calendar_screen.dart       # Calendar management
│   │   │   ├── settings_screen.dart       # Settings
│   │   │   └── voice_settings_screen.dart # Voice/TTS settings
│   │   ├── widgets/
│   │   │   ├── model_viewer_3d.dart       # 3D model viewer
│   │   │   ├── chat_bubble.dart           # Chat message bubble
│   │   │   ├── voice_input_button.dart    # Voice input button
│   │   │   ├── email_list_item.dart       # Email list item
│   │   │   └── calendar_event_card.dart   # Calendar event card
│   │   ├── services/
│   │   │   ├── api_service.dart           # HTTP/WebSocket API
│   │   │   ├── email_service.dart         # Email service
│   │   │   ├── calendar_service.dart      # Calendar service
│   │   │   ├── tts_service.dart           # TTS service
│   │   │   ├── stt_service.dart           # STT service
│   │   │   ├── file_service.dart          # File management
│   │   │   └── notification_service.dart  # Push notifications
│   │   ├── models/
│   │   │   ├── message.dart               # Chat message model
│   │   │   ├── character.dart             # Character model
│   │   │   ├── email.dart                 # Email model
│   │   │   └── calendar_event.dart        # Calendar event model
│   │   └── utils/
│   │       ├── constants.dart             # App constants
│   │       └── theme.dart                 # App theme
│   ├── assets/
│   │   ├── images/
│   │   ├── models/
│   │   └── voice_samples/
│   ├── test/
│   └── pubspec.yaml
│
├── config/
│   ├── server_config.yaml       # Server configuration
│   └── credentials.json         # OAuth credentials template
│
├── scripts/
│   ├── setup.sh                 # Environment setup script
│   ├── start_server.sh          # Start local server
│   └── train_voice.sh           # Voice training script
│
├── docs/
│   └── architecture.md          # Architecture documentation
│
├── voice_samples/               # Voice training samples
│   └── .gitkeep
│
└── README.md
