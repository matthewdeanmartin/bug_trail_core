# Contents of bug_trail_core source tree

## File: config.py

```python
"""
Configuration module for Bug Trail.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import tomllib

    USE_TOMLLIB = True
except ImportError:
    USE_TOMLLIB = False
try:
    import toml
except ImportError:
    pass
import platformdirs


@dataclass
class BugTrailConfig:
    """Dataclass to hold Bug Trail configuration."""

    app_name: str
    app_author: str
    report_folder: str
    database_path: str
    source_folder: str
    ctags_file: str


def read_config(config_path: str) -> BugTrailConfig:
    """
    Read the Bug Trail configuration from a pyproject.toml file.

    Args:
        config_path (str): Path to the pyproject.toml file.

    Returns:
        BugTrailConfig: Configuration object for Bug Trail.
    """
    # Read the TOML file

    try:
        if USE_TOMLLIB:
            with open(config_path, "rb") as handle:
                bug_trail_config = tomllib.load(handle)
        else:
            bug_trail_config = toml.load(config_path)
    # toml and tomllib raise different errors
    except BaseException:
        bug_trail_config = {}

    section = bug_trail_config.get("tool", {}).get("bug_trail", {})

    # Set default values
    app_name = section.get("app_name", "bug_trail")
    app_author = section.get("app_author", "bug_trail")

    default_data_dir = platformdirs.user_data_dir(app_name, app_author, ensure_exists=True)
    default_config_dir = platformdirs.user_config_dir(app_name, app_author, ensure_exists=True)

    report_folder = section.get("report_folder", os.path.join(default_data_dir, "reports"))
    database_path = section.get("database_path", os.path.join(default_config_dir, "bug_trail.db"))

    # input!
    source_folder = section.get("source_folder", "")
    ctags_file = section.get("ctags_file", "")
    return BugTrailConfig(app_name, app_author, report_folder, database_path, source_folder, ctags_file)


if __name__ == "__main__":

    def run() -> None:
        """Example usage"""
        config = read_config("../pyproject.toml")
        print(config)

    run()

```

## File: exceptions.py

```python
"""
Record type, instance and call stack info about an exception.
"""

from __future__ import annotations

import json
import sqlite3


def get_exception_hierarchy(ex: BaseException) -> list[tuple[str, str | None]]:
    """
    Get the inheritance hierarchy of an exception.

    Parameters:
    ex (Exception): The exception instance.

    Returns:
    list of tuples: A list where each tuple contains the name and docstring of a class in the hierarchy.
    """
    hierarchy = []
    ex_class = ex.__class__

    # Traverse the inheritance hierarchy
    while ex_class:
        hierarchy.append((ex_class.__name__, ex_class.__doc__))
        if ex_class.__bases__:
            # Move up to the next base class
            ex_class = ex_class.__bases__[0]
        else:
            break

    return hierarchy


def create_connection(db_file: str) -> sqlite3.Connection:
    """Create a database connection to a SQLite database"""
    conn = sqlite3.connect(db_file)
    return conn


def create_exception_type_table(conn: sqlite3.Connection) -> None:
    """Create the exception_type table with an additional column for the hierarchy"""
    sql_create_exception_type_table = """CREATE TABLE IF NOT EXISTS exception_type (
                                            id INTEGER PRIMARY KEY,
                                            name TEXT NOT NULL,
                                            module TEXT NOT NULL,
                                            docstring TEXT,
                                            hierarchy TEXT
                                        );"""
    cursor = conn.cursor()
    cursor.execute(sql_create_exception_type_table)


def insert_exception_type(conn: sqlite3.Connection, ex: BaseException) -> int:
    """Insert a new row into the exception_type table including the hierarchy"""
    ex_class = ex.__class__
    ex_name = ex_class.__name__
    ex_module = ex_class.__module__
    ex_docstring = ex_class.__doc__
    ex_hierarchy = json.dumps(get_exception_hierarchy(ex))

    # Check if this type of exception already exists
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exception_type WHERE name = ? AND module = ?", (ex_name, ex_module))
    data = cursor.fetchone()

    # Insert new exception type along with its hierarchy
    if data is not None:
        return data[0]
    sql_insert_exception_type = """INSERT INTO exception_type (name, module, docstring, hierarchy) 
                                   VALUES (?, ?, ?, ?)"""
    cursor.execute(sql_insert_exception_type, (ex_name, ex_module, ex_docstring, ex_hierarchy))
    conn.commit()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exception_type WHERE name = ? AND module = ?", (ex_name, ex_module))
    data = cursor.fetchone()
    return data[0]


def create_exception_instance_table(conn: sqlite3.Connection) -> None:
    """Create the exception_instance table if it doesn't exist"""
    sql_create_exception_instance_table = """CREATE TABLE IF NOT EXISTS exception_instance (
                                                record_id TEXT PRIMARY KEY,
                                                type_id INTEGER,
                                                args TEXT,
                                                str_repr TEXT,
                                                comments TEXT,
                                                FOREIGN KEY (type_id) REFERENCES exception_type (id)
                                            );"""
    cursor = conn.cursor()
    cursor.execute(sql_create_exception_instance_table)


def insert_exception_instance(conn: sqlite3.Connection, record_id: str, ex: BaseException, comments: str = "") -> None:
    """Insert a new row into the exception_instance table"""
    ex_class = ex.__class__
    ex_name = ex_class.__name__
    ex_module = ex_class.__module__

    # Find the type_id from the exception_type table
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exception_type WHERE name = ? AND module = ?", (ex_name, ex_module))
    type_data = cursor.fetchone()

    if type_data is not None:
        type_id = type_data[0]
        ex_args = str(ex.args)
        ex_str_repr = str(ex)

        # Insert new exception instance
        sql_insert_exception_instance = """INSERT INTO exception_instance 
                                           (record_id, type_id, args, str_repr, comments) 
                                           VALUES (?, ?, ?, ?, ?)"""
        cursor.execute(sql_insert_exception_instance, (record_id, type_id, ex_args, ex_str_repr, comments))
        conn.commit()


def create_traceback_info_table(conn: sqlite3.Connection) -> None:
    """Create the traceback_info table if it doesn't exist"""
    sql_create_traceback_info_table = """CREATE TABLE IF NOT EXISTS traceback_info (
                                            id TEXT PRIMARY KEY,
                                            exception_instance_id TEXT,
                                            frame_number INTEGER,
                                            f_locals TEXT,
                                            f_globals TEXT,
                                            FOREIGN KEY (exception_instance_id) REFERENCES exception_instance (id)
                                        );"""
    cursor = conn.cursor()
    cursor.execute(sql_create_traceback_info_table)


def insert_traceback_info(conn: sqlite3.Connection, exception_instance_id: str, tb) -> None:
    """Insert traceback information for each frame"""
    cursor = conn.cursor()
    frame_number = 0

    while tb:
        frame = tb.tb_frame
        f_locals = json.dumps(frame.f_locals, default=str)
        f_globals = json.dumps(frame.f_globals, default=str)

        sql_insert_traceback_info = """INSERT INTO traceback_info 
                                       (exception_instance_id, frame_number, f_locals, f_globals) 
                                       VALUES (?, ?, ?, ?)"""
        cursor.execute(sql_insert_traceback_info, (exception_instance_id, frame_number, f_locals, f_globals))

        tb = tb.tb_next
        frame_number += 1

    conn.commit()


if __name__ == "__main__":

    def run():
        # Example usage
        db_file = "path_to_your_database.db"
        conn = create_connection(db_file)
        if conn is not None:
            create_exception_type_table(conn)
            create_exception_instance_table(conn)
            create_traceback_info_table(conn)
            try:
                _ = 2 / 0
            except Exception as ex:
                insert_exception_type(conn, ex)
                # Insert exception instance and get its ID
                ex.add_note("Hello!")
                insert_exception_instance(conn, "abc", ex, "Comments about the exception")
                cursor = conn.cursor()
                cursor.execute("SELECT last_insert_rowid()")
                exception_instance_id = cursor.fetchone()[0]
                # Insert traceback info
                insert_traceback_info(conn, exception_instance_id, ex.__traceback__)

    run()

```

## File: generate_sql.py

```python
"""
Code to generate sql for table.
"""

from __future__ import annotations

import logging


def create_table_schemas(pico: bool) -> str:
    """
    Schema
    """
    # Create a dummy LogRecord to introspect its attributes
    dummy_record = None

    # Define a mapping of Python types to SQLite types
    type_mapping = {
        int: "INTEGER",
        float: "REAL",
        str: "TEXT",
        bytes: "BLOB",  # Assuming bytes should be stored as BLOB
        type(None): "TEXT",  # Why would we have a column of just None?
    }

    # Build the columns schema based on LogRecord attributes
    columns = []

    # mypyc won't deal with a union of the 2 kinds of LogRecords, so
    # we live with some duplication here.

    dummy_record = logging.LogRecord(
        name="", level=logging.ERROR, pathname="", lineno=0, msg="", args=(), exc_info=None
    )
    for attr in dir(dummy_record):
        if not callable(getattr(dummy_record, attr)) and not attr.startswith("__"):
            attr_type = type(getattr(dummy_record, attr, ""))
            sqlite_type = type_mapping.get(attr_type, "TEXT")  # Default to TEXT if type not in mapping
            columns.append(f"{attr} {sqlite_type}")

    # Add traceback column
    columns.append("traceback TEXT")

    # message is when `msg % args` gets evaluated by some part of the `logging` module?
    if "message TEXT" not in columns:
        columns.append("message TEXT")

    columns_text = ", ".join(columns)
    create_table_sql = f"CREATE TABLE IF NOT EXISTS logs ({columns_text})"
    return create_table_sql


if __name__ == "__main__":
    print(create_table_schemas(True))
    print(create_table_schemas(False))

```

## File: handlers.py

```python
"""
This module contains custom logging handlers.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
import traceback
import uuid
from importlib.resources import as_file, files
from typing import Any

from bug_trail_core.exceptions import (
    create_exception_instance_table,
    create_exception_type_table,
    create_traceback_info_table,
    insert_exception_instance,
    insert_exception_type,
    insert_traceback_info,
)
from bug_trail_core.sqlite3_utils import is_table_empty, serialize_to_sqlite_supported
from bug_trail_core.system_info import create_system_info_table, record_system_info
from bug_trail_core.venv_info import create_python_libraries_table, record_venv_info


class BaseErrorLogHandler:
    """
    A custom logging handler that logs to a SQLite database.
    """

    def __init__(
        self, db_path: str, pico: bool = False, minimum_level: int = logging.ERROR, single_threaded: bool = True
    ) -> None:
        """
        Initialize the handler
        Args:
            db_path (str): Path to the SQLite database
        """
        self.single_threaded = single_threaded
        self.db_path = db_path
        self.pico = pico
        self.minimum_level = minimum_level
        self.create_table_sql: str = ""
        self.formatted_sql = ""
        self.field_names = ""
        # call things only after all attributes assigned
        self.reopen()
        self.create_table()
        self.reopen()
        create_exception_type_table(self.conn)
        self.reopen()
        create_exception_instance_table(self.conn)
        self.reopen()
        create_traceback_info_table(self.conn)

        self.reopen()
        create_system_info_table(self.conn)
        self.reopen()
        if is_table_empty(self.conn, "system_info"):
            record_system_info(self.conn)

        self.reopen()
        create_python_libraries_table(self.conn)
        self.reopen()
        if is_table_empty(self.conn, "python_libraries"):
            record_venv_info(self.conn)

    def reopen(self) -> None:
        """Reopen the connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode = MEMORY;")
        self.conn.execute("PRAGMA synchronous = OFF;")

    def create_table(self) -> None:
        """
        Create the logs table if it doesn't exist
        """
        # Locate the resource file
        source = files("bug_trail_core").joinpath("create_table.sql")

        with as_file(source) as file:
            self.create_table_sql = file.read_text(encoding="utf-8")

        if not self.create_table_sql:
            # Create a dummy LogRecord to introspect its attributes
            dummy_record = None

            # Define a mapping of Python types to SQLite types
            type_mapping = {
                int: "INTEGER",
                float: "REAL",
                str: "TEXT",
                bytes: "BLOB",  # Assuming bytes should be stored as BLOB
                type(None): "TEXT",  # Why would we have a column of just None?
            }

            # Build the columns schema based on LogRecord attributes
            columns = []

            dummy_record = logging.LogRecord(
                name="", level=logging.ERROR, pathname="", lineno=0, msg="", args=(), exc_info=None
            )
            for attr in dir(dummy_record):
                if not callable(getattr(dummy_record, attr)) and not attr.startswith("__"):
                    attr_type = type(getattr(dummy_record, attr, ""))
                    sqlite_type = type_mapping.get(attr_type, "TEXT")  # Default to TEXT if type not in mapping
                    columns.append(f"{attr} {sqlite_type}")

            # Add traceback column
            columns.append("traceback TEXT")

            # message is when `msg % args` gets evaluated by some part of the `logging` module?
            if "message TEXT" not in columns:
                columns.append("message TEXT")

            columns_text = ", ".join(columns)
            self.create_table_sql = f"CREATE TABLE IF NOT EXISTS logs ({columns_text})"
        # TODO: is there a faster way to check if a table exist?
        self.safe_execute(self.create_table_sql, [])

    def emit(self, record: logging.LogRecord) -> None:
        """
        Insert a log record into the database

        Args:
            record (logging.LogRecord): The log record to be inserted
        """
        if record.levelno < self.minimum_level:
            return

        # clientside primary key
        record_id = str(uuid.uuid4())
        if not record.exc_info:
            record.exc_info = sys.exc_info()
        # Check if there is exception information
        if record.exc_info:
            exception_type, exception, traceback_object = record.exc_info
            # Format the traceback
            traceback_str = "".join(traceback.format_exception(*record.exc_info))
            record.traceback = traceback_str

            if exception:
                # not unique per log entry
                insert_exception_type(self.conn, exception)
                # unique per log entry
                insert_exception_instance(self.conn, record_id, exception)
                exception_instance_id = record_id
                # Insert traceback info
                if exception and exception.__traceback__:
                    insert_traceback_info(self.conn, exception_instance_id, exception.__traceback__)
        else:
            record.traceback = None

        if not self.formatted_sql:
            # I don't think I can precalc this in advance as the fields in a Record
            # can change subtly from call to call.
            insert_sql = "INSERT INTO logs ({fields}) VALUES ({values})"
            self.field_names = ", ".join(
                [attr for attr in dir(record) if not attr.startswith("__") and not attr == "getMessage"]
            )
            self.field_names = self.field_names + ", traceback, message"
            field_values = ", ".join(["?" for _ in self.field_names.split(", ")])
            self.formatted_sql = insert_sql.format(fields="record_id," + self.field_names, values="?," + field_values)
        args = [record_id] + [getattr(record, field, "") for field in self.field_names.split(", ")]
        args = [serialize_to_sqlite_supported(arg) for arg in args]

        self.safe_execute(self.formatted_sql, args)

    def safe_execute(self, sql: str, args: list[Any], recurse_count: int = 0) -> None:
        if not self.single_threaded:
            self.reopen()
        try:
            self.conn.execute(sql, args)
        except sqlite3.OperationalError as oe:
            if "no such table" in oe.args[0] and recurse_count == 0:
                self.create_table()
                recurse_count += 1
                self.safe_execute(sql, args, recurse_count)
            else:
                raise
        self.conn.commit()
        if not self.single_threaded:
            self.conn.close()

    def close(self) -> None:
        """
        Close the connection to the database
        """
        # If we are not single threaded, even talking to the conn object
        # will throw an error.
        if self.conn and self.single_threaded:
            try:
                self.conn.close()
            except sqlite3.ProgrammingError as programming_error:
                if "Cannot operate on a closed database" in str(programming_error):
                    pass
                raise


class BugTrailHandler(logging.Handler):
    """
    A custom logging handler that logs to a SQLite database.
    """

    def __init__(self, db_path: str, minimum_level: int = logging.ERROR, single_threaded: bool = True) -> None:
        """
        Initialize the handler
        Args:
            db_path (str): Path to the SQLite database
            single_threaded (bool): If True, the handler will close the connection after each emit.
        """
        self.base_handler = BaseErrorLogHandler(db_path, minimum_level=minimum_level, single_threaded=single_threaded)
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Insert a log record into the database

        Args:
            record (logging.LogRecord): The log record to be inserted
        """
        self.base_handler.emit(record)

    def close(self) -> None:
        """
        Close the connection to the database
        """
        self.base_handler.close()
        super().close()

```

## File: report_meta.py

```python
"""
Reports all that ad hoc, folksonomy metadata that is used in Python packages and scripts.

There is no standard but could be useful for diagnostics.
"""

from __future__ import annotations

import inspect
import os
import re
import sys


def get_module(exception):
    """Get the module of the exception."""
    exception_class = exception.__class__
    module_name = exception_class.__module__
    module = sys.modules[module_name]
    return module


def get_module_file(module):
    """Get the file associated with a module."""
    return inspect.getfile(module)


def is_package(module):
    """Check if a module is a package."""
    module_file = get_module_file(module)
    return os.path.basename(module_file) == "__init__.py"


def get_init(module, source_file: str):
    """Get the __init__.py file of the module's package."""
    module_file = inspect.getfile(module)
    module_dir = os.path.dirname(module_file)

    # Check if the module itself is a package (__init__.py)

    if os.path.basename(module_file) == source_file:
        return module_file

    # Check for __init__.py in the module's directory
    init_file = os.path.join(module_dir, source_file)
    if os.path.isfile(init_file):
        return init_file
    return None


def get_meta(init_file):
    """Extract metadata from the __init__.py file or a module file."""
    metadata = {}

    if init_file and os.path.isfile(init_file):
        with open(init_file) as file:
            content = file.read()

        # Define a regex pattern to match metadata variables
        pattern = r"__(\w+)__\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)

        for key, value in matches:
            metadata[key] = value
    return metadata


if __name__ == "__main__":

    class CustomError(Exception):
        """Custom exception for demonstration purposes."""

    def run():
        """Main function to demonstrate metadata extraction."""
        try:
            # ... some code that raises CustomError ...
            raise CustomError("An error occurred")
        except CustomError as ce:
            module = get_module(ce)
            # is_pkg = is_package(module) # returns false even though it is in a package!
            # if not is_pkg:
            # Gets file where declared.
            file = get_module_file(module)
            for candidate in ["__init__.py", "__about__.py", "about.py", "__meta__.py", file]:
                init_file = get_init(module, candidate)
                metadata = get_meta(init_file)
                if metadata:
                    break
            print(metadata)

    run()

```

## File: sqlite3_utils.py

```python
"""
Another module to avoid Circular Import
"""

from __future__ import annotations

import datetime
import sqlite3
from typing import Any, Union

ALL_TABLES = [
    "exception_instance",
    "exception_type",
    "logs",
    "python_libraries",
    "system_info",
    "traceback_info",
]


SqliteTypes = Union[None, int, float, str, bytes, datetime.date, datetime.datetime]


def serialize_to_sqlite_supported(value: Any | None) -> SqliteTypes:
    """
    Sqlite supports None, int, float, str, bytes by default, and also knows how to adapt datetime.date and datetime.datetime
    everything else is str(value)
    >>> serialize_to_sqlite_supported(1)
    1
    >>> serialize_to_sqlite_supported(1.0)
    1.0
    """
    # if isinstance(value, NoneType):
    #     return None
    if value is None:
        return None
    if isinstance(value, (int, float, str, bytes)):
        return value
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value
    return str(value)


def is_table_empty(conn: sqlite3.Connection, table_name: str) -> bool:
    """
    Check if the specified table is empty.

    Parameters:
    conn (sqlite3.Connection): The database connection.
    table_name (str): The name of the table to check.

    Returns:
    bool: True if the table is empty, False otherwise.
    """
    if table_name not in ALL_TABLES:
        raise TypeError("Bad table name.")
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT EXISTS(SELECT 1 FROM {table_name} LIMIT 1);")  # nosec: table checked above
        return cursor.fetchone()[0] == 0
    except sqlite3.Error:
        return True  # Assuming empty if an error occurs


def truncate_table(conn: sqlite3.Connection, table_name: str) -> None:
    """
    Truncate the specified table.

    Parameters:
    conn (sqlite3.Connection): The database connection.
    table_name (str): The name of the table to truncate.
    """
    if table_name not in ALL_TABLES:
        raise TypeError("Bad table name.")
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table_name};")  # nosec: table checked above
        cursor.execute("VACUUM;")  # Optional: Cleans the database file, resetting auto-increment counters
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

```

## File: system_info.py

```python
"""
System info for including with error logs
"""

from __future__ import annotations

import json
import platform
from collections.abc import Sequence

import psutil


def convert_bytes_to_gb(bytes_value: int) -> str:
    """
    Converts a byte value to gigabytes and formats it to two decimal places.
    """
    gb_value = bytes_value / (1024**3)
    return f"{gb_value:.2f} GB"


def convert_mhz_to_ghz(mhz_value: int) -> str:
    """
    Converts a frequency value from MHz to GHz and formats it to two decimal places.
    """
    ghz_value = mhz_value / 1000
    return f"{ghz_value:.2f} GHz"


def get_os_summary() -> dict[str, Sequence[str]]:
    """Collects and returns a summary of the operating system information."""
    os_version = platform.version()
    os_platform = platform.system()
    os_release = platform.release()
    os_architecture = platform.machine()

    # Build operating system summary
    os_summary = {
        "Platform (sysname)": os_platform,
        "Release": os_release,
        "Architecture": os_architecture,
        "Version": os_version,
        "Windows Info": platform.win32_ver(),
    }

    return os_summary


def get_system_info() -> dict[str, str | Sequence[str]]:
    """
    Collects and returns system information including memory, CPU, disk space, and operating system details.
    """
    # Memory information
    mem = psutil.virtual_memory()
    total_memory = convert_bytes_to_gb(mem.total)
    available_memory = convert_bytes_to_gb(mem.available)

    # CPU information
    cpu_freq = psutil.cpu_freq()
    cpu_clock_speed = convert_mhz_to_ghz(cpu_freq.current)
    cpu_count = psutil.cpu_count(logical=False)

    # Disk information
    disk_usage = psutil.disk_usage("/")
    total_disk_space = convert_bytes_to_gb(disk_usage.total)
    available_disk_space = convert_bytes_to_gb(disk_usage.free)

    # Get the operating system summary
    os_summary = get_os_summary()

    # Build system information dictionary
    info = {
        "Total Memory": total_memory,
        "Available Memory": available_memory,
        "CPU Frequency": cpu_clock_speed,
        "CPU Cores": cpu_count,
        "Total Disk Space": total_disk_space,
        "Available Disk Space": available_disk_space,
        "Operating System Summary": os_summary,
    }

    return info


# Usage example
if __name__ == "__main__":
    system_info = get_system_info()
    for key, value in system_info.items():
        if key == "Operating System Summary" and isinstance(value, dict):
            print("Operating System Information:")
            for os_key, os_value in value.items():
                print(f"  {os_key}: {os_value}")
        else:
            print(f"{key}: {value}")


def create_system_info_table(conn):
    """Creates the system_info table in the database if it does not exist."""
    sql_create_table = """CREATE TABLE IF NOT EXISTS system_info (
                              id TEXT PRIMARY KEY,
                              snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              total_memory TEXT,
                              available_memory TEXT,
                              cpu_frequency TEXT,
                              cpu_cores INTEGER,
                              total_disk_space TEXT,
                              available_disk_space TEXT,
                              os_platform TEXT,
                              os_release TEXT,
                              os_architecture TEXT,
                              os_version TEXT,
                              windows_info TEXT
                          );"""
    cursor = conn.cursor()
    cursor.execute(sql_create_table)


def insert_system_info(conn, info):
    """Inserts system information into the system_info table."""
    sql_insert_info = """INSERT INTO system_info 
                         (total_memory, available_memory, cpu_frequency, cpu_cores, 
                          total_disk_space, available_disk_space, os_platform, os_release, 
                          os_architecture, os_version, windows_info) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    cursor = conn.cursor()
    cursor.execute(
        sql_insert_info,
        (
            info["Total Memory"],
            info["Available Memory"],
            info["CPU Frequency"],
            info["CPU Cores"],
            info["Total Disk Space"],
            info["Available Disk Space"],
            info["Operating System Summary"]["Platform (sysname)"],
            info["Operating System Summary"]["Release"],
            info["Operating System Summary"]["Architecture"],
            info["Operating System Summary"]["Version"],
            json.dumps(info["Operating System Summary"]["Windows Info"]),  # Store as JSON string
        ),
    )
    conn.commit()


def record_system_info(conn):
    """Records system information into the database."""
    if conn is None:
        raise TypeError("Need live connection")
    create_system_info_table(conn)
    system_info = get_system_info()
    insert_system_info(conn, system_info)

```

## File: venv_info.py

```python
import importlib.metadata
import json
import sqlite3
import uuid
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any


@contextmanager
def create_connection(db_file: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Establishes a connection to the SQLite database and ensures it's closed
    properly using a context manager.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        yield conn
    finally:
        if conn:
            conn.close()


def create_python_libraries_table(conn: sqlite3.Connection) -> None:
    sql_create_table = """CREATE TABLE IF NOT EXISTS python_libraries (
                              row_id TEXT PRIMARY KEY,
                              library_name TEXT NOT NULL,
                              version TEXT NOT NULL,
                              urls TEXT,
                              snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                          );"""

    cursor = conn.cursor()
    cursor.execute(sql_create_table)


def insert_python_library(conn: sqlite3.Connection, library_name: str, version: str, urls: dict[str, str]) -> None:
    sql_insert_library = """INSERT INTO python_libraries (row_id, library_name, version, urls)
                            VALUES (?, ?, ?, ?)"""
    cursor = conn.cursor()  # Corrected: This should be conn.cursor(), not conn.select()
    row_id = str(uuid.uuid4())
    cursor.execute(sql_insert_library, (row_id, library_name, version, json.dumps(urls)))
    conn.commit()


# Modified type hint for the metadata object
def get_installed_packages() -> Generator[tuple[str, str, Mapping[str, Any]], None, None]:  # type: ignore
    for package in importlib.metadata.distributions():
        # package.metadata in 3.9 is an email.message.Message object,
        # which behaves like a dictionary. We'll use Mapping[str, Any]
        # to represent its dictionary-like behavior without
        # relying on the internal email.message.Message type or the
        # not-yet-exposed PackageMetadata.
        yield package.metadata["Name"], package.version, package.metadata  # type: ignore


def record_venv_info(conn: sqlite3.Connection) -> None:
    if conn is None:
        raise TypeError("Need live connection")
    create_python_libraries_table(conn)
    for name, version, the_metadata in get_installed_packages():
        urls: dict[str, str] = {}  # Initialize urls as a Dict

        # Iterate over metadata items to find URLs.
        # the_metadata is a Mapping[str, Any]
        for key, value in the_metadata.items():
            if isinstance(value, str) and value.strip().lower().startswith("http"):
                urls[key] = value

        # Special handling for 'Project-URL' which can contain multiple URLs
        # In 3.9, the_metadata.get_all works for multi-value headers.
        project_urls = the_metadata.get_all("Project-URL")  # type: ignore
        if project_urls:
            for url_entry in project_urls:
                try:
                    # Use split with maxsplit to handle commas in the URL value itself
                    key, value = url_entry.split(",", 1)
                    urls[key.strip()] = value.strip()
                except ValueError:
                    # Handle cases where the Project-URL might not be in the expected format
                    pass

        insert_python_library(conn, name, version, urls)

```

## File: __about__.py

```python
"""Metadata for bug_trail_core."""

__all__ = [
    "__title__",
    "__version__",
    "__description__",
    "__readme__",
    "__requires_python__",
    "__keywords__",
    "__status__",
]

__title__ = "bug_trail_core"
__version__ = "3.0.0"
__description__ = "Local static html error logger to use while developing python code."
__readme__ = "README.md"
__requires_python__ = ">=3.9"
__keywords__ = ["error logging", "html log report"]
__status__ = "4 - Beta"

```

## File: __init__.py

```python
"""
Captures error logs to sqlite. Companion CLI tool generates a static website.

Install bug_trail_core to your application. Pipx install bug_trail to avoid dependency
conflicts
"""

from bug_trail_core.__about__ import __version__
from bug_trail_core.config import BugTrailConfig, read_config
from bug_trail_core.handlers import BugTrailHandler

__all__ = ["BugTrailHandler", "read_config", "BugTrailConfig", "__version__"]

```

## File: __main__.py

```python
"""
Main entry point for the CLI.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from bug_trail_core import read_config
from bug_trail_core.__about__ import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """
    Main entry point for the CLI.

    Returns:
        int: 0 if successful, 1 if not
    """
    parser = argparse.ArgumentParser(
        prog="bug_trail_core", description="Core library for bug_trail a tool for local logging and error reporting."
    )

    parser.add_argument(
        "--show-config",
        type=str,
        help="Path to the configuration file (usually pyproject.toml)",
        required=False,
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + f"{__version__}")

    args = parser.parse_args(argv)
    if args.show_config:
        print("This is the core library. Install or run bug_trail to generate the website to view the logs.\n")
        print(read_config(args.show_config))
    else:
        print("This is the core library. Install or run bug_trail to generate the website to view the logs.\n")
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())

```

