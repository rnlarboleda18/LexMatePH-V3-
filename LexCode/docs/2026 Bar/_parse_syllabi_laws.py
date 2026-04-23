"""One-off: extract law citations from 2026 Bar syllabi text dump."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
text = (ROOT / "_syllabi_extract.txt").read_text(encoding="utf-8", errors="replace")
# PDF line break split the Remedial + Practical header across two lines
text = re.sub(
    r"(REMEDIAL LAW, LEGAL AND JUDICIAL ETHICS, WITH)\s*\n\s*(PRACTICAL EXERCISES \(\d+%\))",
    r"\1 \2",
    text,
)

header_re = re.compile(
    r"^([A-Z][A-Z0-9 ,/&'\u2013\-]+)\s*\(([0-9]+)%\)\s*$",
    re.MULTILINE,
)
parts = [(m.start(), m.group(1).strip(), m.group(2)) for m in header_re.finditer(text)]

chunks = []
for i, (start, name, pct) in enumerate(parts):
    end = parts[i + 1][0] if i + 1 < len(parts) else len(text)
    chunks.append((name, pct, text[start:end]))

patterns = [
    ("R.A.", re.compile(r"R\.A\.\s*No\.\s*([0-9]+)", re.I)),
    (
        "P.D.",
        re.compile(
            r"(?:Presidential Decree\s*(?:\[P\.D\.\]\s*)?|P\.D\.\s*)No\.\s*([0-9]+)",
            re.I,
        ),
    ),
    ("B.P.", re.compile(r"B\.P\.\s*Blg\.\s*([0-9]+)", re.I)),
    ("E.O.", re.compile(r"E\.O\.\s*No\.\s*([0-9]+)", re.I)),
    ("Executive Order (long)", re.compile(r"Executive Order No\.\s*([0-9]+)", re.I)),
    ("D.O.", re.compile(r"D\.O\.\s*No\.\s*([0-9]+)", re.I)),
    ("A.M.", re.compile(r"A\.M\.\s*No\.\s*([0-9\-]+)", re.I)),
    ("Commonwealth Act", re.compile(r"Commonwealth Act No\.\s*([0-9]+)", re.I)),
]


def extract_laws(body: str) -> set[str]:
    refs: set[str] = set()
    for label, rx in patterns:
        for m in rx.finditer(body):
            if label == "Executive Order (long)":
                refs.add(f"Executive Order No. {m.group(1)}")
            else:
                refs.add(f"{label} {m.group(1)}")

    if "1987 Constitution" in body or "Constitution, Art." in body:
        refs.add("1987 Constitution")
    if "Civil Code" in body or "(NCC)" in body or " NCC," in body:
        refs.add("Civil Code of the Philippines (NCC)")
    if "Revised Penal Code" in body or "(RPC)" in body or " RPC," in body:
        refs.add("Revised Penal Code (RPC)")
    if "Labor Code" in body or "(LC)" in body:
        refs.add("Labor Code of the Philippines (LC)")
    if "Family Code" in body or "Executive Order No. 209" in body:
        refs.add("Family Code (E.O. 209 as amended)")
    if "Rules of Court" in body:
        refs.add("Rules of Court (specific Rules cited in syllabus)")
    if "Local Government Code" in body or "R.A. No. 7160" in body:
        refs.add("Local Government Code (R.A. 7160) — where cited")
    if "National Internal Revenue Code" in body or "NIRC" in body:
        refs.add("National Internal Revenue Code of 1997 (NIRC), as amended")
    if "Revised Administrative Code of 1987" in body:
        refs.add("Executive Order No. 292 — Revised Administrative Code of 1987 (Book I, etc., as cited)")
    return refs


out_lines: list[str] = []
for name, pct, body in chunks:
    laws = extract_laws(body)
    sorted_laws = sorted(laws)
    out_lines.append(f"## {name} ({pct}%)")
    out_lines.append("")
    for r in sorted_laws:
        out_lines.append(f"- {r}")
    out_lines.append("")

(ROOT / "_syllabi_laws_by_subject.md").write_text("\n".join(out_lines), encoding="utf-8")
print(f"Wrote {len(chunks)} subjects to _syllabi_laws_by_subject.md")
