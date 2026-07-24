CREATE TABLE IF NOT EXISTS access_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code_hash TEXT NOT NULL UNIQUE,
  max_devices INTEGER NOT NULL DEFAULT 2 CHECK (max_devices BETWEEN 1 AND 5),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
  batch TEXT NOT NULL DEFAULT 'manual',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT,
  last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS code_devices (
  code_id INTEGER NOT NULL,
  device_hash TEXT NOT NULL,
  first_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (code_id, device_hash),
  FOREIGN KEY (code_id) REFERENCES access_codes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_access_codes_hash ON access_codes(code_hash);
CREATE INDEX IF NOT EXISTS idx_code_devices_code_id ON code_devices(code_id);
