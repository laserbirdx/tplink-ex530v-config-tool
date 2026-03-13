import sys
import struct
import subprocess
import ctypes
from hashlib import md5

try:
    from Crypto.Cipher import DES
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome"])
    from Crypto.Cipher import DES

PRODUCT_ID = 1187982593
BASE_KEY = bytearray([0x74, 0x8d, 0xa5, 0x0b, 0xf9, 0x3e, 0x2d, 0xcf])

def derive_key():
    ds = format(PRODUCT_ID, '08x')
    fk = bytearray(8)
    for i in range(8):
        fk[i] = BASE_KEY[i] ^ ord(ds[i])
    return bytes(fk)

def compress_data(src):
    if src[-1]: src += b'\0'
    size = len(src)
    dst = bytearray(struct.pack('<I', size))
    dst.append(src[0])
    hash_table = [-1] * 8192
    s_p, s_ph, d_pb, d_p, bc, db = 1, 0, 5, 7, 0, 0
    dst.extend(b'\0\0')

    def put_bit(bit):
        nonlocal bc, db, d_p, d_pb
        if bc < 15: bc += 1
        else:
            struct.pack_into('<H', dst, d_pb, db)
            d_pb, d_p = d_p, d_p + 2
            dst.extend(b'\0\0')
            bc = 0
        db = (db >> 1) | (0x8000 if bit else 0)

    def put_ld(bits):
        ldb = bits >> 1
        while True:
            lb = (ldb - 1) & ldb
            if not lb: break
            ldb = lb
        put_bit(int(ldb & bits > 0))
        ldb >>= 1
        while ldb:
            put_bit(1)
            put_bit(int(ldb & bits > 0))
            ldb >>= 1
        put_bit(0)

    def get_hk(o):
        b4 = src[o:o+4]
        if len(b4) < 4: return 0
        hk = 0
        for b in b4[:3]: hk = (hk + b) * 0x13d
        return (hk + b4[3]) & 0x1FFF

    while s_p < size:
        while s_ph < s_p:
            hash_table[get_hk(s_ph)] = s_ph
            s_ph += 1
        hit = hash_table[get_hk(s_p)]
        count = 0
        if hit != -1 and s_p - hit < 8192:
            while s_p + count < size and src[hit + count] == src[s_p + count] and count < 255:
                count += 1
        if count >= 3:
            put_bit(1)
            offset = s_p - hit - 1
            put_ld(count - 2)
            put_ld((offset >> 8) + 2)
            dst.append(offset & 0xFF)
            d_p += 1
            s_p += count
        else:
            put_bit(0)
            dst.append(src[s_p])
            d_p += 1
            s_p += 1
    struct.pack_into('<H', dst, d_pb, db >> (15 - bc))
    while len(dst) % 8: dst.append(0)
    return dst

def uncompress_data(src):
    sp, dp, bc, db = 0, 0, 0, 0
    def get_bit():
        nonlocal bc, db, sp
        if bc > 0: bc -= 1
        else:
            db = struct.unpack_from('<H', src, sp)[0]
            sp, bc = sp + 2, 15
        bit = 1 if db & 0x0001 else 0
        db >>= 1
        return bit
    def get_ld():
        bits = 1
        while True:
            bits = (bits << 1) + get_bit()
            if not get_bit(): break
        return bits
    sz = struct.unpack_from('<I', src, sp)[0]
    sp, dst = sp + 4, bytearray(sz)
    if sp < len(src):
        dst[dp] = src[sp]
        sp, dp = sp + 1, dp + 1
    while dp < sz:
        if get_bit():
            n, m = get_ld() + 2, (get_ld() - 2) << 8
            l = src[sp]
            sp += 1
            o = dp - (l + 1 + m)
            for _ in range(n):
                if dp < sz:
                    dst[dp] = dst[o]
                    dp, o = dp + 1, o + 1
        else:
            dst[dp] = src[sp]
            sp, dp = sp + 1, dp + 1
    return dst

def main():
    if len(sys.argv) < 3:
        print("Kullanim: python dec.py <giris> <cikis>")
        return
    inf, outf = sys.argv[1], sys.argv[2]
    crypto = DES.new(derive_key(), DES.MODE_ECB)
    if inf.endswith('.bin'):
        print("Ayrıştırma başlatılıyor...")
        with open(inf, 'rb') as f: data = f.read()
        dec = crypto.decrypt(data)[16:]
        res = uncompress_data(dec)
        with open(outf, 'wb') as f: f.write(res)
        print("İŞLEM TAMAM!")
        ctypes.windll.user32.MessageBoxW(0, "Powered BYF Support https://techolay.net", "İŞLEM TAMAM!", 0x40)
    elif inf.endswith('.xml'):
        print("Sıkıştırma ve Şifreleme başlatılıyor...")
        with open(inf, 'rb') as f: xml = f.read()
        cmp = compress_data(xml)
        hsh = md5(cmp[:struct.unpack_from('<I', cmp, 0)[0] if False else len(cmp)]).digest()
        full = hsh + cmp
        enc = crypto.encrypt(full)
        with open(outf, 'wb') as f: f.write(enc)
        print("İŞLEM TAMAM!")
        ctypes.windll.user32.MessageBoxW(0, "Powered BYF Support https://techolay.net", "İŞLEM TAMAM!", 0x40)

if __name__ == "__main__":
    main()