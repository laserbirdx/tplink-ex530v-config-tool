import ctypes
from ctypes import wintypes
from hashlib import md5
import os
import struct
import subprocess
import sys

try:
    from Cryptodome.Cipher import DES
except ImportError:
    if getattr(sys, "frozen", False):
        raise
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome"])
    from Cryptodome.Cipher import DES

KEY = b"\x40\xbb\xc6\x6d\xcb\x5a\x1d\xfe"


def compress(src):
    if src[-1]:
        src += b"\0"
    size = len(src)
    hash_table = [0] * 0x2000
    dst = bytearray(struct.pack("<I", size))
    dst.append(src[0])

    s_p, s_ph = 1, 0
    d_pb, d_p = 5, 7
    bc, db = 0x10, 0
    dst.extend(b"\0\0")

    def put_bit(bit):
        nonlocal bc, db, d_p, d_pb
        if bc:
            bc -= 1
        else:
            struct.pack_into("H", dst, d_pb, db)
            d_pb, d_p = d_p, d_p + 2
            dst.extend(b"\0\0")
            bc = 0xF
        db = (bit + (db << 1)) & 0xFFFF

    def put_ld(bits):
        ldb = bits >> 1
        while True:
            lb = (ldb - 1) & ldb
            if not lb:
                break
            ldb = lb
        put_bit(int(ldb & bits > 0))
        ldb >>= 1
        while ldb:
            put_bit(1)
            put_bit(int(ldb & bits > 0))
            ldb >>= 1
        put_bit(0)

    def hash_key(offset):
        b4 = src[offset : offset + 4]
        hk = 0
        for b in b4[:3]:
            hk = (hk + b) * 0x13D
        return (hk + b4[3]) & 0x1FFF

    buffer_countdown = size - 1
    while buffer_countdown > 4:
        while s_ph < s_p:
            hash_table[hash_key(s_ph)] = s_ph
            s_ph += 1
        hit = hash_table[hash_key(s_p)]
        count = 0
        if hit:
            while src[hit + count] == src[s_p + count]:
                count += 1
                if count == buffer_countdown:
                    break
            if count >= 4:
                offset = s_p - hit - 1
                put_bit(1)
                put_ld(count - 2)
                put_ld((offset >> 8) + 2)
                dst.append(offset & 0xFF)
                d_p += 1
                buffer_countdown -= count
                s_p += count
                continue
        put_bit(0)
        dst.append(src[s_p])
        s_p, d_p = s_p + 1, d_p + 1
        buffer_countdown -= 1

    while buffer_countdown:
        put_bit(0)
        dst.append(src[s_p])
        s_p, d_p = s_p + 1, d_p + 1
        buffer_countdown -= 1

    struct.pack_into("H", dst, d_pb, (db << bc) & 0xFFFF)
    return dst[:d_p]


def uncompress(src):
    block16_countdown, block16_dict_bits, s_p, d_p = 0, 0, 4, 0

    def get_bit():
        nonlocal block16_countdown, block16_dict_bits, s_p
        if block16_countdown:
            block16_countdown -= 1
        else:
            block16_dict_bits = struct.unpack_from("H", src, s_p)[0]
            s_p, block16_countdown = s_p + 2, 0xF
        block16_dict_bits = block16_dict_bits << 1
        return 1 if block16_dict_bits & 0x10000 else 0

    def get_dict_ld():
        bits = 1
        while True:
            bits = (bits << 1) + get_bit()
            if not get_bit():
                break
        return bits

    size = struct.unpack_from("<I", src, 0)[0]
    dst = bytearray(size)
    dst[d_p] = src[s_p]
    s_p, d_p = s_p + 1, d_p + 1
    while d_p < size:
        if get_bit():
            num_chars = get_dict_ld() + 2
            offset = d_p - (((get_dict_ld() - 2) << 8) + src[s_p] + 1)
            s_p += 1
            for _ in range(num_chars):
                dst[d_p] = dst[offset]
                d_p, offset = d_p + 1, offset + 1
        else:
            dst[d_p] = src[s_p]
            s_p, d_p = s_p + 1, d_p + 1
    return dst


def _default_output_path(inf):
    base, ext = os.path.splitext(inf)
    if ext.lower() == ".bin":
        return base + ".xml"
    candidate = base + ".bin"
    if os.path.abspath(candidate) == os.path.abspath(inf) or os.path.exists(candidate):
        return base + "_repacked.bin"
    return candidate


def _win32_file_dialog(save=False, default_path="", title="", filter_spec=""):
    if os.name != "nt":
        return None

    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", ctypes.c_void_p),
            ("lpstrCustomFilter", ctypes.c_void_p),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", ctypes.c_void_p),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", ctypes.c_void_p),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]

    filter_buf = ctypes.create_unicode_buffer(filter_spec, len(filter_spec) + 2)
    buf = ctypes.create_unicode_buffer(default_path, 1024)
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.lpstrFilter = ctypes.addressof(filter_buf)
    ofn.nFilterIndex = 1
    ofn.lpstrFile = ctypes.addressof(buf)
    ofn.nMaxFile = 1024
    ofn.lpstrTitle = title
    if save:
        ofn.Flags = 0x00000002 | 0x00000800 | 0x00000008  # OFN_OVERWRITEPROMPT | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR
        ok = ctypes.windll.comdlg32.GetSaveFileNameW(ctypes.byref(ofn))
    else:
        ofn.Flags = 0x00001000 | 0x00000800 | 0x00000008  # OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR
        ok = ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
    return buf.value if ok else None


def _notify(message, title="TP-Link EX530v Config Tool", quiet=False, is_error=False):
    if quiet or os.name != "nt":
        return
    flags = 0x10 if is_error else 0x40
    ctypes.windll.user32.MessageBoxW(0, message, title, flags)


def process_file(inf, outf, quiet=False):
    crypto = DES.new(KEY, DES.MODE_ECB)

    if inf.lower().endswith(".bin"):
        print(f"[*] Decrypting & decompressing: {inf} -> {outf}")
        with open(inf, "rb") as f:
            data = f.read()
        if len(data) < 24 or len(data) % 8 != 0:
            raise ValueError("Invalid .bin file size (must be a multiple of 8 bytes and >= 24 bytes).")
        decrypted = crypto.decrypt(data)
        decrypted_payload = decrypted[16:]
        result = uncompress(decrypted_payload)
        with open(outf, "wb") as f:
            f.write(result)
        print(f"[+] Done! Extracted {len(result)} bytes to: {outf}")
        _notify(
            f"Decryption & decompression completed!\n\nOutput: {outf}\n\nPowered by BYF Support (https://techolay.net)",
            "Operation Complete",
            quiet=quiet,
        )
    else:
        print(f"[*] Compressing & encrypting: {inf} -> {outf}")
        with open(inf, "rb") as f:
            xml_content = f.read()
        if not xml_content:
            raise ValueError("Input XML file is empty.")
        compressed_data = compress(xml_content)
        md5_hash = md5(compressed_data).digest()
        full_data = md5_hash + compressed_data
        if len(full_data) % 8:
            full_data += b"\0" * (8 - (len(full_data) % 8))
        encrypted_data = crypto.encrypt(bytes(full_data))
        with open(outf, "wb") as f:
            f.write(encrypted_data)
        print(f"[+] Done! Wrote {len(encrypted_data)} bytes to: {outf}")
        _notify(
            f"Compression & encryption completed!\n\nOutput: {outf}\n\nPowered by BYF Support (https://techolay.net)",
            "Operation Complete",
            quiet=quiet,
        )


def main():
    args = [a for a in sys.argv[1:] if a not in ("-q", "--quiet")]
    quiet = len(args) != len(sys.argv[1:])

    if any(a in ("-h", "--help") for a in args):
        prog = os.path.basename(sys.argv[0])
        print(f"Usage: {prog} [-q|--quiet] <input.bin|input.xml> [output.xml|output.bin]")
        return

    if len(args) == 0:
        if getattr(sys, "frozen", False) and os.name == "nt":
            inf = _win32_file_dialog(
                save=False,
                title="Select TP-Link EX530v Backup (.bin) or Config (.xml)",
                filter_spec="TP-Link Config Files (*.bin;*.xml)\0*.bin;*.xml\0All Files (*.*)\0*.*\0\0",
            )
            if not inf:
                return
            suggested_out = _default_output_path(inf)
            is_bin = inf.lower().endswith(".bin")
            out_filter = (
                "XML Configuration (*.xml)\0*.xml\0All Files (*.*)\0*.*\0\0"
                if is_bin
                else "TP-Link Backup (*.bin)\0*.bin\0All Files (*.*)\0*.*\0\0"
            )
            outf = _win32_file_dialog(
                save=True,
                default_path=suggested_out,
                title="Save Output File As",
                filter_spec=out_filter,
            )
            if not outf:
                return
        else:
            prog = os.path.basename(sys.argv[0])
            print(f"Usage: python {prog} [-q|--quiet] <input.bin|input.xml> [output.xml|output.bin]")
            return
    elif len(args) == 1:
        inf = args[0]
        outf = _default_output_path(inf)
    else:
        inf, outf = args[0], args[1]

    try:
        process_file(inf, outf, quiet=quiet)
    except Exception as exc:
        print(f"[!] Error: {exc}", file=sys.stderr)
        _notify(f"Operation failed:\n{exc}", "TP-Link EX530v Config Tool - Error", quiet=quiet, is_error=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
