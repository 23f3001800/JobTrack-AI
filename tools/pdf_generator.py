"""PDF Resume Generator — creates tailored resumes per job application.

WHY generate PDFs instead of just text?
1. Job portals require PDF uploads — text won't work
2. Professional formatting (headers, bullets, spacing) matters
3. Each resume is tailored to the specific job's requirements
4. PDF is portable and renders identically everywhere

Uses ReportLab (pure Python, no system deps) for PDF generation.
The layout mimics a clean, ATS-friendly single-column resume format
that parses well with automated systems while still looking professional.
"""
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, HRFlowable
)
from reportlab.lib.enums import TA_CENTER


# ──────────────────────────────────────────────
# Style configuration
# ──────────────────────────────────────────────

# WHY these specific colors? Dark charcoal for text (not pure black —
# easier on the eyes), indigo accent for section headers to add a
# touch of personality while remaining ATS-friendly.
COLOR_TEXT = HexColor("#1a1a2e")
COLOR_ACCENT = HexColor("#4338ca")   # Indigo — matches dashboard theme
COLOR_SUBTLE = HexColor("#64748b")   # Slate for secondary text


def _build_styles():
    """Create paragraph styles for the resume.

    WHY custom styles instead of using defaults?
    Default ReportLab styles are ugly — Times New Roman, big margins.
    These custom styles create a modern, clean look that's both
    human-readable and ATS-compatible.
    """
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "ResumeName",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=COLOR_TEXT,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
    ))

    styles.add(ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=COLOR_SUBTLE,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    ))

    styles.add(ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=COLOR_ACCENT,
        spaceBefore=5 * mm,
        spaceAfter=2 * mm,
        borderWidth=0,
    ))

    styles.add(ParagraphStyle(
        "BulletItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=COLOR_TEXT,
        leftIndent=8 * mm,
        bulletIndent=3 * mm,
        spaceBefore=1 * mm,
        spaceAfter=1 * mm,
        leading=13,
    ))

    styles.add(ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=COLOR_TEXT,
        spaceAfter=2 * mm,
        leading=13,
    ))

    styles.add(ParagraphStyle(
        "SubHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=COLOR_TEXT,
        spaceBefore=3 * mm,
        spaceAfter=1 * mm,
    ))

    return styles


def _parse_bullets(text: str) -> list[str]:
    """Extract bullet points from text.

    WHY parse bullets from text?
    The Writer agent returns tailored bullets as markdown-style text
    (lines starting with •, -, or *). We need to split them into
    individual items for proper PDF bullet formatting.
    """
    lines = text.strip().split("\n")
    bullets = []
    for line in lines:
        line = line.strip()
        # Remove common bullet prefixes
        cleaned = re.sub(r"^[•\-\*]\s*", "", line)
        if cleaned:
            bullets.append(cleaned)
    return bullets


def generate_resume_pdf(
    name: str,
    email: str,
    phone: str,
    background: str,
    tailored_bullets: str,
    job_title: str,
    company: str,
    role_fit: str = "",
    output_dir: str = "",
    parsed_profile: dict | None = None,
    linkedin_url: str = "",
    github_url: str = "",
) -> str:
    """Generate a tailored PDF resume for a specific job application.

    Args:
        name: Candidate's full name
        email: Contact email
        phone: Contact phone
        background: General background/summary
        tailored_bullets: Job-specific CV bullets from the Writer agent
        job_title: Target job title (used in objective)
        company: Target company name
        role_fit: Role fit analysis (optional, adds talking points)
        output_dir: Directory to save the PDF (default: workspace/)
        parsed_profile: Full structured resume data (experience, education, etc.)
        linkedin_url: LinkedIn profile URL
        github_url: GitHub profile URL

    Returns:
        File path of the generated PDF.

    WHY accept both flat params AND parsed_profile?
    Backward compatibility — existing callers pass flat params.
    New callers (resume_generator agent) pass parsed_profile for
    full-fidelity resume generation with all sections.
    """
    if not output_dir:
        output_dir = os.getenv("WORKSPACE_DIR", "./workspace")
    os.makedirs(output_dir, exist_ok=True)

    # Sanitize filename — remove special characters
    safe_company = re.sub(r"[^\w\s-]", "", company).strip().replace(" ", "_")
    safe_title = re.sub(r"[^\w\s-]", "", job_title).strip().replace(" ", "_")
    filename = f"Resume_{safe_company}_{safe_title}.pdf"
    filepath = os.path.join(output_dir, filename)

    # Create the PDF document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = _build_styles()
    story = []

    # ── Header: Name + Contact ──
    story.append(Paragraph(name, styles["ResumeName"]))
    contact_parts = [p for p in [email, phone] if p]
    if linkedin_url:
        contact_parts.append(linkedin_url)
    if github_url:
        contact_parts.append(github_url)
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), styles["ResumeContact"]))

    # Divider line
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=COLOR_SUBTLE,
        spaceBefore=2 * mm, spaceAfter=3 * mm,
    ))

    # ── Professional Summary ──
    story.append(Paragraph("PROFESSIONAL SUMMARY", styles["SectionHeader"]))
    summary = (
        f"Experienced professional targeting the <b>{job_title}</b> role at "
        f"<b>{company}</b>. {background}"
    )
    story.append(Paragraph(summary, styles["BodyText2"]))

    # ── Tailored Experience Bullets ──
    story.append(Paragraph("KEY ACHIEVEMENTS", styles["SectionHeader"]))
    bullets = _parse_bullets(tailored_bullets)
    for bullet in bullets:
        story.append(Paragraph(
            f"• {bullet}",
            styles["BulletItem"],
        ))

    # ── Work Experience (from parsed profile) ──
    if parsed_profile and parsed_profile.get("experience"):
        story.append(Paragraph("WORK EXPERIENCE", styles["SectionHeader"]))
        for exp in parsed_profile["experience"]:
            title = exp.get("title", "")
            co = exp.get("company", "")
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")
            date_range = f"{start} — {end}" if start else ""
            header = f"<b>{title}</b>"
            if co:
                header += f" at {co}"
            if date_range:
                header += f" ({date_range})"
            story.append(Paragraph(header, styles["SubHeader"]))
            for b in exp.get("bullets", []):
                story.append(Paragraph(f"• {b}", styles["BulletItem"]))

    # ── Education (from parsed profile) ──
    if parsed_profile and parsed_profile.get("education"):
        story.append(Paragraph("EDUCATION", styles["SectionHeader"]))
        for edu in parsed_profile["education"]:
            degree = edu.get("degree", "")
            inst = edu.get("institution", "")
            year = edu.get("year", "")
            line = f"<b>{degree}</b>"
            if inst:
                line += f" — {inst}"
            if year:
                line += f" ({year})"
            story.append(Paragraph(line, styles["SubHeader"]))
            details = edu.get("details", "")
            if details:
                story.append(Paragraph(details, styles["BodyText2"]))

    # ── Skills (from parsed profile or fallback) ──
    skills = (
        parsed_profile.get("skills", [])
        if parsed_profile
        else []
    )
    if skills:
        story.append(Paragraph("SKILLS", styles["SectionHeader"]))
        # Display as comma-separated for ATS readability
        skills_text = " • ".join(skills)
        story.append(Paragraph(skills_text, styles["BodyText2"]))

    # ── Projects (from parsed profile) ──
    if parsed_profile and parsed_profile.get("projects"):
        story.append(Paragraph("PROJECTS", styles["SectionHeader"]))
        for proj in parsed_profile["projects"][:5]:  # Cap at 5
            pname = proj.get("name", "")
            pdesc = proj.get("description", "")
            ptech = proj.get("technologies", [])
            header = f"<b>{pname}</b>"
            if ptech:
                header += f" ({', '.join(ptech)})"
            story.append(Paragraph(header, styles["SubHeader"]))
            if pdesc:
                story.append(Paragraph(pdesc, styles["BodyText2"]))

    # ── Certifications (from parsed profile) ──
    if parsed_profile and parsed_profile.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", styles["SectionHeader"]))
        for cert in parsed_profile["certifications"]:
            story.append(Paragraph(f"• {cert}", styles["BulletItem"]))

    # ── Role Fit / Talking Points (if available) ──
    if role_fit:
        story.append(Paragraph("ROLE FIT HIGHLIGHTS", styles["SectionHeader"]))
        fit_bullets = _parse_bullets(role_fit)
        for bullet in fit_bullets[:5]:  # Cap at 5 to keep it concise
            story.append(Paragraph(
                f"• {bullet}",
                styles["BulletItem"],
            ))

    # ── Build the PDF ──
    doc.build(story)

    return filepath

