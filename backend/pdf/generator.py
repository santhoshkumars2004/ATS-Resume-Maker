"""PDF Generator — creates professional resume PDFs from optimized content."""
from pathlib import Path
from fpdf import FPDF


class ResumePDF(FPDF):
    """Custom PDF class for generating professional resumes."""

    # Color scheme (dark navy + accent)
    NAVY = (26, 32, 44)
    DARK_GRAY = (45, 55, 72)
    MEDIUM_GRAY = (113, 128, 150)
    LIGHT_GRAY = (226, 232, 240)
    ACCENT = (99, 102, 241)  # Indigo
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        """Minimal header — just a thin accent line at the top."""
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(0.8)
        self.line(10, 8, self.w - 10, 8)

    def footer(self):
        """Page number footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*self.MEDIUM_GRAY)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_name(self, name: str):
        """Add the candidate name as a large header."""
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*self.NAVY)
        self.cell(0, 12, name, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

    def add_contact_info(self, contact: str):
        """Add contact info line (email | phone | location | linkedin)."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.MEDIUM_GRAY)
        self.cell(0, 6, contact, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(6)

    def add_section_header(self, title: str):
        """Add a styled section header with accent underline."""
        self.ln(4)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.ACCENT)
        self.cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
        # Accent underline
        self.set_draw_color(*self.ACCENT)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(10, y, self.w - 10, y)
        self.ln(4)

    def add_text(self, text: str, bold: bool = False):
        """Add a paragraph of text."""
        style = "B" if bold else ""
        self.set_font("Helvetica", style, 10)
        self.set_text_color(*self.BLACK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def add_experience_entry(self, title: str, company: str, dates: str, bullets: list[str]):
        """Add a work experience entry with title, company, dates, and bullets."""
        # Title and company
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.NAVY)
        self.cell(0, 6, f"{title} | {company}", new_x="LMARGIN", new_y="NEXT")

        # Dates
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*self.MEDIUM_GRAY)
        self.cell(0, 5, dates, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # Bullets
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*self.DARK_GRAY)
        for bullet in bullets:
            bullet_text = f"  \u2022  {bullet}"
            self.multi_cell(0, 5, bullet_text)
            self.ln(1)

        self.ln(3)

    def add_skills_row(self, category: str, skills: list[str]):
        """Add a skills category row."""
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(*self.NAVY)
        self.cell(40, 5.5, f"{category}:")

        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*self.DARK_GRAY)
        skills_text = ", ".join(skills)
        self.multi_cell(0, 5.5, skills_text)
        self.ln(1)

    def add_education_entry(self, degree: str, school: str, dates: str):
        """Add an education entry."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.NAVY)
        self.cell(0, 6, degree, new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*self.DARK_GRAY)
        self.cell(0, 5, f"{school} | {dates}", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def add_bullet_list(self, items: list[str]):
        """Add a simple bullet list."""
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*self.DARK_GRAY)
        for item in items:
            self.multi_cell(0, 5, f"  \u2022  {item}")
            self.ln(1)


def generate_optimized_pdf(
    original_sections: dict[str, str],
    optimization: dict,
    output_path: str | Path,
    company_name: str = "",
) -> Path:
    """Generate a professional PDF resume with optimized content.

    Args:
        original_sections: Parsed sections from the original PDF.
        optimization: Optimization results from the resume optimizer agent.
        output_path: Where to save the generated PDF.
        company_name: Target company name for the filename.

    Returns:
        Path to the generated PDF file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = ResumePDF()
    pdf.add_page()

    full_text = original_sections.get("full_text", "")

    # Extract name from header section (usually first non-empty line)
    header_text = original_sections.get("header", "")
    name_lines = [l for l in header_text.split("\n") if l.strip()] if header_text else []
    name = name_lines[0] if name_lines else "Your Name"

    # Contact info (second line of header, or remaining header lines)
    contact = " | ".join(name_lines[1:3]) if len(name_lines) > 1 else ""

    pdf.add_name(name)
    if contact:
        pdf.add_contact_info(contact)

    # Professional Summary
    summary = optimization.get("summary_rewrite", "")
    if not summary:
        summary = original_sections.get("summary", original_sections.get("professional", ""))
    if summary:
        pdf.add_section_header("Professional Summary")
        pdf.add_text(summary)

    # Skills Section (optimized)
    skills_to_reorder = optimization.get("skills_to_reorder", [])
    skills_to_add = optimization.get("skills_to_add", [])
    all_skills = list(skills_to_reorder)
    for s in skills_to_add:
        if s not in all_skills:
            all_skills.append(s)

    if all_skills:
        pdf.add_section_header("Technical Skills")
        categorized = _categorize_skills(all_skills)
        for category, skills in categorized.items():
            pdf.add_skills_row(category, skills)
    elif "skills" in original_sections or "technical" in original_sections:
        pdf.add_section_header("Technical Skills")
        skills_text = original_sections.get("skills", original_sections.get("technical", ""))
        pdf.add_text(skills_text)

    # Experience Section (with rewrites applied)
    experience_text = original_sections.get("experience", original_sections.get("work", ""))
    rewrites = {r["original"]: r["replacement"] for r in optimization.get("experience_rewrites", []) if r.get("original") and r.get("replacement")}

    if experience_text:
        pdf.add_section_header("Professional Experience")
        # Apply rewrites to the experience text
        modified_exp = experience_text
        for original, replacement in rewrites.items():
            modified_exp = modified_exp.replace(original, replacement)

        # Split into bullet-like lines
        for line in modified_exp.split("\n"):
            line = line.strip()
            if not line:
                continue
            if any(line.startswith(c) for c in ["•", "-", "◦", "▪", "●"]):
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*ResumePDF.DARK_GRAY)
                pdf.multi_cell(0, 5, f"  {line}")
                pdf.ln(1)
            else:
                # Likely a title/company line
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(*ResumePDF.NAVY)
                pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)

    # Education
    education_text = original_sections.get("education", original_sections.get("academic", ""))
    if education_text:
        pdf.add_section_header("Education")
        for line in education_text.split("\n"):
            line = line.strip()
            if line:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*ResumePDF.DARK_GRAY)
                pdf.cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Projects
    projects_text = original_sections.get("projects", original_sections.get("key", ""))
    if projects_text:
        pdf.add_section_header("Projects")
        for line in projects_text.split("\n"):
            line = line.strip()
            if line:
                if any(line.startswith(c) for c in ["•", "-", "◦"]):
                    pdf.set_font("Helvetica", "", 9.5)
                    pdf.set_text_color(*ResumePDF.DARK_GRAY)
                    pdf.multi_cell(0, 5, f"  {line}")
                    pdf.ln(1)
                else:
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.set_text_color(*ResumePDF.NAVY)
                    pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(1)

    # Certifications
    certs_text = original_sections.get("certifications", original_sections.get("certificates", ""))
    if certs_text:
        pdf.add_section_header("Certifications")
        for line in certs_text.split("\n"):
            line = line.strip()
            if line:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(*ResumePDF.DARK_GRAY)
                pdf.multi_cell(0, 5, f"  \u2022  {line}")
                pdf.ln(1)

    # Keywords injection (add as a subtle "Keywords" section at the bottom)
    keywords = optimization.get("keywords_to_inject", [])
    if keywords:
        pdf.add_section_header("Key Competencies")
        keywords_text = " | ".join(keywords)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*ResumePDF.MEDIUM_GRAY)
        pdf.multi_cell(0, 5, keywords_text, align="C")

    # Save the PDF
    pdf.output(str(output_path))
    return output_path


def _categorize_skills(skills: list[str]) -> dict[str, list[str]]:
    """Auto-categorize skills into groups."""
    categories = {
        "Languages": [],
        "Frameworks & Libraries": [],
        "DevOps & Cloud": [],
        "Databases": [],
        "Tools & Practices": [],
    }

    lang_kw = {"python", "javascript", "typescript", "java", "go", "rust", "c++", "c#", "ruby", "sql", "r", "scala", "kotlin", "swift", "c", "php", "perl", "matlab"}
    framework_kw = {"react", "angular", "vue", "next.js", "fastapi", "django", "flask", "spring", "express", "node.js", "svelte", "graphql", ".net", "tailwind", "bootstrap"}
    devops_kw = {"docker", "kubernetes", "ci/cd", "jenkins", "github actions", "terraform", "ansible", "aws", "gcp", "azure", "helm", "argocd", "linux", "nginx"}
    db_kw = {"postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb", "cassandra", "sqlite", "oracle", "sql server"}

    for skill in skills:
        sl = skill.lower().strip()
        if sl in lang_kw:
            categories["Languages"].append(skill)
        elif sl in framework_kw:
            categories["Frameworks & Libraries"].append(skill)
        elif sl in devops_kw:
            categories["DevOps & Cloud"].append(skill)
        elif sl in db_kw:
            categories["Databases"].append(skill)
        else:
            categories["Tools & Practices"].append(skill)

    return {k: v for k, v in categories.items() if v}
