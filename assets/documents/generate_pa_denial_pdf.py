#!/usr/bin/env python3
"""Generate the synthetic PA denial letter PDF (stdlib only, no deps)."""
import os

OUT = os.path.join(os.path.dirname(__file__), "pa_denial_letter.pdf")


def esc(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def wrap(text, width=92):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def simple_pdf(path, blocks):
    """blocks: list of (text, font, size) where font is F1 (helv) or F2 (bold)."""
    ops = ["BT"]
    y = 740
    for text, font, size in blocks:
        for line in wrap(text):
            ops.append(f"/{font} {size} Tf")
            ops.append(f"1 0 0 1 60 {y} Tm")
            ops.append(f"({esc(line)}) Tj")
            y -= size + 5
        y -= 6
    ops.append("ET")

    content = "\n".join(ops).encode("latin-1", "replace")
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
           b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        6: b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
           + content + b"\nendstream",
    }

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for n in sorted(objects):
        offsets[n] = len(out)
        out += f"{n} 0 obj\n".encode()
        out += objects[n] + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for n in sorted(objects):
        out += f"{offsets[n]:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n").encode()
    with open(path, "wb") as f:
        f.write(bytes(out))
    print(f"wrote {path} ({len(out)} bytes)")


blocks = [
    ("Blue Advantage Pharmacy Benefit Management", "F2", 14),
    ("Carelon Health - Prior Authorization Determination Notice", "F1", 10),
    ("", "F1", 8),
    ("NOTICE: REQUEST FOR PRIOR AUTHORIZATION - DENIED", "F2", 12),
    ("", "F1", 8),
    ("Member Name: Jordan Ellison", "F1", 10),
    ("Member ID: MEM-0004821", "F1", 10),
    ("Group Number: 60492-A", "F1", 10),
    ("Date of Notice: March 12, 2026", "F1", 10),
    ("Reference Number: PA-2026-0338471", "F1", 10),
    ("", "F1", 8),
    ("Medication Requested: Semaglutide 1 mg injection (GLP-1 Agonist, Tier 4)", "F1", 10),
    ("Prescriber: Dr. Marcus Chen, MD (NPI 1487302596)", "F1", 10),
    ("Prescribing Practice: Peachtree Endocrinology Associates, Atlanta, GA", "F1", 10),
    ("Diagnosis on File: E11.9 - Type 2 diabetes mellitus without complications", "F1", 10),
    ("Most Recent HbA1c on File: 7.9% (February 2026)", "F1", 10),
    ("Step Therapy Status: Not satisfied", "F1", 10),
    ("", "F1", 8),
    ("DETERMINATION: DENIED", "F2", 12),
    ("", "F1", 8),
    ("Denial Reason:", "F2", 10),
    ("The request for Semaglutide 1 mg does not meet the plan's coverage criteria. "
     "Per Section 2.1 of the Blue Advantage Formulary Guidelines (FORM-2026-001), "
     "GLP-1 agonists require documentation of a failed 90-day trial of at least two "
     "formulary alternatives at therapeutic dose, including Metformin plus one other "
     "oral antidiabetic agent. Pharmacy claims history shows a 45-day supply of "
     "Metformin ER 750 mg filled November 2025 through December 2025 with no "
     "additional fills, and no trial of a second oral agent. The member's HbA1c of "
     "7.9% does not satisfy the requirement of 7.5% or above on two consecutive "
     "readings. Step therapy requirements are not waived for member convenience.", "F1", 9),
    ("", "F1", 8),
    ("Appeal Rights:", "F2", 10),
    ("You or your prescriber may appeal this determination within 60 calendar days "
     "of the date of this notice. The appeal deadline for this denial is May 11, "
     "2026. A Level 1 appeal must include clinical documentation of medical "
     "necessity. Standard appeals are decided within 30 calendar days; urgent "
     "appeals within 72 hours. Your prescriber may also request a peer-to-peer "
     "review with the medical director, which does not extend the appeal deadline. "
     "If the Level 1 appeal is upheld, you may request an independent external "
     "review by the state Department of Insurance within 4 months.", "F1", 9),
    ("", "F1", 8),
    ("Alternative Options:", "F2", 10),
    ("Coverage may be reconsidered upon completion of a documented 90-day trial of "
     "Metformin plus one additional formulary oral antidiabetic (options include "
     "Glipizide, Sitagliptin, or Empagliflozin), with HbA1c reassessment at the "
     "end of the trial period. Your prescriber can submit a new PA request with "
     "the updated clinical documentation.", "F1", 9),
    ("", "F1", 8),
    ("Questions: Call the number on your member ID card or contact Pharmacy "
     "Benefit Management. This notice is a synthetic document created for "
     "training purposes and contains no real member data.", "F1", 9),
]

simple_pdf(OUT, blocks)
