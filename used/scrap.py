"""
make_bird_pdf.py
----------------
Generates a PDF with:
  - The text "Completely normal pdf"
  - A pushbutton AcroForm field whose appearance is your bird.png

True PNG transparency is preserved via a PDF SMask (Soft Mask) — the alpha
channel is sent as a separate greyscale Image XObject and the viewer composites
against whatever is actually behind the button. No white/black square.

Usage:
    python make_bird_pdf.py bird.png output.pdf
"""

import sys
import zlib
import io
from PIL import Image

# ── tuneable layout ──────────────────────────────────────────────────────────
BTN_X, BTN_Y = 50, 580    # lower-left corner of button (PDF pts, origin=bottom-left)
BTN_W, BTN_H = 80, 60     # width × height in points (auto-sized if unchanged)
PAGE_W, PAGE_H = 612, 792  # US Letter
# ─────────────────────────────────────────────────────────────────────────────


def load_image(png_path):
    """
    Returns (rgb_bytes, alpha_bytes_or_None, width, height).

    rgb_bytes  – raw R,G,B interleaved, one byte per channel per pixel
    alpha_bytes – raw greyscale alpha (one byte per pixel), or None
    """
    img = Image.open(png_path)

    if img.mode == "P":          # palette → need full RGBA before splitting
        img = img.convert("RGBA")

    if img.mode == "RGBA":
        r, g, b, a = img.split()
        rgb_bytes   = Image.merge("RGB", (r, g, b)).tobytes()
        alpha_bytes = a.tobytes()
        return rgb_bytes, alpha_bytes, img.width, img.height

    elif img.mode == "LA":       # greyscale + alpha
        l, a = img.split()
        rgb_bytes   = Image.merge("RGB", (l, l, l)).tobytes()
        alpha_bytes = a.tobytes()
        return rgb_bytes, alpha_bytes, img.width, img.height

    else:                        # RGB, L, etc. — no transparency
        img = img.convert("RGB")
        return img.tobytes(), None, img.width, img.height


def deflate(data: bytes) -> bytes:
    return zlib.compress(data, 9)


class PdfBuilder:
    """Minimal hand-rolled PDF writer."""

    def __init__(self):
        self.objects = {}
        self._next_id = 1
        self.offsets = {}

    def alloc(self) -> int:
        oid = self._next_id
        self._next_id += 1
        return oid

    def add(self, oid: int, raw: bytes):
        self.objects[oid] = raw

    def serialise(self) -> bytes:
        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        for oid in sorted(self.objects):
            self.offsets[oid] = buf.tell()
            buf.write(f"{oid} 0 obj\n".encode())
            buf.write(self.objects[oid])
            buf.write(b"\nendobj\n")

        xref_offset = buf.tell()
        count = max(self.objects) + 1
        buf.write(f"xref\n0 {count}\n".encode())
        buf.write(b"0000000000 65535 f \n")
        for oid in range(1, count):
            off = self.offsets.get(oid, 0)
            buf.write(f"{off:010d} 00000 n \n".encode())

        buf.write(b"trailer\n")
        buf.write(f"<< /Size {count} /Root 1 0 R >>\n".encode())
        buf.write(b"startxref\n")
        buf.write(f"{xref_offset}\n".encode())
        buf.write(b"%%EOF\n")
        return buf.getvalue()


def build(png_path: str, out_path: str):
    rgb_bytes, alpha_bytes, img_w, img_h = load_image(png_path)

    # Auto-size button to image's natural dimensions (cap at 200pt)
    global BTN_W, BTN_H
    if BTN_W == 80 and BTN_H == 60:
        scale = min(1.0, 200 / max(img_w, img_h))
        BTN_W = max(1, int(img_w * scale))
        BTN_H = max(1, int(img_h * scale))

    pdf = PdfBuilder()

    # ── allocate IDs ──────────────────────────────────────────────────────
    cat_id     = pdf.alloc()   # 1  Catalog
    pages_id   = pdf.alloc()   # 2  Pages
    page_id    = pdf.alloc()   # 3  Page
    content_id = pdf.alloc()   # 4  Page content stream
    font_id    = pdf.alloc()   # 5  Font
    acro_id    = pdf.alloc()   # 6  AcroForm
    field_id   = pdf.alloc()   # 7  Widget annotation (button)
    ap_id      = pdf.alloc()   # 8  Appearance Form XObject
    img_id     = pdf.alloc()   # 9  Image XObject (RGB)
    # object 10 is allocated below only when alpha exists
    mask_id    = pdf.alloc()   # 10 SMask Image XObject (alpha) — or unused

    # ── 10 / mask: Alpha channel as greyscale Image XObject ───────────────
    # This only gets added to the PDF if the image actually has transparency.
    # It's a plain /DeviceGray image — one byte per pixel, 0=fully transparent,
    # 255=fully opaque.  The PDF viewer reads this alongside the RGB image and
    # uses it to blend against whatever is underneath — no white square, no
    # black square, regardless of background colour.
    if alpha_bytes:
        alpha_compressed = deflate(alpha_bytes)
        mask_dict = (
            f"<< /Type /XObject /Subtype /Image\n"
            f"   /Width {img_w} /Height {img_h}\n"
            f"   /ColorSpace /DeviceGray\n"
            f"   /BitsPerComponent 8\n"
            f"   /Filter /FlateDecode\n"
            f"   /Length {len(alpha_compressed)} >>\n"
            f"stream\n"
        ).encode() + alpha_compressed + b"\nendstream"
        pdf.add(mask_id, mask_dict)
        smask_ref = f"/SMask {mask_id} 0 R\n   "
    else:
        smask_ref = ""   # image has no alpha — omit the SMask key entirely

    # ── 9: RGB Image XObject ──────────────────────────────────────────────
    # /SMask points to the alpha image above. When present the viewer treats
    # each pixel's alpha value as its opacity and blends accordingly.
    rgb_compressed = deflate(rgb_bytes)
    img_dict = (
        f"<< /Type /XObject /Subtype /Image\n"
        f"   /Width {img_w} /Height {img_h}\n"
        f"   /ColorSpace /DeviceRGB /BitsPerComponent 8\n"
        f"   {smask_ref}"
        f"/Filter /FlateDecode\n"
        f"   /Length {len(rgb_compressed)} >>\n"
        f"stream\n"
    ).encode() + rgb_compressed + b"\nendstream"
    pdf.add(img_id, img_dict)

    # ── 8: Appearance Form XObject ────────────────────────────────────────
    ap_stream     = f"q {BTN_W} 0 0 {BTN_H} 0 0 cm /Im0 Do Q".encode()
    ap_compressed = deflate(ap_stream)
    ap_dict = (
        f"<< /Type /XObject /Subtype /Form\n"
        f"   /BBox [0 0 {BTN_W} {BTN_H}]\n"
        f"   /Resources << /XObject << /Im0 {img_id} 0 R >> >>\n"
        f"   /Filter /FlateDecode\n"
        f"   /Length {len(ap_compressed)} >>\n"
        f"stream\n"
    ).encode() + ap_compressed + b"\nendstream"
    pdf.add(ap_id, ap_dict)

    # ── 7: Widget annotation (pushbutton) ─────────────────────────────────
    field_dict = (
        f"<< /Type /Annot /Subtype /Widget\n"
        f"   /FT /Btn\n"
        f"   /Ff 65536\n"
        f"   /T (BirdBtn)\n"
        f"   /Rect [{BTN_X} {BTN_Y} {BTN_X+BTN_W} {BTN_Y+BTN_H}]\n"
        f"   /AP << /N {ap_id} 0 R >>\n"
        f"   /MK << /I {ap_id} 0 R /TP 1 >>\n"
        f"   /BS << /W 0 >>\n"
        f"   /P {page_id} 0 R\n"
        f">>"
    ).encode()
    pdf.add(field_id, field_dict)

    # ── 6: AcroForm ───────────────────────────────────────────────────────
    pdf.add(acro_id, (
        f"<< /Fields [{field_id} 0 R] /DR << /Font << /F1 {font_id} 0 R >> >> >>"
    ).encode())

    # ── 5: Font ───────────────────────────────────────────────────────────
    pdf.add(font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # ── 4: Page content stream ────────────────────────────────────────────
    page_stream   = f"BT /F1 12 Tf 250 {PAGE_H-100} Td (Completely normal pdf) Tj ET".encode()
    page_stream_z = deflate(page_stream)
    pdf.add(content_id, (
        f"<< /Filter /FlateDecode /Length {len(page_stream_z)} >>\nstream\n"
    ).encode() + page_stream_z + b"\nendstream")

    # ── 3: Page ───────────────────────────────────────────────────────────
    pdf.add(page_id, (
        f"<< /Type /Page /Parent {pages_id} 0 R\n"
        f"   /MediaBox [0 0 {PAGE_W} {PAGE_H}]\n"
        f"   /Resources << /Font << /F1 {font_id} 0 R >> >>\n"
        f"   /Contents {content_id} 0 R\n"
        f"   /Annots [{field_id} 0 R]\n"
        f">>"
    ).encode())

    # ── 2: Pages ──────────────────────────────────────────────────────────
    pdf.add(pages_id, f"<< /Type /Pages /Count 1 /Kids [{page_id} 0 R] >>".encode())

    # ── 1: Catalog ────────────────────────────────────────────────────────
    pdf.add(cat_id, (
        f"<< /Type /Catalog /Pages {pages_id} 0 R /AcroForm {acro_id} 0 R >>"
    ).encode())

    with open(out_path, "wb") as f:
        f.write(pdf.serialise())

    has_alpha = "yes → SMask embedded" if alpha_bytes else "no"
    print(f"✓ Written to {out_path}")
    print(f"  Button : ({BTN_X},{BTN_Y})  {BTN_W}×{BTN_H} pts")
    print(f"  Image  : {img_w}×{img_h} px")
    print(f"  Alpha  : {has_alpha}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python make_bird_pdf.py bird.png output.pdf")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
