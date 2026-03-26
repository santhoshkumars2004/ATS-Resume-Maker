"""PDF Parser — extracts structured text from uploaded resume PDFs."""
import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract all text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Full text content of the PDF.
    """
    pdf_path = Path(pdf_path)
    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts)


def extract_sections_from_pdf(pdf_path: str | Path) -> dict[str, str]:
    """Extract and identify common resume sections from a PDF.

    Attempts to split the resume into sections like Summary, Experience,
    Skills, Education, etc.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dictionary mapping section names to their content.
    """
    full_text = extract_text_from_pdf(pdf_path)
    if not full_text:
        return {"full_text": ""}

    # Common resume section headers (case-insensitive matching)
    section_headers = [
        "summary", "professional summary", "objective", "profile",
        "experience", "work experience", "professional experience", "employment",
        "skills", "technical skills", "core competencies", "technologies",
        "education", "academic", "qualifications",
        "projects", "key projects", "notable projects",
        "certifications", "certificates", "awards",
        "publications", "research",
    ]

    sections = {"full_text": full_text}
    lines = full_text.split("\n")
    current_section = "header"
    current_content = []

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Check if this line is a section header
        is_header = False
        for header in section_headers:
            if line_lower == header or line_lower.startswith(header + ":") or line_lower.startswith(header + " "):
                # Save previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = header.split()[0]  # Use first word as key
                current_content = []
                is_header = True
                break

        if not is_header and line_stripped:
            current_content.append(line_stripped)

    # Save the last section
    if current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections
