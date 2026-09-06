"""Dependency-free Windows recursive directory-change watcher.

This module is deliberately transport-like: it reports filesystem edges and owns no
execution/job semantics.  Callers must treat notifications as derived hints and retain
a separate authoritative resynchronization path.
"""

from __future__ import annotations

import ctypes
import os
import struct
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
FILE_NOTIFY_CHANGE_DIR_NAME = 0x00000002

FILE_ACTION_ADDED = 0x00000001
FILE_ACTION_REMOVED = 0x00000002
FILE_ACTION_MODIFIED = 0x00000003
FILE_ACTION_RENAMED_OLD_NAME = 0x00000004
FILE_ACTION_RENAMED_NEW_NAME = 0x00000005

ERROR_OPERATION_ABORTED = 995
ERROR_INVALID_HANDLE = 6


@dataclass(frozen=True)
class DirectoryChangeEvent:
    action: int
    relative_path: str


class WindowsRecursiveDirectoryWatcher:
    """One-handle recursive watcher backed by ``ReadDirectoryChangesW``.

    The watcher intentionally emits filename/directory-name edges only.  PCMMAD's
    execution metadata and worker receipts use atomic temp-file replacement, so name
    changes provide the required wake signal without turning stdout/stderr writes into
    an event storm.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        on_events: Callable[[list[DirectoryChangeEvent]], None],
        on_overflow: Callable[[], None],
        on_error: Callable[[str], None],
        buffer_size: int = 65536,
    ) -> None:
        if os.name != "nt":
            raise RuntimeError("WindowsRecursiveDirectoryWatcher requires Windows")
        self.root = Path(root).resolve()
        self.on_events = on_events
        self.on_overflow = on_overflow
        self.on_error = on_error
        self.buffer_size = max(4096, int(buffer_size))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._handle: int | None = None
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_api()

    def _configure_api(self) -> None:
        from ctypes import wintypes

        handle_t = ctypes.c_void_p
        self._handle_t = handle_t
        self._kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            handle_t,
        ]
        self._kernel32.CreateFileW.restype = handle_t
        self._kernel32.ReadDirectoryChangesW.argtypes = [
            handle_t,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self._kernel32.ReadDirectoryChangesW.restype = wintypes.BOOL
        self._kernel32.CancelIoEx.argtypes = [handle_t, ctypes.c_void_p]
        self._kernel32.CancelIoEx.restype = wintypes.BOOL
        self._kernel32.CloseHandle.argtypes = [handle_t]
        self._kernel32.CloseHandle.restype = wintypes.BOOL

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if not self.root.is_dir():
            raise FileNotFoundError(f"watch root does not exist: {self.root}")

        file_list_directory = 0x0001
        share_read_write_delete = 0x0001 | 0x0002 | 0x0004
        open_existing = 3
        file_flag_backup_semantics = 0x02000000
        raw_handle = self._kernel32.CreateFileW(
            str(self.root),
            file_list_directory,
            share_read_write_delete,
            None,
            open_existing,
            file_flag_backup_semantics,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        handle_value = raw_handle if isinstance(raw_handle, int) else raw_handle.value
        if handle_value in (None, 0, -1, invalid_handle):
            error = ctypes.get_last_error()
            raise OSError(error, f"CreateFileW failed for watch root {self.root}")

        self._handle = int(handle_value)
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="pcmmad-windows-directory-watch",
            daemon=True,
        )
        self._thread.start()

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _emit_error(self, message: str) -> None:
        try:
            self.on_error(message[:500])
        except Exception:
            pass

    def _emit_overflow(self) -> None:
        try:
            self.on_overflow()
        except Exception as exc:
            self._emit_error(f"watch overflow callback failed: {type(exc).__name__}: {exc}")

    def _emit_events(self, events: list[DirectoryChangeEvent]) -> None:
        if not events:
            return
        try:
            self.on_events(events)
        except Exception as exc:
            self._emit_error(f"watch event callback failed: {type(exc).__name__}: {exc}")

    @staticmethod
    def _parse_events(data: bytes) -> list[DirectoryChangeEvent]:
        events: list[DirectoryChangeEvent] = []
        offset = 0
        size = len(data)
        while offset + 12 <= size:
            next_offset, action, name_bytes = struct.unpack_from("<III", data, offset)
            name_start = offset + 12
            name_end = name_start + int(name_bytes)
            if name_end > size or name_bytes % 2:
                raise ValueError("malformed FILE_NOTIFY_INFORMATION payload")
            relative_path = data[name_start:name_end].decode("utf-16-le")
            events.append(DirectoryChangeEvent(action=int(action), relative_path=relative_path))
            if next_offset == 0:
                break
            if next_offset < 12:
                raise ValueError("invalid FILE_NOTIFY_INFORMATION next offset")
            offset += int(next_offset)
        return events

    def _run(self) -> None:
        from ctypes import wintypes

        notify_filter = FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_DIR_NAME
        while not self._stop.is_set():
            handle_value = self._handle
            if handle_value is None:
                break
            buffer = ctypes.create_string_buffer(self.buffer_size)
            returned = wintypes.DWORD()
            ok = self._kernel32.ReadDirectoryChangesW(
                self._handle_t(handle_value),
                buffer,
                len(buffer),
                True,
                notify_filter,
                ctypes.byref(returned),
                None,
                None,
            )
            if not ok:
                error = ctypes.get_last_error()
                if self._stop.is_set() and error in {ERROR_OPERATION_ABORTED, ERROR_INVALID_HANDLE}:
                    break
                self._emit_error(f"ReadDirectoryChangesW failed: winerror={error}")
                break
            if returned.value == 0:
                # Windows reports a zero-byte successful read when the notification
                # buffer cannot represent the change set.  The caller must resync.
                self._emit_overflow()
                continue
            try:
                events = self._parse_events(buffer.raw[: returned.value])
            except (UnicodeError, ValueError, struct.error) as exc:
                self._emit_error(f"watch payload parse failed: {type(exc).__name__}: {exc}")
                self._emit_overflow()
                continue
            self._emit_events(events)

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        handle_value = self._handle
        if handle_value is not None:
            # Cancellation is best-effort; ERROR_NOT_FOUND simply means no read is
            # currently pending.
            self._kernel32.CancelIoEx(self._handle_t(handle_value), None)
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(0.0, float(timeout)))
        self._thread = None
        if handle_value is not None:
            self._kernel32.CloseHandle(self._handle_t(handle_value))
        self._handle = None
