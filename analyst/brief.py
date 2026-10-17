"""Extract a supplied PDF as company context, preserving page-level provenance."""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess

from analyst.schema import BriefPage, CompanyBrief


def extract_brief(path: Path, company_name: str = "Fizzera") -> CompanyBrief:
    executable = shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("pdftotext is required; install Poppler before loading the PDF brief")
    pdf = path.read_bytes()
    extraction = subprocess.run(
        [executable, "-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout
    parts = extraction.split("\f")
    if parts and not parts[-1].strip():
        parts.pop()
    pages = [BriefPage(page_number=i, text=text.strip()) for i, text in enumerate(parts, 1)]
    if not pages or not any(page.text for page in pages):
        raise ValueError("Company PDF contains no extractable text")
    text = "\n\f\n".join(page.text for page in pages)
    notes = ["Company-provided planning context; not independently verified market evidence."]
    if "fictional" in text.lower():
        notes.append("The brief explicitly labels some survey/customer research as fictional; preserve that status.")
    if "forecast" in text.lower():
        notes.append("Forecasts, targets, and proposed budgets must remain distinct from actual results.")
    if re.search(r"Unresolved question:\s*When\s*$", text):
        notes.append("The PDF ends with an incomplete question on page 18; do not invent the missing wording.")
    # Extract only explicitly stated monetary ceilings, never infer them from market articles.
    normalized = " ".join(text.split())
    envelope = re.search(r"maximum discretionary strategic investment envelope of CAD\s*\$([\d.]+)\s*million", normalized, re.I)
    launch = re.search(r"Maximum development and launch preparation budget:\s*CAD\s*\$([\d,]+)", normalized, re.I)
    return CompanyBrief(
        company_name=company_name, source_filename=path.name,
        pdf_sha256=hashlib.sha256(pdf).hexdigest(), text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        pages=pages, data_status_notes=notes,
        investment_envelope_cad=float(envelope[1]) * 1_000_000 if envelope else None,
        product_launch_budget_cad=float(launch[1].replace(",", "")) if launch else None,
    )
