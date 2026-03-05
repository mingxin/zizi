-- zizi 用户体系数据库 Schema
-- 适用于 SQLite (开发) / MySQL (生产)

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- SQLite语法，MySQL改为: id BIGINT PRIMARY KEY AUTO_INCREMENT
    phone VARCHAR(20) UNIQUE NOT NULL,     -- 手机号，唯一
    password_hash VARCHAR(255) NOT NULL,   -- bcrypt哈希密码
    nickname VARCHAR(50),                  -- 用户昵称（可选）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

-- 学习记录表（与原有功能关联）
CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    char VARCHAR(10) NOT NULL,             -- 学习的汉字
    library_id VARCHAR(50),                -- 所属字库
    action_type VARCHAR(50) NOT NULL,      -- photo_capture, char_viewed, story_played, etc.
    context TEXT,                          -- JSON格式的上下文信息
    duration_sec INTEGER DEFAULT 0,        -- 停留时长
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_learning_user_time ON learning_records(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_learning_char ON learning_records(user_id, char);

-- 用户设置表（云端同步设置）
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    preferred_voice VARCHAR(50) DEFAULT 'serena',
    current_library VARCHAR(50) DEFAULT 'infant',
    settings_json TEXT,                    -- 其他设置JSON
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 汉字掌握度表（用于学习进度追踪）
CREATE TABLE IF NOT EXISTS char_mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    char VARCHAR(10) NOT NULL,
    mastery_level INTEGER DEFAULT 0,       -- 0:初学 1:了解 2:熟悉 3:掌握
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, char),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mastery_user ON char_mastery(user_id);
