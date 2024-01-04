from unittest.mock import MagicMock, patch

from bug_trail_core.handlers import BugTrailHandler


class MockBaseErrorLogHandler:
    def __init__(self, db_path):
        self.db_path = db_path

    def close(self):
        pass  # Mock close behavior


@patch("bug_trail_core.handlers.super")
def test_bug_trail_handler_close(mock_super, tmp_path):
    db_path = str(tmp_path / "test.db")

    # Initialize BugTrailHandler with a mock BaseErrorLogHandler
    handler = BugTrailHandler(db_path)
    handler.base_handler = MockBaseErrorLogHandler(db_path)

    # Mock the close method of the superclass
    mock_super_close = MagicMock()
    mock_super.return_value.close = mock_super_close

    # Call the close method
    handler.close()

    # Assert that the close method of the superclass was called
    mock_super_close.assert_called_once()
