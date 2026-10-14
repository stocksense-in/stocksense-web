"""Builds a tiny text PDF in memory, so scanner tests don't need a binary fixture."""


def make_pdf(pages: list[list[str]]) -> bytes:
    objects: list[str] = []

    def add(obj: str) -> int:
        objects.append(obj)
        return len(objects)

    font = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    contents = []
    for lines in pages:
        text = " ".join("(%s) Tj T*" % line.replace("(", r"\(").replace(")", r"\)") for line in lines)
        stream = f"BT /F1 10 Tf 40 800 Td 13 TL {text} ET"
        contents.append(add(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"))
    pages_id = len(objects) + len(pages) + 1
    page_ids = [
        add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Contents {c} 0 R "
            f"/Resources << /Font << /F1 {font} 0 R >> >> >>")
        for c in contents
    ]
    add("<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join(f"{p} 0 R" for p in page_ids), len(page_ids)))
    catalog = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    out = b"%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


SAMPLE_DRHP = [
    ["RISK FACTORS", "Our top 10 customers contributed 62.4% of our revenue from operations in Fiscal 2025,",
     "and the loss of any of them could adversely affect us.", "We have incurred losses in the past and may continue to do so."],
    ["OUTSTANDING LITIGATION", "There are outstanding litigation proceedings involving our Company. Claims",
     "against us aggregating to Rs. 142.5 crore are pending before various courts.",
     "Certain criminal proceedings are pending against our Promoters in Mumbai."],
    ["THE OFFER", "The Offer comprises a Fresh Issue of Rs. 300 crore and an Offer for Sale of",
     "Rs. 1,200 crore by the Selling Shareholders. We intend to use Rs. 75 crore",
     "towards general corporate purposes. Additional text so the page has enough characters to read."],
]
