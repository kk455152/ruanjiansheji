CREATE TABLE IF NOT EXISTS Daily_Stats (
    stat_date DATE NOT NULL COMMENT '统计日期',
    total_play_count INT NOT NULL DEFAULT 0 COMMENT '当日总播放次数',
    unique_song_count INT NOT NULL DEFAULT 0 COMMENT '当日播放过的去重歌曲数',
    unique_user_count INT NOT NULL DEFAULT 0 COMMENT '当日活跃用户数',
    unique_device_count INT NOT NULL DEFAULT 0 COMMENT '当日活跃设备数',
    total_play_duration_seconds BIGINT NOT NULL DEFAULT 0 COMMENT '当日累计播放时长，单位秒',
    avg_play_duration_seconds DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '单次平均播放时长，单位秒',
    hottest_song_id VARCHAR(100) DEFAULT NULL COMMENT '当日最热歌曲 ID',
    hottest_song_name VARCHAR(255) DEFAULT NULL COMMENT '当日最热歌曲名',
    hottest_artist VARCHAR(255) DEFAULT NULL COMMENT '当日最热歌曲歌手',
    hottest_play_count INT NOT NULL DEFAULT 0 COMMENT '当日最热歌曲播放次数',
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '统计生成时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP COMMENT '统计更新时间',
    PRIMARY KEY (stat_date),
    KEY idx_daily_stats_hottest_song_id (hottest_song_id),
    KEY idx_daily_stats_generated_at (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
