import logging
from contextlib import contextmanager


class CapturedLog(logging.Handler):
    """Collects what the proxy logs. Unlike caplog it does not depend on how other tests left the logger."""

    def __init__(self):
        super().__init__(logging.WARNING)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@contextmanager
def capture_log(name="uvicorn.error"):
    logger = logging.getLogger(name)
    handler = CapturedLog()
    saved = (logger.level, logger.disabled)
    logger.setLevel(logging.WARNING)
    logger.disabled = False
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(saved[0])
        logger.disabled = saved[1]
