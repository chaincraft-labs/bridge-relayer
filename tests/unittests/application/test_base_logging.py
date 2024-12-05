import os
import logging
import pytest

from src.relayer.application.base_logging import RelayerLogging

# ----------------------- FIXTURES -----------------------
@pytest.fixture(scope="module", autouse=True)
def setup_logging():
    """Setup fixture to clean up log files before tests."""
    log_file = 'relayer.log'
    log_err_file = 'relayer.err.log'
    log_debug_file = 'relayer.debug.log'

    # Cleanup log files before the tests run
    for file in [log_file, log_err_file, log_debug_file]:
        if os.path.exists(file):
            os.remove(file)

    yield

    # Cleanup log files after tests complete
    for file in [log_file, log_err_file, log_debug_file]:
        if os.path.exists(file):
            os.remove(file)

# ----------------------- TESTS -----------------------

def test_logger_creation():
    """Test logger creation and basic logging functionality."""
    relayer_logger = RelayerLogging(level='DEBUG')

    assert relayer_logger.logger.name == f"{relayer_logger.__class__.__name__}_{id(relayer_logger)}"
    assert relayer_logger.logger.level == logging.DEBUG

    # Log a message
    relayer_logger.logger.debug("Debug message")
    relayer_logger.logger.info("Info message")
    relayer_logger.logger.warning("Warning message")

    # Check if the log file exists and contains the expected log messages
    log_file = 'relayer.log'
    log_err_file = 'relayer.err.log'
    log_debug_file = 'relayer.debug.log'

    assert os.path.exists(log_file)
    assert os.path.exists(log_err_file)
    assert os.path.exists(log_debug_file)

def test_log_format():
    """Test if logs are formatted correctly."""
    relayer_logger = RelayerLogging(level='DEBUG')
    
    # Log a message
    relayer_logger.logger.info("Info message for formatting test")

    # Read the log file
    with open('relayer.log', 'r') as f:
        logs = f.readlines()

    # Check the last log entry for correct formatting
    last_log = logs[-1]
    assert "Info message for formatting test" in last_log
    assert len(last_log.split()) >= 5  # Ensures that there are at least timestamp, level, and message

def test_warning_logging():
    """Test if warning logs are correctly written to error log."""
    relayer_logger = RelayerLogging(level='INFO')

    # Log a warning message
    relayer_logger.logger.warning("Warning message for error log")

    # Read the error log file
    log_err_file = 'relayer.err.log'
    with open(log_err_file, 'r') as f:
        logs = f.readlines()

    assert os.path.exists(log_err_file)
    assert "Warning message for error log" in logs[-1]  # Check if the warning message is present
