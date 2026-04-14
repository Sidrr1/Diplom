-- ============================================
-- EdgeTools Unified Database Schema
-- ============================================

-- ============================================
-- SMART NOTES (бывший Todo)
-- ============================================
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_context TEXT NOT NULL DEFAULT 'global',  -- 'chrome.exe', 'code.exe', 'global'
    title TEXT,
    content TEXT NOT NULL,
    priority INTEGER DEFAULT 3,                   -- 1 (красный), 2 (жёлтый), 3 (зелёный)
    category TEXT,                                -- работа, личное, срочно
    color TEXT DEFAULT '#fef3c7',                 -- цвет стикера
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 250,
    height INTEGER DEFAULT 200,
    collapsed INTEGER DEFAULT 0,                  -- 0 = развёрнут, 1 = свёрнут
    is_base INTEGER DEFAULT 0,                    -- 1 = базовая заметка (нельзя удалить)
    deadline TEXT,                                -- ISO формат
    reminder_at TEXT,                             -- ISO формат
    created_at TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0                  -- порядок отображения
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_notes_app_context ON notes(app_context);
CREATE INDEX IF NOT EXISTS idx_notes_completed ON notes(completed);
CREATE INDEX IF NOT EXISTS idx_notes_reminder ON notes(reminder_at);

-- ============================================
-- WINDOW CONTEXTS (для Smart Notes)
-- ============================================
CREATE TABLE IF NOT EXISTS window_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_name TEXT NOT NULL UNIQUE,            -- 'chrome.exe', 'code.exe'
    display_name TEXT NOT NULL,                   -- 'Google Chrome', 'VS Code'
    icon_path TEXT,                               -- путь к иконке
    last_active TEXT,                             -- последняя активность
    notes_count INTEGER DEFAULT 0                 -- кол-во заметок
);

-- Начальные контексты
INSERT OR IGNORE INTO window_contexts (process_name, display_name, notes_count) VALUES
('global', 'Общие заметки', 1),
('chrome.exe', 'Google Chrome', 0),
('firefox.exe', 'Firefox', 0),
('msedge.exe', 'Microsoft Edge', 0),
('code.exe', 'VS Code', 0),
('pycharm64.exe', 'PyCharm', 0),
('notepad.exe', 'Блокнот', 0),
('explorer.exe', 'Проводник', 0);

-- ============================================
-- FILE SORTER
-- ============================================
CREATE TABLE IF NOT EXISTS sorter_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL,                      -- 'extension', 'keyword'
    pattern TEXT NOT NULL,                        -- '.jpg', 'invoice'
    destination TEXT NOT NULL,                    -- путь к папке
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sorter_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    destination_path TEXT NOT NULL,
    rule_id INTEGER,
    moved_at TEXT NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES sorter_rules(id)
);

-- ============================================
-- IMAGE ENHANCER
-- ============================================
CREATE TABLE IF NOT EXISTS enhancer_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    enhanced_path TEXT NOT NULL,
    settings_used TEXT,                           -- JSON с настройками
    processing_time REAL,                         -- секунды
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enhancer_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    settings TEXT NOT NULL,                       -- JSON
    is_default INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- ============================================
-- PLAYER
-- ============================================
CREATE TABLE IF NOT EXISTS player_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    duration REAL,                                -- секунды
    last_position REAL,                           -- секунды
    played_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_playlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (playlist_id) REFERENCES player_playlists(id) ON DELETE CASCADE
);

-- ============================================
-- OCR
-- ============================================
CREATE TABLE IF NOT EXISTS ocr_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screenshot_path TEXT,
    recognized_text TEXT NOT NULL,
    language TEXT DEFAULT 'rus+eng',
    created_at TEXT NOT NULL
);

-- ============================================
-- GLOBAL SETTINGS
-- ============================================
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    module TEXT NOT NULL,                         -- 'player', 'notes', 'sorter', 'global'
    updated_at TEXT NOT NULL
);
