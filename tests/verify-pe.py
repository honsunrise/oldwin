#!/usr/bin/env python3
"""Check a built link-smoke executable's PE headers and static imports.

Only the ordinary import directory is inspected: delay imports and DLLs loaded
at runtime are outside this check. Passing does not prove old-Windows runtime
compatibility. RVA reads must be backed by file bytes, not virtual zero-fill.
"""

import argparse
from pathlib import Path
import struct
import sys


class PE:
    def __init__(self, data):
        self.data = data
        self.require(self.bytes_at(0, 2) == b"MZ", "missing DOS signature")
        pe_offset = self.unpack("<I", 0x3C)[0]
        self.require(self.bytes_at(pe_offset, 4) == b"PE\0\0", "missing PE signature")
        coff = pe_offset + 4
        self.machine, section_count = self.unpack("<HH", coff)
        optional_size = self.unpack("<H", coff + 16)[0]
        optional = coff + 20
        self.bytes_at(optional, optional_size)
        magic = self.unpack("<H", optional)[0]
        if magic == 0x10B:
            self.pointer_size = 4
            directory_offset = 96
            directory_count_offset = 92
        elif magic == 0x20B:
            self.pointer_size = 8
            directory_offset = 112
            directory_count_offset = 108
        else:
            raise ValueError(f"unsupported optional-header magic 0x{magic:04x}")
        self.require(optional_size >= directory_offset, "truncated optional header")
        self.subsystem_version = self.unpack("<HH", optional + 48)
        self.subsystem = self.unpack("<H", optional + 68)[0]
        self.header_size = self.unpack("<I", optional + 60)[0]
        self.require(self.header_size <= len(data), "headers extend past end of file")
        directory_count = self.unpack("<I", optional + directory_count_offset)[0]
        self.require(
            directory_count <= (optional_size - directory_offset) // 8,
            "data directories extend past optional header",
        )
        self.import_rva, self.import_size = (0, 0)
        if directory_count > 1:
            self.import_rva, self.import_size = self.unpack(
                "<II", optional + directory_offset + 8
            )
        section_table = optional + optional_size
        self.require(
            section_table + section_count * 40 <= self.header_size,
            "section table extends past headers",
        )
        self.sections = []
        for index in range(section_count):
            section = section_table + index * 40
            virtual_size, rva, raw_size, raw_offset = self.unpack("<IIII", section + 8)
            self.require(
                rva + max(virtual_size, raw_size) <= 0x100000000,
                "section RVA range overflows",
            )
            if raw_size:
                self.bytes_at(raw_offset, raw_size)
            self.sections.append((rva, raw_size, raw_offset))

    @staticmethod
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def bytes_at(self, offset, size):
        self.require(
            offset >= 0 and size >= 0 and offset + size <= len(self.data),
            f"file read outside bounds at 0x{offset:x} ({size} bytes)",
        )
        return self.data[offset:offset + size]

    def unpack(self, fmt, offset):
        return struct.unpack(fmt, self.bytes_at(offset, struct.calcsize(fmt)))

    def rva_span(self, rva):
        """Return file offset and remaining contiguous file-backed RVA bytes."""
        self.require(0 < rva <= 0xFFFFFFFF, f"invalid RVA 0x{rva:x}")
        matches = []
        if rva < self.header_size:
            matches.append((rva, self.header_size - rva))
        for start, size, offset in self.sections:
            if start <= rva < start + size:
                delta = rva - start
                matches.append((offset + delta, size - delta))
        self.require(len(matches) == 1, f"unmapped or ambiguous RVA 0x{rva:x}")
        return matches[0]

    def rva_unpack(self, fmt, rva):
        offset, remaining = self.rva_span(rva)
        size = struct.calcsize(fmt)
        self.require(size <= remaining, f"RVA read crosses raw section at 0x{rva:x}")
        return self.unpack(fmt, offset)

    def string_at_rva(self, rva):
        offset, remaining = self.rva_span(rva)
        end = self.data.find(b"\0", offset, offset + remaining)
        self.require(end != -1, f"unterminated import name at RVA 0x{rva:x}")
        name = self.data[offset:end].decode("ascii")
        self.require(bool(name), f"empty import name at RVA 0x{rva:x}")
        return name

    def imports(self):
        """Return DLL names and named imports, accepting ordinal-only entries."""
        self.require(self.import_rva != 0 and self.import_size >= 20, "missing import table")
        self.require(
            self.import_rva + self.import_size <= 0x100000000,
            "import directory RVA range overflows",
        )
        dlls = set()
        names = set()
        pointer_format = "<I" if self.pointer_size == 4 else "<Q"
        ordinal_flag = 1 << (self.pointer_size * 8 - 1)
        for relative in range(0, self.import_size - 19, 20):
            descriptor = self.rva_unpack("<IIIII", self.import_rva + relative)
            if not any(descriptor):
                self.require(bool(dlls), "empty import table")
                return dlls, names
            original_thunk, _, _, name_rva, first_thunk = descriptor
            dlls.add(self.string_at_rva(name_rva).lower())
            # An unbound on-disk image can omit OriginalFirstThunk and use IAT.
            thunk_rva = original_thunk or first_thunk
            _, remaining = self.rva_span(thunk_rva)
            for entry_offset in range(0, remaining - self.pointer_size + 1, self.pointer_size):
                entry = self.rva_unpack(pointer_format, thunk_rva + entry_offset)[0]
                if entry == 0:
                    break
                if entry & ordinal_flag:
                    continue
                self.require(entry <= 0xFFFFFFFF, "import-name RVA exceeds 32 bits")
                self.rva_unpack("<H", entry)  # IMAGE_IMPORT_BY_NAME hint
                names.add(self.string_at_rva(entry + 2))
            else:
                raise ValueError(f"unterminated thunk table for {self.string_at_rva(name_rva)}")
        raise ValueError("unterminated import descriptor table")


def verify(args):
    pe = PE(args.exe.read_bytes())
    machine, pointer_size = {"x86": (0x014C, 4), "x86_64": (0x8664, 8)}[args.arch]
    pe.require(
        pe.machine == machine and pe.pointer_size == pointer_size,
        f"expected {args.arch} machine/PE format, got machine 0x{pe.machine:04x} "
        f"and PE{pe.pointer_size * 8}",
    )
    expected_subsystem = {"console": 3, "windows": 2}[args.subsystem]
    pe.require(
        pe.subsystem == expected_subsystem,
        f"expected {args.subsystem} subsystem ({expected_subsystem}), got {pe.subsystem}",
    )
    expected_version = (5, 1 if args.arch == "x86" else 2) if args.os == "xp" else (6, 0)
    pe.require(
        pe.subsystem_version == expected_version,
        f"expected subsystem version {expected_version[0]}.{expected_version[1]}, "
        f"got {pe.subsystem_version[0]}.{pe.subsystem_version[1]}",
    )
    dlls, names = pe.imports()
    precise_time = "GetSystemTimePreciseAsFileTime"
    if args.os in ("xp", "vista", "win7"):
        pe.require(precise_time not in names, f"{precise_time} still statically imported: thunk missing")
    else:
        pe.require(precise_time in names, f"{precise_time} missing from native import control")
    if args.crt != "none":
        forbidden = sorted(
            dll for dll in dlls
            if dll.startswith("api-ms-win-crt-")
            or (dll.startswith("vcruntime") and dll.endswith(".dll"))
        )
        pe.require(not forbidden, f"VC-LTL CRT import regression: {', '.join(forbidden)}")
        if args.crt == "dynamic":
            expected_crt = "ucrtbase.dll" if args.os == "win10" else "msvcrt.dll"
            pe.require(expected_crt in dlls, f"missing VC-LTL system CRT import: {expected_crt}")
        # VC-LTL static libraries can still import the system CRT. Do not assert
        # that msvcrt.dll/ucrtbase.dll is absent, or require one to be present.
    print(
        f"PE OK: machine=0x{pe.machine:04x} ({args.arch}), "
        f"subsystem={args.subsystem} {pe.subsystem_version[0]}.{pe.subsystem_version[1]}, "
        f"imports={', '.join(sorted(dlls))}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--arch", choices=("x86", "x86_64"), required=True)
    parser.add_argument("--os", choices=("xp", "vista", "win7", "win8", "win10"), required=True)
    parser.add_argument("--crt", choices=("none", "dynamic", "static"), required=True)
    parser.add_argument("--subsystem", choices=("console", "windows"), required=True)
    args = parser.parse_args()
    try:
        verify(args)
    except (OSError, ValueError, struct.error) as error:
        print(f"PE check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
