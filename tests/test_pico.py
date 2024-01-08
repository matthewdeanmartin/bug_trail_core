import sqlite3

import picologging as logging

from bug_trail_core.handlers import PicoBugTrailHandler


def test_pico_sqlite_handler(tmp_path):
    db_path = tmp_path / "test.db"

    # Instantiate the handler
    handler = PicoBugTrailHandler(str(db_path))

    # Create a logger and add the handler
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)

    # Log a test message
    test_message = "This is a test error log"
    logger.error(test_message)

    # Verify the log is in the database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT msg FROM logs")
    log_record = cursor.fetchone()
    conn.close()

    assert log_record is not None
    assert test_message in log_record

    for leftover in logger.handlers:
        logger.removeHandler(leftover)
    # # Clean up
    # handler.close()


def test_pico_handler_with_exception(tmp_path):
    db_path = tmp_path / "test_pico.db"

    # Instantiate the handler
    handler = PicoBugTrailHandler(str(db_path))

    # Create a logger and add the handler
    logger = logging.getLogger("test_logger_exception")
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)

    logger.info("this will be ignored")

    # Log a message with an exception
    try:
        raise ValueError("This is a test exception")
    except ValueError:
        logger.exception("Logging an exception")

    # Verify the exception log is in the database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs")
    log_record = cursor.fetchone()
    conn.close()

    assert log_record is not None
    assert "This is a test exception" in log_record[4]

    for leftover in logger.handlers:
        logger.removeHandler(leftover)


def test_defensive_if(tmp_path):
    db_path = str(tmp_path / "test.db")

    # Initialize BugTrailHandler with a mock BaseErrorLogHandler
    handler = PicoBugTrailHandler(db_path)
    record = logging.LogRecord("test_logger", logging.INFO, "test_file.py", 123, "This is a test message", None, None)
    handler.emit(record)  # Call emit with None to test the defensive if
