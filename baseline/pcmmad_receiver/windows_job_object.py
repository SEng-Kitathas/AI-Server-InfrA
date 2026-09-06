"""Minimal Windows Job Object primitives for PCMMAD process ownership experiments.

This module is deliberately transport/scheduler agnostic. It exposes OS-native
containment/identity operations only; the canonical execution scheduler remains
the authority for job lifecycle semantics.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from typing import Iterable

if os.name != "nt":
    raise ImportError("windows_job_object is Windows-only")

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

HANDLE = wintypes.HANDLE
DWORD = wintypes.DWORD
BOOL = wintypes.BOOL
LPVOID = wintypes.LPVOID

JOB_OBJECT_ASSIGN_PROCESS = 0x0001
JOB_OBJECT_QUERY = 0x0004
JOB_OBJECT_TERMINATE = 0x0008
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001

JobObjectBasicProcessIdList = 3

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9

class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", DWORD),
        ("SchedulingClass", DWORD),
    ]

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]

class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

kernel32.CreateJobObjectW.argtypes = [LPVOID, wintypes.LPCWSTR]
kernel32.CreateJobObjectW.restype = HANDLE
kernel32.OpenJobObjectW.argtypes = [DWORD, BOOL, wintypes.LPCWSTR]
kernel32.OpenJobObjectW.restype = HANDLE
kernel32.AssignProcessToJobObject.argtypes = [HANDLE, HANDLE]
kernel32.AssignProcessToJobObject.restype = BOOL
kernel32.QueryInformationJobObject.argtypes = [HANDLE, ctypes.c_int, LPVOID, DWORD, ctypes.POINTER(DWORD)]
kernel32.QueryInformationJobObject.restype = BOOL
kernel32.SetInformationJobObject.argtypes = [HANDLE, ctypes.c_int, LPVOID, DWORD]
kernel32.SetInformationJobObject.restype = BOOL
kernel32.TerminateJobObject.argtypes = [HANDLE, wintypes.UINT]
kernel32.TerminateJobObject.restype = BOOL
kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
kernel32.OpenProcess.restype = HANDLE
kernel32.GetProcessTimes.argtypes = [HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME)]
kernel32.GetProcessTimes.restype = BOOL
kernel32.CloseHandle.argtypes = [HANDLE]
kernel32.CloseHandle.restype = BOOL


def _raise_last_error(operation: str) -> None:
    code = ctypes.get_last_error()
    raise OSError(code, f"{operation} failed", None, code)


@dataclass
class JobObjectHandle:
    value: int
    name: str

    def close(self) -> None:
        if self.value:
            if not kernel32.CloseHandle(HANDLE(self.value)):
                _raise_last_error("CloseHandle(job)")
            self.value = 0

    def __enter__(self) -> "JobObjectHandle":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def create_named_job(name: str) -> JobObjectHandle:
    if not name or "\\" not in name:
        # Explicit Local\ namespace avoids collisions with ordinary object names.
        name = f"Local\\{name}"
    ctypes.set_last_error(0)
    handle = kernel32.CreateJobObjectW(None, name)
    if not handle:
        _raise_last_error("CreateJobObjectW")
    error = ctypes.get_last_error()
    if error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        raise FileExistsError(error, f"Job Object already exists: {name}")
    return JobObjectHandle(int(handle), name)


def open_named_job(name: str, *, terminate: bool = True) -> JobObjectHandle:
    access = JOB_OBJECT_QUERY | (JOB_OBJECT_TERMINATE if terminate else 0)
    handle = kernel32.OpenJobObjectW(access, False, name)
    if not handle:
        _raise_last_error("OpenJobObjectW")
    return JobObjectHandle(int(handle), name)



def set_kill_on_close(job: JobObjectHandle, enabled: bool = True) -> None:
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE if enabled else 0
    if not kernel32.SetInformationJobObject(
        HANDLE(job.value),
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        _raise_last_error("SetInformationJobObject(KILL_ON_JOB_CLOSE)")

def assign_pid(job: JobObjectHandle, pid: int) -> None:
    access = PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION
    process = kernel32.OpenProcess(access, False, int(pid))
    if not process:
        _raise_last_error("OpenProcess(assign)")
    try:
        if not kernel32.AssignProcessToJobObject(HANDLE(job.value), process):
            _raise_last_error("AssignProcessToJobObject")
    finally:
        kernel32.CloseHandle(process)


def query_process_ids(job: JobObjectHandle) -> list[int]:
    # Small PCMMAD jobs normally have few descendants, but grow until the API says
    # every assigned PID fits instead of silently truncating.
    slots = 16
    ptr_size = ctypes.sizeof(ctypes.c_void_p)
    header_size = 8
    while slots <= 16384:
        size = header_size + slots * ptr_size
        buffer = ctypes.create_string_buffer(size)
        returned = DWORD(0)
        ok = kernel32.QueryInformationJobObject(
            HANDLE(job.value),
            JobObjectBasicProcessIdList,
            ctypes.byref(buffer),
            size,
            ctypes.byref(returned),
        )
        # Header is two DWORDs followed by ULONG_PTR[] (8-byte aligned at offset 8).
        assigned = DWORD.from_buffer(buffer, 0).value
        listed = DWORD.from_buffer(buffer, 4).value
        if ok and listed >= assigned:
            result: list[int] = []
            array_type = ctypes.c_size_t * listed
            values = array_type.from_buffer(buffer, header_size)
            for value in values:
                if value:
                    result.append(int(value))
            return result
        if ok and listed < assigned:
            slots = max(slots * 2, assigned)
            continue
        error = ctypes.get_last_error()
        # ERROR_MORE_DATA=234 is expected for undersized PID buffers.
        if error == 234:
            slots *= 2
            continue
        raise OSError(error, "QueryInformationJobObject failed", None, error)
    raise RuntimeError("job object PID list exceeded safety ceiling")


def terminate(job: JobObjectHandle, exit_code: int = 0xC000013A) -> None:
    if not kernel32.TerminateJobObject(HANDLE(job.value), int(exit_code) & 0xFFFFFFFF):
        _raise_last_error("TerminateJobObject")


def process_creation_time_100ns(pid: int) -> int:
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not process:
        _raise_last_error("OpenProcess(query)")
    try:
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(process, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
            _raise_last_error("GetProcessTimes")
        return (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
    finally:
        kernel32.CloseHandle(process)
