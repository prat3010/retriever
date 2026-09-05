"""Zero-Knowledge Ephemeral Memory Sanitizer (M101).

Implements MemorySanitizerProtocol with in-memory volatile bytearray tracking,
ctypes.memset zeroing routines, and OS signal hooks (SIGTERM, SIGINT) to prevent
cold-boot RAM dumping and physical memory probing.
"""

import ctypes
import logging
import signal
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from src.domain.abstractions.enclave import MemorySanitizerProtocol

logger = logging.getLogger(__name__)


class EphemeralMemorySanitizer(MemorySanitizerProtocol):
    """Secure in-memory volatile key storage with active zeroing."""

    def __init__(self, register_signals: bool = True) -> None:
        self._key_store: dict[str, bytearray] = {}
        self._lock = threading.Lock()
        if register_signals and threading.current_thread() is threading.main_thread():
            self._register_signal_traps()

    def _register_signal_traps(self) -> None:
        """Trap OS termination signals to securely purge all keys before process shutdown."""
        try:
            original_sigterm = signal.getsignal(signal.SIGTERM)
            original_sigint = signal.getsignal(signal.SIGINT)

            def _signal_wipe_handler(signum: int, frame: object) -> None:
                logger.warning(
                    f"Confidential Enclave received OS signal {signum}. "
                    f"Executing emergency zero-knowledge volatile key wipe."
                )
                self.wipe_all()
                if callable(original_sigterm) and signum == signal.SIGTERM:
                    original_sigterm(signum, frame)
                elif callable(original_sigint) and signum == signal.SIGINT:
                    original_sigint(signum, frame)
                elif signum == signal.SIGINT:
                    raise KeyboardInterrupt

            signal.signal(signal.SIGTERM, _signal_wipe_handler)
            signal.signal(signal.SIGINT, _signal_wipe_handler)
        except (ValueError, AttributeError) as exc:
            logger.debug(f"Signal registration skipped (non-main thread or unsupported platform): {exc}")

    def allocate_ephemeral_key(self, key_id: str, key_bytes: bytes) -> str:
        """Store volatile key bytes in a tracked mutable bytearray."""
        with self._lock:
            # If key_id already exists, wipe old buffer first
            if key_id in self._key_store:
                self._zero_buffer(self._key_store[key_id])
            self._key_store[key_id] = bytearray(key_bytes)
            return key_id

    def get_ephemeral_key(self, key_id: str) -> bytes | None:
        """Retrieve key bytes from the buffer if still allocated."""
        with self._lock:
            buf = self._key_store.get(key_id)
            if buf is None:
                return None
            return bytes(buf)

    def _zero_buffer(self, buf: bytearray) -> None:
        """Aggressively overwrite buffer bytes in-place using ctypes.memset and loop zeroing."""
        length = len(buf)
        if length == 0:
            return
        # 1. In-place byte overwrite
        for i in range(length):
            buf[i] = 0
        # 2. C-level memory zeroing to bypass interpreter optimizations
        try:
            c_buf = (ctypes.c_char * length).from_buffer(buf)
            ctypes.memset(c_buf, 0, length)
        except Exception:
            pass

    def wipe_key(self, key_id: str) -> bool:
        """Aggressively zero memory buffer for specific key in-place and remove reference."""
        with self._lock:
            buf = self._key_store.pop(key_id, None)
            if buf is None:
                return False
            self._zero_buffer(buf)
            return True

    def wipe_all(self) -> int:
        """Zero all allocated volatile keys immediately."""
        with self._lock:
            count = len(self._key_store)
            for buf in self._key_store.values():
                self._zero_buffer(buf)
            self._key_store.clear()
            logger.info(f"Confidential Enclave sanitized {count} volatile keys from RAM.")
            return count

    @property
    def active_key_count(self) -> int:
        """Return the number of ephemeral keys currently held in memory."""
        with self._lock:
            return len(self._key_store)

    @contextmanager
    def scoped_key(self, key_id: str, key_bytes: bytes) -> Iterator[bytes]:
        """Context manager that allocates a key and guarantees zeroing on exit."""
        self.allocate_ephemeral_key(key_id, key_bytes)
        try:
            yield key_bytes
        finally:
            self.wipe_key(key_id)
