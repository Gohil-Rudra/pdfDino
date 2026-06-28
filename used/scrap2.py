"""
make_bird_pdf.py
----------------
Generates a PDF with an animated flapping bird using two image frames.
Uses a checkbox field (Ff=0) with named appearance states so JavaScript
can toggle frames via field.value = "frame0" / "frame1".

app.setInterval drives the animation at 50ms intervals.

Usage:
    python make_bird_pdf.py bird.png bird2.png output.pdf
"""

import sys
import zlib
import io
from PIL import Image

# ── tuneable layout ──────────────────────────────────────────────────────────
BTN_X, BTN_Y = 50, 580
BTN_W, BTN_H = 80, 60
PAGE_W, PAGE_H = 612, 792
INTERVAL_MS = 50
# ─────────────────────────────────────────────────────────────────────────────


def load_image(png_path):
    """Return (rgb_bytes, alpha_bytes_or_None, width, height)."""
    img = Image.open(png_path)
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode == "RGBA":
        r, g, b, a = img.split()
        return Image.merge("RGB", (r,g,b)).tobytes(), a.tobytes(), img.width, img.height
    elif img.mode == "LA":
        l, a = img.split()
        return Image.merge("RGB", (l,l,l)).tobytes(), a.tobytes(), img.width, img.height
    else:
        img = img.convert("RGB")
        return img.tobytes(), None, img.width, img.height


def deflate(data: bytes) -> bytes:
    return zlib.compress(data, 9)


class PdfBuilder:
    def __init__(self):
        self.objects = {}
        self._next_id = 1
        self.offsets = {}

    def alloc(self):
        oid = self._next_id
        self._next_id += 1
        return oid

    def add(self, oid, raw: bytes):
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


def make_image_objects(pdf, rgb_bytes, alpha_bytes, img_w, img_h):
    """
    Adds an Image XObject (+ optional SMask) to the pdf.
    Returns img_id.
    """
    img_id  = pdf.alloc()
    mask_id = pdf.alloc()

    if alpha_bytes:
        alpha_z = deflate(alpha_bytes)
        pdf.add(mask_id, (
            f"<< /Type /XObject /Subtype /Image\n"
            f"   /Width {img_w} /Height {img_h}\n"
            f"   /ColorSpace /DeviceGray /BitsPerComponent 8\n"
            f"   /Filter /FlateDecode /Length {len(alpha_z)} >>\n"
            f"stream\n"
        ).encode() + alpha_z + b"\nendstream")
        smask = f"/SMask {mask_id} 0 R\n   "
    else:
        smask = ""

    rgb_z = deflate(rgb_bytes)
    pdf.add(img_id, (
        f"<< /Type /XObject /Subtype /Image\n"
        f"   /Width {img_w} /Height {img_h}\n"
        f"   /ColorSpace /DeviceRGB /BitsPerComponent 8\n"
        f"   {smask}/Filter /FlateDecode /Length {len(rgb_z)} >>\n"
        f"stream\n"
    ).encode() + rgb_z + b"\nendstream")

    return img_id


def make_ap_object(pdf, img_id, w, h):
    """
    Adds a Form XObject that scales img_id to fill w×h.
    Returns ap_id.
    """
    ap_id = pdf.alloc()
    stream   = f"q {w} 0 0 {h} 0 0 cm /Im0 Do Q".encode()
    stream_z = deflate(stream)
    pdf.add(ap_id, (
        f"<< /Type /XObject /Subtype /Form\n"
        f"   /BBox [0 0 {w} {h}]\n"
        f"   /Resources << /XObject << /Im0 {img_id} 0 R >> >>\n"
        f"   /Filter /FlateDecode /Length {len(stream_z)} >>\n"
        f"stream\n"
    ).encode() + stream_z + b"\nendstream")
    return ap_id


def build(png0: str, png1: str, out_path: str):
    rgb0, a0, w0, h0 = load_image(png0)
    rgb1, a1, w1, h1 = load_image(png1)

    # Button size from frame 0, capped at 200pt
    global BTN_W, BTN_H
    if BTN_W == 80 and BTN_H == 60:
        scale = min(1.0, 200 / max(w0, h0))
        BTN_W = max(1, int(w0 * scale))
        BTN_H = max(1, int(h0 * scale))

    pdf = PdfBuilder()

    # ── fixed-ID objects ──────────────────────────────────────────────────
    cat_id     = pdf.alloc()   # 1  Catalog
    pages_id   = pdf.alloc()   # 2  Pages
    page_id    = pdf.alloc()   # 3  Page
    content_id = pdf.alloc()   # 4  Page content
    font_id    = pdf.alloc()   # 5  Font
    acro_id    = pdf.alloc()   # 6  AcroForm
    field_id   = pdf.alloc()   # 7  Widget (checkbox field)
    js_id      = pdf.alloc()   # 8  JavaScript action

    # ── frame images (alloc inside helpers, IDs vary) ─────────────────────
    img0_id = make_image_objects(pdf, rgb0, a0, w0, h0)   # 9 (+10 if alpha)
    img1_id = make_image_objects(pdf, rgb1, a1, w1, h1)   # 11 (+12 if alpha)

    # ── appearance Form XObjects ──────────────────────────────────────────
    ap0_id = make_ap_object(pdf, img0_id, BTN_W, BTN_H)   # 13
    ap1_id = make_ap_object(pdf, img1_id, BTN_W, BTN_H)   # 14

    # ── 8: JavaScript action ──────────────────────────────────────────────
    # Checkbox field value toggles between "frame0" and "frame1".
    # app.setInterval string is eval'd in the document context so `this`
    # is the document — exactly what getField needs.
    js_code = (
        'var _f = 0;'
        'app.setInterval('
        '"var fld = this.getField(\\"BirdBtn\\");'
        'fld.value = (_f++ % 2 === 0) ? \\"frame0\\" : \\"frame1\\";", '
        f'{INTERVAL_MS});'
    )
    pdf.add(js_id, (
        f"<< /S /JavaScript /JS ({js_code}) >>"
    ).encode())

    # ── 7: Widget annotation — checkbox with named appearances ────────────
    #
    # Key decisions:
    #   /FT /Btn  /Ff 0   → checkbox (NOT pushbutton)
    #                        Ff=0 means no special flags set, making it a
    #                        checkbox whose visible state tracks /V
    #
    #   /V /frame0         → initial value = show frame0
    #   /DV /frame0        → default value (used on form reset)
    #
    #   /AP /N << /frame0 ap0_id /frame1 ap1_id >>
    #                      → named Normal appearances.
    #                        When field.value = "frame1", the viewer
    #                        automatically switches to the ap1 XObject.
    #                        No JS image-swapping needed — the PDF spec
    #                        handles the lookup.
    #
    #   /BS /W 0           → hide the checkbox border
    #   /MK << >>          → empty mark-up dict suppresses default check glyph
    #
    pdf.add(field_id, (
        f"<< /Type /Annot /Subtype /Widget\n"
        f"   /FT /Btn /Ff 0\n"
        f"   /T (BirdBtn)\n"
        f"   /V /frame0 /DV /frame0\n"
        f"   /Rect [{BTN_X} {BTN_Y} {BTN_X+BTN_W} {BTN_Y+BTN_H}]\n"
        f"   /AP << /N << /frame0 {ap0_id} 0 R /frame1 {ap1_id} 0 R >> >>\n"
        f"   /BS << /W 0 >>\n"
        f"   /MK << >>\n"
        f"   /P {page_id} 0 R\n"
        f">>"
    ).encode())

    # ── 6: AcroForm ───────────────────────────────────────────────────────
    # /CO (Calculate Order) runs JS actions on document open.
    # We abuse it here to fire our setInterval bootstrap.
    pdf.add(acro_id, (
        f"<< /Fields [{field_id} 0 R]\n"
        f"   /DR << /Font << /F1 {font_id} 0 R >> >>\n"
        f"   /CO [{js_id} 0 R]\n"
        f">>"
    ).encode())

    # ── 5: Font ───────────────────────────────────────────────────────────
    pdf.add(font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # ── 4: Page content ───────────────────────────────────────────────────
    ps   = f"BT /F1 12 Tf 250 {PAGE_H-100} Td (Completely normal pdf) Tj ET".encode()
    ps_z = deflate(ps)
    pdf.add(content_id, (
        f"<< /Filter /FlateDecode /Length {len(ps_z)} >>\nstream\n"
    ).encode() + ps_z + b"\nendstream")

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

    print(f"✓  {out_path}")
    print(f"   Button  : ({BTN_X},{BTN_Y})  {BTN_W}×{BTN_H} pts")
    print(f"   Frame 0 : {w0}×{h0}  alpha={'yes' if a0 else 'no'}")
    print(f"   Frame 1 : {w1}×{h1}  alpha={'yes' if a1 else 'no'}")
    print(f"   Interval: {INTERVAL_MS} ms")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python make_bird_pdf.py bird.png bird2.png output.pdf")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
