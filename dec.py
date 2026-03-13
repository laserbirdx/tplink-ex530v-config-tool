import sys
import struct
import subprocess
import ctypes
from hashlib import md5

try:
    from Cryptodome.Cipher import DES
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome"])
    from Cryptodome.Cipher import DES

KEY = b'\x40\xbb\xc6\x6d\xcb\x5a\x1d\xfe'

def compress(src):
    if src[-1]: src += b'\0'
    size = len(src)
    hash_table = [0] * 0x2000
    dst = bytearray(struct.pack('<I', size))
    dst.append(src[0])
    
    s_p, s_ph = 1, 0
    d_pb, d_p = 5, 7
    bc, db = 0x10, 0
    dst.extend(b'\0\0')

    def put_bit(bit):
        nonlocal bc, db, d_p, d_pb
        if bc: bc -= 1
        else:
            struct.pack_into('H', dst, d_pb, db)
            d_pb, d_p = d_p, d_p + 2
            dst.extend(b'\0\0')
            bc = 0xF
        db = (bit + (db << 1)) & 0xFFFF

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

    def hash_key(offset):
        b4 = src[offset:offset+4]
        hk = 0
        for b in b4[:3]: hk = (hk + b) * 0x13d
        return ((hk + b4[3]) & 0x1FFF)

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
                if count == buffer_countdown: break
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

    struct.pack_into('H', dst, d_pb, (db << bc) & 0xFFFF)
    return dst[:d_p]

def uncompress(src):
    block16_countdown, block16_dict_bits, s_p, d_p = 0, 0, 4, 0
    def get_bit():
        nonlocal block16_countdown, block16_dict_bits, s_p
        if block16_countdown: block16_countdown -= 1
        else:
            block16_dict_bits = struct.unpack_from('H', src, s_p)[0]
            s_p, block16_countdown = s_p + 2, 0xF
        block16_dict_bits = block16_dict_bits << 1
        return 1 if block16_dict_bits & 0x10000 else 0

    def get_dict_ld():
        bits = 1
        while True:
            bits = (bits << 1) + get_bit()
            if not get_bit(): break
        return bits

    size = struct.unpack_from('<I', src, 0)[0]
    dst = bytearray(size)
    dst[d_p] = src[s_p]
    s_p, d_p = s_p + 1, d_p + 1
    while d_p < size:
        if get_bit():
            num_chars = get_dict_ld() + 2
            offset = d_p - (((get_dict_ld() - 2) << 8) + src[s_p] + 1)
            s_p += 1
            for i in range(num_chars):
                dst[d_p] = dst[offset]
                d_p, offset = d_p + 1, offset + 1
        else:
            dst[d_p] = src[s_p]
            s_p, d_p = s_p + 1, d_p + 1
    return dst

def main():
    if len(sys.argv) < 3:
        print("Kullanim: python dec.py <giris> <cikis>")
        return
    inf, outf = sys.argv[1], sys.argv[2]
    crypto = DES.new(KEY, DES.MODE_ECB)

    if inf.endswith('.bin'):
        print("Ayrıştırma başlatılıyor...")
        with open(inf, 'rb') as f: data = f.read()
        decrypted_payload = crypto.decrypt(data)[16:]
        result = uncompress(decrypted_payload)
        with open(outf, 'wb') as f: f.write(result)
        print("İŞLEM TAMAM!")
        ctypes.windll.user32.MessageBoxW(0, "Powered BYF Support https://techolay.net", "İŞLEM TAMAM!", 0x40)
    else:
        print("Şifreleme başlatılıyor...")
        with open(inf, 'rb') as f: xml_content = f.read()
        compressed_data = compress(xml_content)
        md5_hash = md5(compressed_data).digest()
        full_data = md5_hash + compressed_data
        if len(full_data) % 8: full_data += b'\0' * (8 - (len(full_data) % 8))
        encrypted_data = crypto.encrypt(bytes(full_data))
        with open(outf, 'wb') as f: f.write(encrypted_data)
        print("İŞLEM TAMAM!")
        ctypes.windll.user32.MessageBoxW(0, "Powered BYF Support https://techolay.net", "İŞLEM TAMAM!", 0x40)

if __name__ == "__main__":
    main()
