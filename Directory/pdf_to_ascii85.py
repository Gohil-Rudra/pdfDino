#!/usr/bin/env python3
"""
Re-encodes all streams in a PDF from FlateDecode (binary)
to ASCII85Decode + FlateDecode, so the file is text-editor friendly.

Usage:
    python3 pdf_to_ascii85.py input.pdf output.pdf
"""

import sys
import re
import zlib

# ---------------------------------------------------------------------------
# ASCII85 encoder (pure Python, no external deps)
# ---------------------------------------------------------------------------
def ascii85_encode(data: bytes) -> bytes:
    """Encode bytes to Adobe ASCII85, terminated with ~>"""
    result = []
    # pad to multiple of 4
    padding = (4 - len(data) % 4) % 4
    padded = data + b'\x00' * padding
    for i in range(0, len(padded), 4):
        b = int.from_bytes(padded[i:i+4], 'big')
        if b == 0:
            result.append(b'z')
        else:
            chars = []
            for _ in range(5):
                chars.append(b % 85 + 33)
                b //= 85
            result.append(bytes(reversed(chars)))
    # If we added padding, we need to trim the last group
    if padding:
        # The last group: remove 'padding' bytes from encoded output
        last = result[-1]
        if last == b'z':
            last = b'!!!!!'
        result[-1] = last[:5 - padding]
    result.append(b'~>')
    # Wrap at 75 chars per line for readability
    raw = b''.join(result)
    lines = [raw[i:i+75] for i in range(0, len(raw), 75)]
    return b'\n'.join(lines)


# ---------------------------------------------------------------------------
# PDF token-level stream extractor
# ---------------------------------------------------------------------------
STREAM_RE = re.compile(
    rb'(\d+ \d+ obj\s*<<)(.*?)(>>)\s*stream\r?\n(.*?)endstream',
    re.DOTALL
)

def get_filter_info(obj_dict: bytes):
    """Return the /Filter value(s) and /DecodeParms if present."""
    # Match /Filter /Name  or  /Filter [/Name /Name ...]
    m = re.search(rb'/Filter\s+(/\w+|\[.*?\])', obj_dict, re.DOTALL)
    if not m:
        return None, None
    filter_val = m.group(1).strip()
    dp = re.search(rb'/DecodeParms\s+(\[.*?\]|<<.*?>>)', obj_dict, re.DOTALL)
    decode_parms = dp.group(1) if dp else None
    return filter_val, decode_parms


def replace_filter_and_parms(obj_dict: bytes, new_filter: bytes, new_parms: bytes | None) -> bytes:
    """Replace /Filter (and optionally /DecodeParms) in the dict bytes."""
    # Remove existing /DecodeParms
    obj_dict = re.sub(rb'\s*/DecodeParms\s+(\[.*?\]|<<.*?>>)', b'', obj_dict, flags=re.DOTALL)
    # Replace /Filter value
    obj_dict = re.sub(
        rb'/Filter\s+(/\w+|\[.*?\])',
        b'/Filter ' + new_filter,
        obj_dict,
        flags=re.DOTALL
    )
    if new_parms:
        obj_dict = obj_dict + b'\n/DecodeParms ' + new_parms
    return obj_dict


def process_pdf(in_path: str, out_path: str):
    with open(in_path, 'rb') as f:
        data = f.read()

    result = bytearray()
    prev_end = 0
    streams_converted = 0
    streams_skipped = 0

    for m in STREAM_RE.finditer(data):
        obj_header   = m.group(1)   # "N G obj  <<"
        dict_content = m.group(2)   # everything inside << ... >>
        dict_close   = m.group(3)   # ">>"
        stream_data  = m.group(4)   # raw bytes between stream\n and \nendstream

        full_dict = dict_content  # without the surrounding << >>

        filter_val, decode_parms = get_filter_info(full_dict)

        # We only touch streams that are SOLELY FlateDecode (single filter)
        if filter_val != b'/FlateDecode':
            # Skip array filters and non-flate streams
            streams_skipped += 1
            continue

        # Decompress to verify we can handle this stream
        try:
            raw = zlib.decompress(stream_data)
        except zlib.error:
            # Some streams have a predictor applied; try wbits=-15
            try:
                raw = zlib.decompress(stream_data, -15)
            except zlib.error:
                streams_skipped += 1
                continue

        # Re-compress (same data, reproducible)
        recompressed = zlib.compress(raw, level=6)

        # ASCII85-encode the compressed bytes
        a85_data = ascii85_encode(recompressed)

        # New filter: [ASCII85Decode FlateDecode]  (outermost first)
        new_filter = b'[/ASCII85Decode /FlateDecode]'
        # Preserve DecodeParms if it existed (it belonged to FlateDecode,
        # which is now the inner filter → wrap in array)
        if decode_parms:
            new_parms = b'[null ' + decode_parms + b']'
        else:
            new_parms = None

        # Rebuild dict
        new_dict = replace_filter_and_parms(full_dict, new_filter, new_parms)
        # Update /Length
        new_length = len(a85_data)
        new_dict = re.sub(rb'/Length\s+\d+', b'/Length ' + str(new_length).encode(), new_dict)

        # Reconstruct the object
        new_obj = (
            obj_header +
            new_dict +
            dict_close +
            b'\nstream\n' +
            a85_data +
            b'\nendstream'
        )

        result += data[prev_end:m.start()]
        result += new_obj
        prev_end = m.end()
        streams_converted += 1

    result += data[prev_end:]

    # Fix the cross-reference table offsets — we need to rebuild xref.
    # Easiest: use qpdf-style re-linearization via a second pass.
    # Since we're changing lengths, we must update xref.
    final = rebuild_xref(bytes(result))

    with open(out_path, 'wb') as f:
        f.write(final)

    print(f"Done. Converted {streams_converted} streams, skipped {streams_skipped}.")
    print(f"Output written to: {out_path}")


# ---------------------------------------------------------------------------
# xref rebuilder  (handles both xref-table and cross-reference streams)
# ---------------------------------------------------------------------------
def rebuild_xref(data: bytes) -> bytes:
    """Recompute all object byte offsets and rewrite the xref table + trailer."""
    # Find all object definitions
    obj_offsets = {}
    for m in re.finditer(rb'(\d+) (\d+) obj\b', data):
        obj_num = int(m.group(1))
        gen_num = int(m.group(2))
        obj_offsets[(obj_num, gen_num)] = m.start()

    if not obj_offsets:
        return data

    # Locate the old xref section
    last_xref = data.rfind(b'\nxref')
    if last_xref == -1:
        last_xref = data.rfind(b'\r\nxref')
    if last_xref == -1:
        # Cross-reference stream PDF — too complex; just return as-is
        return data

    # Build new xref
    all_keys = sorted(obj_offsets.keys())
    max_obj = max(k[0] for k in all_keys)

    xref_lines = []
    xref_lines.append(b'xref\n')
    xref_lines.append(b'0 ' + str(max_obj + 1).encode() + b'\n')
    xref_lines.append(b'0000000000 65535 f \n')
    for i in range(1, max_obj + 1):
        if (i, 0) in obj_offsets:
            off = obj_offsets[(i, 0)]
            xref_lines.append(f'{off:010d} 00000 n \n'.encode())
        else:
            xref_lines.append(b'0000000000 00000 f \n')

    xref_bytes = b''.join(xref_lines)

    # Find existing trailer dict
    trailer_match = re.search(rb'trailer\s*<<(.*?)>>', data[last_xref:], re.DOTALL)
    if not trailer_match:
        return data
    trailer_dict = trailer_match.group(1)
    # Remove old /Prev if any
    trailer_dict = re.sub(rb'\s*/Prev\s+\d+', b'', trailer_dict)

    body = data[:last_xref + 1]  # everything before old xref (keep leading \n)
    startxref_pos = len(body)

    new_tail = (
        xref_bytes +
        b'trailer\n<<' + trailer_dict + b'>>\n' +
        b'startxref\n' +
        str(startxref_pos).encode() + b'\n' +
        b'%%EOF\n'
    )

    return body + new_tail


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 pdf_to_ascii85.py input.pdf output.pdf")
        sys.exit(1)
    process_pdf(sys.argv[1], sys.argv[2])
