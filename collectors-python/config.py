"""Environment-backed settings for the Boyar collector."""
from dataclasses import dataclass, field
import fcntl
import hashlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


@dataclass(frozen=True)
class BoyarConfig:
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:16380/0"))
    cursor_key: str = "collector:boyar:last_article_id"
    start_article_id: int = field(default_factory=lambda: int(os.getenv("BOYAR_START_ARTICLE_ID", "1267743")))
    scan_limit: int = field(default_factory=lambda: int(os.getenv("BOYAR_SCAN_LIMIT", "150")))
    request_timeout: float = 30.0
    min_interval: float = 1.0
    max_interval: float = 3.0
    max_retries: int = 3
    log_dir: str = field(default_factory=lambda: os.getenv("COLLECTOR_LOG_DIR", "/app/logs/collectors"))
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    user_agents: tuple = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Version/16.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
    )

    def __post_init__(self):
        if self.start_article_id < 1 or self.scan_limit < 1:
            raise ValueError("start_article_id and scan_limit must be positive")
        if not 1 <= self.min_interval <= self.max_interval <= 3:
            raise ValueError("request intervals must be between 1 and 3 seconds")
        if self.request_timeout <= 0 or not 0 <= self.max_retries <= 3:
            raise ValueError("invalid timeout or retry count")
        if not self.user_agents:
            raise ValueError("at least one User-Agent is required")
        if self.log_max_bytes < 1 or self.log_backup_count < 1:
            raise ValueError("log size and backup count must be positive")


class LockedRotatingFileHandler(RotatingFileHandler):
    """Coordinate rollover across short-lived Python runner processes (Linux/macOS)."""
    def emit(self, record):
        try:
            with open(self.baseFilename + ".lock", "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    # A different runner may have rotated the path since our last emit.
                    if self.stream is not None:
                        self.stream.close()
                        self.stream = None
                    super().emit(record)
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)
        except Exception:
            self.handleError(record)


def configure_boyar_logging(config, log_dir=None):
    directory = Path(log_dir or config.log_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "boyar.log"
    suffix = hashlib.sha256(str(path).encode()).hexdigest()[:16]
    logger = logging.getLogger("collectors.boyar_production." + suffix)
    if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(path)
               for h in logger.handlers):
        handler = LockedRotatingFileHandler(
            path, maxBytes=config.log_max_bytes, backupCount=config.log_backup_count,
            encoding="utf-8", delay=True,
        )
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True
    return logger
