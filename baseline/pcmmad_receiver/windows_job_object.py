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

JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9

JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x00000001
JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP = 0x00000004
JobObjectCpuRateControlInformation = 15

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

class JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("ControlFlags", DWORD),
        ("CpuRate", DWORD),
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
    # Preserve any already-applied memory/process limits. KILL_ON_JOB_CLOSE is one
    # bit in the same ExtendedLimitInformation structure; writing a fresh zeroed
    # structure here would silently erase the resource envelope.
    info = _query_extended_limits(job)
    flags = int(info.BasicLimitInformation.LimitFlags)
    if enabled:
        flags |= JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    else:
        flags &= ~JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    info.BasicLimitInformation.LimitFlags = flags
    if not kernel32.SetInformationJobObject(
        HANDLE(job.value),
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        _raise_last_error("SetInformationJobObject(KILL_ON_JOB_CLOSE)")


def _query_extended_limits(job: JobObjectHandle) -> JOBOBJECT_EXTENDED_LIMIT_INFORMATION:
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    returned = DWORD(0)
    if not kernel32.QueryInformationJobObject(
        HANDLE(job.value),
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
        ctypes.byref(returned),
    ):
        _raise_last_error("QueryInformationJobObject(ExtendedLimitInformation)")
    return info


def _query_cpu_limits(job: JobObjectHandle) -> JOBOBJECT_CPU_RATE_CONTROL_INFORMATION:
    info = JOBOBJECT_CPU_RATE_CONTROL_INFORMATION()
    returned = DWORD(0)
    if not kernel32.QueryInformationJobObject(
        HANDLE(job.value),
        JobObjectCpuRateControlInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
        ctypes.byref(returned),
    ):
        _raise_last_error("QueryInformationJobObject(CpuRateControlInformation)")
    return info


def configure_resource_envelope(
    job: JobObjectHandle,
    *,
    kill_on_close: bool = True,
    process_memory_limit_bytes: int | None = None,
    job_memory_limit_bytes: int | None = None,
    active_process_limit: int | None = None,
    cpu_rate_percent: int | None = None,
) -> dict[str, int | bool | None]:
    """Apply and read back an OS-enforced Job Object resource envelope.

    Limits apply to the whole Job Object membership. In PCMMAD async execution
    that includes the worker capsule plus the user process tree.
    """

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    flags = 0
    if kill_on_close:
        flags |= JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if process_memory_limit_bytes is not None:
        value = int(process_memory_limit_bytes)
        if value <= 0:
            raise ValueError("process_memory_limit_bytes must be > 0")
        info.ProcessMemoryLimit = value
        flags |= JOB_OBJECT_LIMIT_PROCESS_MEMORY
    if job_memory_limit_bytes is not None:
        value = int(job_memory_limit_bytes)
        if value <= 0:
            raise ValueError("job_memory_limit_bytes must be > 0")
        info.JobMemoryLimit = value
        flags |= JOB_OBJECT_LIMIT_JOB_MEMORY
    if active_process_limit is not None:
        value = int(active_process_limit)
        if value <= 0:
            raise ValueError("active_process_limit must be > 0")
        info.BasicLimitInformation.ActiveProcessLimit = value
        flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
    info.BasicLimitInformation.LimitFlags = flags
    if not kernel32.SetInformationJobObject(
        HANDLE(job.value),
        JobObjectExtendedLimitInformation,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        _raise_last_error("SetInformationJobObject(ResourceEnvelope)")

    if cpu_rate_percent is not None:
        percent = int(cpu_rate_percent)
        if percent < 1 or percent > 100:
            raise ValueError("cpu_rate_percent must be between 1 and 100")
        cpu = JOBOBJECT_CPU_RATE_CONTROL_INFORMATION()
        cpu.ControlFlags = JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP
        cpu.CpuRate = percent * 100  # Windows uses 1/100 of one percent.
        if not kernel32.SetInformationJobObject(
            HANDLE(job.value),
            JobObjectCpuRateControlInformation,
            ctypes.byref(cpu),
            ctypes.sizeof(cpu),
        ):
            _raise_last_error("SetInformationJobObject(CpuRateControlInformation)")
    return query_resource_envelope(job)


def query_resource_envelope(job: JobObjectHandle) -> dict[str, int | bool | None]:
    extended = _query_extended_limits(job)
    cpu = _query_cpu_limits(job)
    flags = int(extended.BasicLimitInformation.LimitFlags)
    cpu_flags = int(cpu.ControlFlags)
    cpu_enabled = bool(cpu_flags & JOB_OBJECT_CPU_RATE_CONTROL_ENABLE)
    cpu_hard_cap = bool(cpu_flags & JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP)
    return {
        "kill_on_close": bool(flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE),
        "process_memory_limit_bytes": (
            int(extended.ProcessMemoryLimit)
            if flags & JOB_OBJECT_LIMIT_PROCESS_MEMORY
            else None
        ),
        "job_memory_limit_bytes": (
            int(extended.JobMemoryLimit)
            if flags & JOB_OBJECT_LIMIT_JOB_MEMORY
            else None
        ),
        "active_process_limit": (
            int(extended.BasicLimitInformation.ActiveProcessLimit)
            if flags & JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            else None
        ),
        "cpu_rate_percent": (
            int(cpu.CpuRate) // 100 if cpu_enabled and cpu_hard_cap else None
        ),
    }

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
