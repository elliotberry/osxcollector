"""Optional Mach-O extra-data scanner (requires macholib when enabled)."""

from __future__ import annotations

import os
import struct
from typing import Any

try:
    import macholib.MachO as MachO

    HAS_MACHOLIB = True
except ImportError:  # pragma: no cover - optional dependency
    MachO = None  # type: ignore[assignment, misc]
    HAS_MACHOLIB = False


class Kyphosis:
    """Detect appended/extra data in Mach-O binaries."""

    def __init__(self, some_file: str, write_file: bool = False) -> None:
        self.someFile = some_file
        self.extra_data_found = False
        self.supportedfiles = [
            b"\xca\xfe\xba\xbe",  # FAT / universal
            b"\xcf\xfa\xed\xfe",  # 64-bit LE (x86_64 / arm64)
            b"\xce\xfa\xed\xfe",  # 32-bit LE
            b"\xfe\xed\xfa\xcf",  # 64-bit BE
            b"\xfe\xed\xfa\xce",  # 32-bit BE
        ]
        self.dataoff = 0
        self.datasize = 0
        self.beginOffset = 0
        self.endOffset = 0
        self.fat_hdrs: dict[int, dict[str, int]] = {}
        self.extra_data: dict[Any, Any] = {}
        self.writeFile = write_file
        self.last_entry = 0
        self.count = 0
        self.run()

    def run(self) -> bool | None:
        if not HAS_MACHOLIB:
            return None
        if self.check_binary() is not True:
            return None

        assert MachO is not None
        self.aFile = MachO.MachO(self.someFile)

        if self.aFile.fat is None:
            self.find_load_cmds()
            self.check_macho_size()
        else:
            self.make_soap()

        return True if self.extra_data_found else False

    def make_soap(self) -> None:
        with open(self.someFile, "rb") as self.bin:
            self.bin.read(4)
            arch_no = struct.unpack(">I", self.bin.read(4))[0]
            for arch in range(arch_no):
                self.fat_hdrs[arch] = self.fat_header()
            self.end_fat_hdr = self.bin.tell()
            beginning = True
            self.count = 0
            for _hdr, value in self.fat_hdrs.items():
                if beginning:
                    self.beginOffset = self.end_fat_hdr
                    self.endOffset = value["Offset"]
                    self.check_space()
                    self.beginOffset = value["Size"] + value["Offset"]
                    beginning = False
                    self.count += 1
                    continue
                self.endOffset = value["Offset"]
                self.check_space()
                self.beginOffset = value["Size"] + value["Offset"]
                self.count += 1
        self.last_entry = self.beginOffset
        self.check_macho_size()

    def check_space(self) -> None:
        self.bin.seek(self.beginOffset, 0)
        empty_space = self.bin.read(self.endOffset - self.beginOffset)
        if empty_space != len(empty_space) * b"\x00":
            self.extra_data_found = True
            self.extra_data[self.count] = empty_space
            if self.writeFile:
                out_name = f"{os.path.basename(self.someFile)}.extra_data_section{self.count}"
                print(f"Writing to {out_name}")
                with open(out_name, "wb") as handle:
                    handle.write(empty_space)

    def fat_header(self) -> dict[str, int]:
        return {
            "CPU Type": struct.unpack(">I", self.bin.read(4))[0],
            "CPU SubType": struct.unpack(">I", self.bin.read(4))[0],
            "Offset": struct.unpack(">I", self.bin.read(4))[0],
            "Size": struct.unpack(">I", self.bin.read(4))[0],
            "Align": struct.unpack(">I", self.bin.read(4))[0],
        }

    def check_binary(self) -> bool | None:
        with open(self.someFile, "rb") as f:
            magicheader = f.read(4)
            if magicheader in self.supportedfiles:
                return True
        return None

    def find_load_cmds(self) -> None:
        for header in self.aFile.headers:
            for command in header.commands:
                objects = vars(command[1]).get("_objects_", {})
                if "dataoff" in objects:
                    dataoff = objects["dataoff"]
                    datasize = objects.get("datassize", objects.get("datasize", 0))
                    if dataoff > self.dataoff:
                        self.dataoff = dataoff
                        self.datasize = datasize
                if "stroff" in objects:
                    dataoff = objects["stroff"]
                    datasize = objects["strsize"]
                    if dataoff > self.dataoff:
                        self.dataoff = dataoff
                        self.datasize = datasize
                if "fileoff" in objects:
                    dataoff = objects["fileoff"]
                    datasize = objects["filesize"]
                    if dataoff > self.dataoff:
                        self.dataoff = dataoff
                        self.datasize = datasize
        self.last_entry = int(self.datasize + self.dataoff)

    def check_macho_size(self) -> None:
        with open(self.someFile, "rb") as f:
            if os.stat(self.someFile).st_size > self.last_entry:
                f.seek(self.last_entry, 0)
                extra_data_end = f.read()
                self.extra_data_found = True
                self.extra_data["extra_data_end"] = extra_data_end
                if self.writeFile:
                    out_name = f"{os.path.basename(self.someFile)}.extra_data_end"
                    print(f"Writing to {out_name}")
                    with open(out_name, "wb") as handle:
                        handle.write(extra_data_end)


# Historical name used by fileinfo / tests
kyphosis = Kyphosis
