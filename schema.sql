-- Users' bank accounts table
CREATE TABLE IF NOT EXISTS bank_accounts (
    user_id BIGINT PRIMARY KEY,
    wallet INTEGER NOT NULL DEFAULT 50,
    bank INTEGER NOT NULL DEFAULT 0,
    last_work TIMESTAMP
);

-- Jobs configuration
CREATE TABLE IF NOT EXISTS jobs (
    name VARCHAR(50) PRIMARY KEY,
    base_pay INTEGER NOT NULL,
    bonus_chance DECIMAL(5,2) NOT NULL,
    bonus_amount INTEGER NOT NULL,
    cost INTEGER NOT NULL
);

-- Users' jobs
CREATE TABLE IF NOT EXISTS user_jobs (
    user_id BIGINT NOT NULL,
    job_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, job_name),
    FOREIGN KEY (job_name) REFERENCES jobs(name) ON DELETE CASCADE
);

-- User levels
CREATE TABLE IF NOT EXISTS user_levels (
    user_id BIGINT PRIMARY KEY,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 0,
    total_messages INTEGER NOT NULL DEFAULT 0,
    last_message TIMESTAMP
);

-- Voice channel activity
CREATE TABLE IF NOT EXISTS voice_activity (
    user_id BIGINT PRIMARY KEY,
    voice_time INTEGER NOT NULL DEFAULT 0
);

-- LastFM usernames
CREATE TABLE IF NOT EXISTS lastfm_users (
    user_id BIGINT PRIMARY KEY,
    lastfm_username VARCHAR(100) NOT NULL
);

-- Initial jobs data
INSERT INTO jobs (name, base_pay, bonus_chance, bonus_amount, cost) VALUES
('McDonalds-Employee', 75, 0.2, 50, 0),
('Artist', 300, 0.25, 250, 1000),
('Teacher', 350, 0.1, 100, 2000),
('Software-Developer', 500, 0.2, 200, 5000),
('Police-Officer', 450, 0.15, 150, 7500),
('Engineer', 550, 0.2, 250, 10000),
('Doctor', 600, 0.1, 300, 15000),
('Politician', 750, 0.3, 350, 25000),
('Stripper', 150, 0.5, 150, 1000),
('Pilot', 800, 0.15, 400, 30000),
('Scientist', 700, 0.25, 300, 20000),
('Lawyer', 650, 0.3, 250, 18000),
('Real-Estate-Agent', 400, 0.4, 300, 10000),
('Stock-Trader', 600, 0.5, 400, 20000),
('Youtuber', 300, 0.6, 500, 5000),
('Streamer', 250, 0.55, 400, 4000),
('Esportler', 400, 0.45, 300, 8000),
('Astronaut', 1000, 0.2, 500, 50000),
('Flight-Attendant', 250, 0.2, 100, 3000),
('Delivery-Driver', 150, 0.25, 50, 0),
('Plumber', 300, 0.2, 100, 4000),
('Farmer', 220, 0.2, 80, 2000),
('Life-Coach', 350, 0.3, 150, 6000)
ON CONFLICT (name) DO NOTHING;