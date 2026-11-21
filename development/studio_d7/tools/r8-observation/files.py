"""Windows-only read adapter for a bounded, manifest-selected local artifact."""
import ctypes
import hashlib
import re
import time
from contextlib import contextmanager
from ctypes import wintypes as w
from pathlib import Path

k = ctypes.WinDLL("kernel32", use_last_error=True)


def api(name, returns, *args):
    fn = getattr(k, name)
    fn.restype, fn.argtypes = returns, args
    return fn


create = api("CreateFileW", w.HANDLE, w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE)
close = api("CloseHandle", w.BOOL, w.HANDLE)
info = api("GetFileInformationByHandle", w.BOOL, w.HANDLE, w.LPVOID)
identity = api("GetFileInformationByHandleEx", w.BOOL, w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD)
final = api("GetFinalPathNameByHandleW", w.DWORD, w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD)
file_type = api("GetFileType", w.DWORD, w.HANDLE)
read = api("ReadFile", w.BOOL, w.HANDLE, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID)


class Info(ctypes.Structure):
    _fields_ = [("attributes", w.DWORD), ("created", w.FILETIME), ("access", w.FILETIME),
                ("written", w.FILETIME), ("volume", w.DWORD), ("high", w.DWORD), ("low", w.DWORD),
                ("links", w.DWORD), ("index_high", w.DWORD), ("index_low", w.DWORD)]


class FileId(ctypes.Structure):
    _fields_ = [("volume", ctypes.c_uint64), ("identifier", ctypes.c_ubyte * 16)]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


@contextmanager
def opened(path, directory, shared_writer=False):
    require(re.fullmatch(r"[A-Za-z]:", path.drive) and path.is_absolute(), "LOCAL_PATH")
    # OPEN_REPARSE_POINT inspects the named object even if the last component is a link.
    flags = 0x00200000 | (0x02000000 if directory else 0)
    handle = create(str(path), 0x80 if directory else 0x80000000, 3 if directory or shared_writer else 1,
                    None, 3, flags, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield handle
    finally:
        close(handle)


def metadata(handle, path, directory):
    basic, fid = Info(), FileId()
    buf = ctypes.create_unicode_buffer(32768)
    n = final(handle, buf, len(buf), 0)
    require(0 < n < len(buf) and buf.value.casefold() == ("\\\\?\\" + str(path)).casefold(), "FINAL_PATH")
    require(file_type(handle) == 1 and info(handle, ctypes.byref(basic)) and
            identity(handle, 18, ctypes.byref(fid), ctypes.sizeof(fid)), "FILE_INFO")
    require(not basic.attributes & 0x400 and bool(basic.attributes & 16) == directory, "UNSAFE_TYPE")
    require(directory or basic.links == 1, "MULTIPLE_LINKS")
    return (f"{fid.volume:016x}", bytes(fid.identifier).hex(), (basic.high << 32) | basic.low)


def hold_directory(stack, path, volume=None):
    meta = metadata(stack.enter_context(opened(path, True)), path, True)
    require(volume is None or volume == meta[0], "VOLUME")
    return meta[0]


def require_wal_header(handle):
    header = ctypes.create_string_buffer(20)
    count = w.DWORD()
    if not read(handle, header, 20, ctypes.byref(count), None):
        raise ctypes.WinError(ctypes.get_last_error())
    require(count.value == 20 and header.raw[:16] == b"SQLite format 3\0" and
            header.raw[18:20] == b"\x02\x02", "EXISTING_WAL_REQUIRED")


def read_held(stack, path, volume, limit, deadline, cancel, keep=False):
    handle = stack.enter_context(opened(path, False))
    before = metadata(handle, path, False)
    require(before[0] == volume and before[2] <= limit, "SIZE_OR_VOLUME")
    buf = ctypes.create_string_buffer(65536)
    count = w.DWORD()
    size, digest, data = 0, hashlib.sha256(), bytearray()
    while True:
        require(not cancel() and time.monotonic() < deadline, "TIME_OR_CANCEL")
        if not read(handle, buf, len(buf), ctypes.byref(count), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if count.value == 0:
            break
        size += count.value
        require(size <= before[2], "SIZE_CHANGED")
        block = buf.raw[:count.value]
        digest.update(block)
        if keep:
            data.extend(block)
    require(metadata(handle, path, False) == before and size == before[2], "IDENTITY_CHANGED")
    return dict(volume=before[0], file_id=before[1], bytes=size, sha256=digest.hexdigest()), bytes(data)
