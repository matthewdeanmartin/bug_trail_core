import sys
from unittest.mock import patch

import pytest

from bug_trail_core import read_config  # Replace with your actual import


# Test when the config file is present and contains all necessary fields
@pytest.mark.skipif(sys.version_info[:2] == (3, 9), reason="Skipped on Python 3.9")
@pytest.mark.skipif(sys.version_info[:2] == (3, 10), reason="Skipped on Python 3.10")
def test_read_config_full(tmp_path):
    # Create a temporary TOML file with full configuration
    config_file = tmp_path / "pyproject.toml"
    config_content = """
    [tool.bug_trail]
    app_name = "MyApp"
    app_author = "MyAuthor"
    report_folder = "/path/to/reports"
    database_path = "/path/to/database.db"
    source_folder = "/path/to/source"
    ctags_file = "/path/to/ctags"
    """
    config_file.write_text(config_content)

    # Mock platformdirs functions
    with (
        patch("platformdirs.user_data_dir") as mock_user_data_dir,
        patch("platformdirs.user_config_dir") as mock_user_config_dir,
    ):
        mock_user_data_dir.return_value = "/default/data/dir"
        mock_user_config_dir.return_value = "/default/config/dir"

        # Read the configuration
        config = read_config(str(config_file))

    # Assertions
    assert config.app_name == "MyApp"
    assert config.app_author == "MyAuthor"
    assert config.report_folder == "/path/to/reports"
    assert config.database_path == "/path/to/database.db"
    assert config.source_folder == "/path/to/source"
    assert config.ctags_file == "/path/to/ctags"


# Test when the config file is missing some fields
@pytest.mark.skipif(sys.version_info[:2] == (3, 9), reason="Skipped on Python 3.9")
@pytest.mark.skipif(sys.version_info[:2] == (3, 10), reason="Skipped on Python 3.10")
def test_read_config_partial(tmp_path):
    # Create a temporary TOML file with partial configuration
    config_file = tmp_path / "pyproject.toml"
    config_content = """
    [tool.bug_trail]
    app_name = "MyApp"
    """
    config_file.write_text(config_content)

    # Mock platformdirs functions
    with (
        patch("platformdirs.user_data_dir") as mock_user_data_dir,
        patch("platformdirs.user_config_dir") as mock_user_config_dir,
    ):
        mock_user_data_dir.return_value = "/default/data/dir"
        mock_user_config_dir.return_value = "/default/config/dir"

        # Read the configuration
        config = read_config(str(config_file))

    # Assertions
    assert config.app_name == "MyApp"
    assert config.app_author == "bug_trail"  # Default value
    assert config.report_folder.replace("\\", "/") == "/default/data/dir/reports"  # Default value
    assert config.database_path.replace("\\", "/") == "/default/config/dir/bug_trail.db"  # Default value
    assert config.source_folder.replace("\\", "/") == ""  # Default value
    assert config.ctags_file.replace("\\", "/") == ""  # Default value


# Test when the config file is not present
def test_read_config_missing(tmp_path):
    # Test with a non-existent config file
    config_file = tmp_path / "nonexistent.toml"

    # Mock platformdirs functions
    with (
        patch("platformdirs.user_data_dir") as mock_user_data_dir,
        patch("platformdirs.user_config_dir") as mock_user_config_dir,
    ):
        mock_user_data_dir.return_value = "/default/data/dir"
        mock_user_config_dir.return_value = "/default/config/dir"

        # Read the configuration
        config = read_config(str(config_file))

    # Assertions for default values
    assert config.app_name == "bug_trail"
    assert config.app_author == "bug_trail"
    assert config.report_folder.replace("\\", "/") == "/default/data/dir/reports"
    assert config.database_path.replace("\\", "/") == "/default/config/dir/bug_trail.db"
    assert config.source_folder.replace("\\", "/") == ""
    assert config.ctags_file.replace("\\", "/") == ""
