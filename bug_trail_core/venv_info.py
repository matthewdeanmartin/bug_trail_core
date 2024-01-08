import importlib.metadata
import json
import sqlite3
import uuid
from collections.abc import Generator
from importlib.metadata import PackageMetadata
from typing import cast


def create_connection(db_file: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_file)
    return conn


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

    # cursor = conn.cursor()
    # cursor.execute("Delete from python_libraries;")


def insert_python_library(conn: sqlite3.Connection, library_name: str, version: str, urls: dict[str, str]) -> None:
    sql_insert_library = """INSERT INTO python_libraries (row_id, library_name, version, urls) 
                            VALUES (?, ?, ?, ?)"""
    cursor = conn.cursor()
    row_id = str(uuid.uuid4())
    cursor.execute(sql_insert_library, (row_id, library_name, version, json.dumps(urls)))
    conn.commit()


def get_installed_packages() -> Generator[tuple[str, str, PackageMetadata], None, None]:
    for package in importlib.metadata.distributions():
        yield package.metadata["Name"], package.version, package.metadata


def record_venv_info(conn: sqlite3.Connection) -> None:
    if conn is None:
        raise TypeError("Need live connection")
    create_python_libraries_table(conn)
    for name, version, metadata in get_installed_packages():
        urls = {key: value for key, value in cast(dict, metadata).items() if value.strip().lower().startswith("http")}
        if metadata.json:
            kvs = metadata.json
            project_url = kvs.get("project_url")
            if isinstance(project_url, list):
                more_urls = {}
                for url in project_url:
                    key, value = url.split(",")
                    more_urls[key] = value
                urls.update(more_urls)

            more_urls = {
                key: value
                for key, value in kvs.items()
                if isinstance(value, str) and value.strip().lower().startswith("http")
            }
            urls.update(more_urls)
        insert_python_library(conn, name, version, urls)
