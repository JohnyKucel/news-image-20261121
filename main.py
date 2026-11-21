import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (246, 239, 221)
LINE = (198, 188, 164)
ACCENT = (163, 32, 26)
ACCENT_LT = (200, 90, 60)

HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "assets")
OUT = os.path.join(
    os.environ.get("MAKEFUN_OUTPUT_DIR", os.path.join(HERE, "out")),
    "entry.png",
)

LEAD_POS = (258, 174)
SIDE_COLS = (24, 778)
SIDE_ROWS = (156, 302)
BAND_COLS = (24, 270, 516, 762)
BAND_ROWS = (512, 668)

photos = [("illo_summit.png",) + LEAD_POS]
_side_names = (
    ("illo_europe.png", "illo_ukraine.png"),
    ("illo_riyadh.png", "illo_markets.png"),
)
for _col, _names in enumerate(_side_names):
    for _row, _nm in enumerate(_names):
        photos.append((_nm, SIDE_COLS[_col], SIDE_ROWS[_row]))
_band_names = (
    ("illo_trade.png", "illo_tech.png", "illo_jakarta.png", "illo_kyiv.png"),
    ("illo_lebanon.png", "illo_iran.png", "illo_seoul.png", "illo_sport.png"),
)
for _row, _names in enumerate(_band_names):
    for _col, _nm in enumerate(_names):
        photos.append((_nm, BAND_COLS[_col], BAND_ROWS[_row]))

texts = {
    "t_meta.png": (24, 11),
    "t_ear_l.png": (24, 30),
    "t_ear_r.png": (850, 30),
    "t_masthead.png": (226, 54),
    "t_tag.png": (209, 129),
    "t_lead.png": (257, 158),
    "t_side0.png": (23, 220),
    "t_side1.png": (23, 366),
    "t_side2.png": (777, 220),
    "t_side3.png": (777, 366),
    "t_band0_0.png": (23, 578),
    "t_band0_1.png": (269, 578),
    "t_band0_2.png": (515, 578),
    "t_band0_3.png": (762, 578),
    "t_band1_0.png": (24, 734),
    "t_band1_1.png": (269, 734),
    "t_band1_2.png": (516, 734),
    "t_band1_3.png": (761, 734),
    "t_numband.png": (24, 454),
    "t_crypto.png": (24, 824),
    "t_datecheck.png": (24, 914),
    "t_alsotoday.png": (608, 914),
    "t_foot.png": (24, 991),
}

hlines = [
    (24, 1000, 26, 1, LINE),
    (24, 1000, 148, 1, ACCENT_LT),
    (24, 1000, 149, 2, ACCENT),
    (24, 1000, 450, 1, LINE),
    (24, 1000, 507, 1, LINE),
    (24, 1000, 663, 1, LINE),
    (24, 1000, 818, 1, LINE),
    (24, 1000, 982, 2, LINE),
]

vlines = [
    (252, 156, 440, LINE),
    (772, 156, 440, LINE),
    (266, 512, 658, LINE),
    (512, 512, 658, LINE),
    (758, 512, 658, LINE),
    (266, 668, 814, LINE),
    (512, 668, 814, LINE),
    (758, 668, 814, LINE),
]

outlines = []


def _paeth(a, b, c):
    p = a + b - c
    da = abs(p - a)
    db = abs(p - b)
    dc = abs(p - c)
    if da <= db and da <= dc:
        return a
    if db <= dc:
        return b
    return c


def load_png(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: " + path)
    off = 8
    w = h = None
    depth = ctype = lace = None
    blocks = bytearray()
    while off < len(blob):
        size = struct.unpack_from(">I", blob, off)[0]
        kind = blob[off + 4:off + 8]
        part = blob[off + 8:off + 8 + size]
        if kind == b"IHDR":
            w, h, depth, ctype, _c, _f, lace = struct.unpack(
                ">IIBBBBB", part)
        elif kind == b"IDAT":
            blocks += part
        elif kind == b"IEND":
            break
        off += 12 + size
    if depth != 8 or lace != 0 or ctype not in (0, 2, 6):
        raise ValueError("unsupported PNG: " + path)
    nc = {0: 1, 2: 3, 6: 4}[ctype]
    raw = zlib.decompress(bytes(blocks))
    stride = w * nc
    if nc == 1:
        out = bytearray(w * h * 3)
    else:
        out = bytearray(w * h * nc)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        f = raw[pos]
        pos += 1
        row = bytearray(raw[pos:pos + stride])
        pos += stride
        if f == 1:
            for i in range(nc, stride):
                row[i] = (row[i] + row[i - nc]) & 255
        elif f == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = row[i - nc] if i >= nc else 0
                row[i] = (row[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = row[i - nc] if i >= nc else 0
                b = prev[i]
                c = prev[i - nc] if i >= nc else 0
                row[i] = (row[i] + _paeth(a, b, c)) & 255
        elif f != 0:
            raise ValueError("bad PNG filter %d in %s" % (f, path))
        prev = row
        if nc == 1:
            dst = y * w * 3
            for x in range(w):
                out[dst + x * 3] = row[x]
                out[dst + x * 3 + 1] = row[x]
                out[dst + x * 3 + 2] = row[x]
        else:
            dst = y * stride
            out[dst:dst + stride] = row
    return w, h, bytes(out), nc == 4


def _chunk(kind, payload):
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _filtered(rgb, w, h, mode):
    stride = w * 3
    buf = bytearray()
    above = bytes(stride)
    for y in range(h):
        cur = rgb[y * stride:(y + 1) * stride]
        buf.append(mode)
        if mode == 0:
            buf += cur
        else:
            buf += bytes((v - u) & 255 for v, u in zip(cur, above))
        above = cur
    return bytes(buf)


def save_png(path, w, h, rgb):
    head = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    first = zlib.compress(_filtered(rgb, w, h, 0), 9)
    second = zlib.compress(_filtered(rgb, w, h, 2), 9)
    body = first if len(first) <= len(second) else second
    blob = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", head)
        + _chunk(b"IDAT", body)
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(blob)


def blit(page, img, iw, ih, ox, oy, alpha):
    if not alpha:
        for y in range(ih):
            d = ((oy + y) * W + ox) * 3
            s = y * iw * 3
            page[d:d + iw * 3] = img[s:s + iw * 3]
        return
    for y in range(ih):
        prow = (oy + y) * W * 3
        irow = y * iw * 4
        for x in range(iw):
            s = irow + x * 4
            a = img[s + 3]
            if a == 0:
                continue
            d = prow + (ox + x) * 3
            if a == 255:
                page[d:d + 3] = img[s:s + 3]
            else:
                inv = 255 - a
                for k in range(3):
                    page[d + k] = (img[s + k] * a + page[d + k] * inv + 127) // 255


def paint(page, x0, y0, x1, y1, rgb):
    r, g, b = rgb
    for y in range(y0, y1 + 1):
        base = y * W * 3
        for x in range(x0, x1 + 1):
            o = base + x * 3
            page[o] = r
            page[o + 1] = g
            page[o + 2] = b


def edge(page, x0, y0, x1, y1):
    inv = 255 - 56
    for x in range(x0, x1 + 1):
        for y in (y0, y1):
            o = (y * W + x) * 3
            for k in range(3):
                page[o + k] = (PAPER[k] * 56 + page[o + k] * inv + 127) // 255
    for y in range(y0 + 1, y1):
        for x in (x0, x1):
            o = (y * W + x) * 3
            for k in range(3):
                page[o + k] = (PAPER[k] * 56 + page[o + k] * inv + 127) // 255


def place(page, name, x, y):
    iw, ih, pix, al = load_png(os.path.join(IMGDIR, name))
    blit(page, pix, iw, ih, x, y, al)


def build():
    page = bytearray(bytes(PAPER) * (W * H))
    gw, gh, grain, gal = load_png(os.path.join(IMGDIR, "grain_256.png"))
    for ty in range(0, H, gh):
        for tx in range(0, W, gw):
            blit(page, grain, gw, gh, tx, ty, gal)
    for name, x, y in photos:
        place(page, name, x, y)
    for x0, x1, y, th, col in hlines:
        top = y - (th - 1) // 2
        paint(page, x0, top, x1, top + th - 1, col)
    for x, y0, y1, col in vlines:
        paint(page, x, y0, x, y1, col)
    for name, (x, y) in texts.items():
        place(page, name, x, y)
    for x0, y0, x1, y1 in outlines:
        edge(page, x0, y0, x1, y1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    save_png(OUT, W, H, bytes(page))
    print("wrote", OUT)


if __name__ == "__main__":
    build()
