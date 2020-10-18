import os
from segtypes.segment import N64Segment
from pathlib import Path
from util import Yay0decompress
import json

def decode_null_terminated_ascii(data):
    length = 0
    for byte in data:
        if byte == 0:
            break
        length += 1

    return data[:length].decode('ascii')

class N64SegPaperMarioMapFS(N64Segment):
    def split(self, rom_bytes, base_path):
        paths = self.config.get("paths", {})

        fs_dir = Path(base_path, self.name)
        fs_dir.mkdir(parents=True, exist_ok=True)

        data = rom_bytes[self.rom_start : self.rom_end]

        filesystem = {
            "title": decode_null_terminated_ascii(data[0:0x20]),
            "files": [],
        }

        asset_idx = 0
        while True:
            asset_data = data[0x20 + asset_idx * 0x1C :]

            name = decode_null_terminated_ascii(asset_data[0:])
            if name == "end_data":
                break

            offset            = int.from_bytes(asset_data[0x10:0x14], byteorder="big")
            size              = int.from_bytes(asset_data[0x14:0x18], byteorder="big")
            decompressed_size = int.from_bytes(asset_data[0x18:0x1C], byteorder="big")

            is_compressed = size != decompressed_size

            path = paths.get(name, "{}.bin".format(name))
            Path(fs_dir, path).parent.mkdir(parents=True, exist_ok=True)

            filesystem["files"].append({ "path": path, "compress": is_compressed })

            with open(os.path.join(fs_dir, path), "wb") as f:
                bytes = rom_bytes[self.rom_start + 0x20 + offset : self.rom_start + 0x20 + offset + size]
                if is_compressed:
                    decompressed_bytes = Yay0decompress.decompress_yay0(bytes)
                    f.write(decompressed_bytes)
                else:
                    f.write(bytes)

            asset_idx += 1

        with open(os.path.join(base_path, "{}.json".format(self.name)), "w") as f:
            json.dump(filesystem, f, indent=4)


    def get_ld_section(self):
        section_name = ".data_{}".format(self.rom_start)

        lines = []
        lines.append("    /* 0x00000000 {:X}-{:X} [{:X}] */".format(self.rom_start, self.rom_end, self.rom_end - self.rom_start))
        lines.append("    {} 0x{:X} : AT(0x{:X}) ".format(section_name, self.rom_start, self.rom_start) + "{")
        lines.append("        build/{}.o(.data);".format(self.name))
        lines.append("    }")
        lines.append("")
        lines.append("")
        return "\n".join(lines)
        return ""


    @staticmethod
    def create_makefile_target():
        return ""
