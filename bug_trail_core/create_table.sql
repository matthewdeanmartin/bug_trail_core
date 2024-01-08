CREATE TABLE IF NOT EXISTS logs
(
    record_id TEXT PRIMARY KEY,
    args            TEXT,
    asctime         TEXT,
    created         REAL,
    exc_info        TEXT,
    exc_text        TEXT,
    filename        TEXT,
    funcName        TEXT,
    levelname       TEXT,
    levelno         INTEGER,
    lineno          INTEGER,
    message         TEXT,
    module          TEXT,
    msecs           REAL,
    msg             TEXT,
    name            TEXT,
    pathname        TEXT,
    process         INTEGER,
    processName     TEXT,
    relativeCreated REAL,
    stack_info      TEXT,
    thread          INTEGER,
    threadName      TEXT,
    traceback       TEXT
)
