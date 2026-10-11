from loguru import logger

from wowfish import paths
from wowfish.logging import setup_logging


def test_setup_logging_returns_log_file_and_writes_to_it(capsys):
    log_path = setup_logging(verbose=False)
    assert log_path == paths.log_file()
    logger.info("hello from test")
    logger.debug("debug should not reach stderr")
    logger.complete()
    err = capsys.readouterr().err
    assert "hello from test" in err
    assert "debug should not reach stderr" not in err
    assert "hello from test" in log_path.read_text()


def test_verbose_enables_debug_on_stderr(capsys):
    setup_logging(verbose=True)
    logger.debug("debug visible")
    logger.complete()
    assert "debug visible" in capsys.readouterr().err
