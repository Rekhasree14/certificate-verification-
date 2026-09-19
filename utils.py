import os
import uuid
import hashlib
import qrcode
from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_unique_token():
    """Generate a cryptographically strong unique identity token (UUID4)."""
    return str(uuid.uuid4())

def calculate_file_sha256(filepath):
    """
    Calculate the SHA-256 hash of a file by reading in chunks.
    Returns 64-character hexadecimal string.
    """
    if not os.path.exists(filepath):
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def calculate_data_sha256(data_dict):
    """
    Calculate canonical SHA-256 hash of certificate metadata fields.
    Ensures data consistency regardless of file state.
    """
    canonical_string = (
        f"CERT_ID:{data_dict.get('certificate_id', '').strip()}|"
        f"CANDIDATE:{data_dict.get('candidate_name', '').strip()}|"
        f"COURSE:{data_dict.get('course_name', '').strip()}|"
        f"INSTITUTION:{data_dict.get('institution_name', '').strip()}|"
        f"ISSUE_DATE:{data_dict.get('issue_date', '').strip()}|"
        f"TYPE:{data_dict.get('certificate_type', '').strip()}"
    )
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()

def generate_qr_code(token, base_url, output_path):
    """
    Generate a QR code containing the verification URL.
    Saves image as PNG at output_path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    verification_url = f"{base_url.rstrip('/')}/verify/{token}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#0d233a", back_color="white")
    img.save(output_path)
    return output_path

def generate_certificate_pdf(cert_dict, qr_code_path, output_path):
    """
    Generate a professional digital certificate as a PDF using ReportLab.
    Contains ornate borders, institution details, candidate name, course,
    unique token, embedded QR code, and cryptographic verification info.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Use landscape A4 (841.89 pt width x 595.27 pt height)
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(output_path, pagesize=landscape(A4))

    # --- Draw Ornate Borders ---
    # Background subtle tint
    c.setFillColor(colors.HexColor("#FCFDFD"))
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # Outer border (Deep Navy)
    c.setStrokeColor(colors.HexColor("#0D233A"))
    c.setLineWidth(5)
    c.rect(20, 20, page_width - 40, page_height - 40)

    # Inner border (Gold / Bronze)
    c.setStrokeColor(colors.HexColor("#C59B27"))
    c.setLineWidth(2)
    c.rect(28, 28, page_width - 56, page_height - 56)

    # Decorative Corner Accents
    corner_size = 30
    c.setFillColor(colors.HexColor("#0D233A"))
    # Top-left corner box
    c.rect(28, page_height - 28 - corner_size, corner_size, corner_size, fill=1, stroke=0)
    # Top-right corner box
    c.rect(page_width - 28 - corner_size, page_height - 28 - corner_size, corner_size, corner_size, fill=1, stroke=0)
    # Bottom-left corner box
    c.rect(28, 28, corner_size, corner_size, fill=1, stroke=0)
    # Bottom-right corner box
    c.rect(page_width - 28 - corner_size, 28, corner_size, corner_size, fill=1, stroke=0)

    # --- Header / Institution ---
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.HexColor("#0D233A"))
    c.drawCentredString(page_width / 2.0, page_height - 75, cert_dict.get('institution_name', 'National Institute of Technology'))

    # Sub-header
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#C59B27"))
    c.drawCentredString(page_width / 2.0, page_height - 95, "OFFICIAL VERIFIABLE DIGITAL CREDENTIAL")

    # Horizontal divider rule
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(1)
    c.line(100, page_height - 110, page_width - 100, page_height - 110)

    # Certificate Title
    c.setFont("Times-BoldItalic", 28)
    c.setFillColor(colors.HexColor("#1A365D"))
    c.drawCentredString(page_width / 2.0, page_height - 150, "Certificate of Completion")

    # "This is to certify that"
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor("#4A5568"))
    c.drawCentredString(page_width / 2.0, page_height - 185, "This is proudly presented to")

    # Candidate Name (Prominent & Elegant)
    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(colors.HexColor("#0D233A"))
    c.drawCentredString(page_width / 2.0, page_height - 230, cert_dict.get('candidate_name', 'Candidate Name'))

    # Name underline
    c.setStrokeColor(colors.HexColor("#C59B27"))
    c.setLineWidth(2)
    name_width = c.stringWidth(cert_dict.get('candidate_name', 'Candidate Name'), "Helvetica-Bold", 30)
    c.line((page_width - name_width) / 2.0 - 20, page_height - 238, (page_width + name_width) / 2.0 + 20, page_height - 238)

    # Description text
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#4A5568"))
    c.drawCentredString(
        page_width / 2.0,
        page_height - 275,
        f"for successfully completing the specialized professional program in"
    )

    # Course Name
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#2B6CB0"))
    c.drawCentredString(page_width / 2.0, page_height - 310, cert_dict.get('course_name', 'Course Name'))

    # Metadata Badges / Info Line
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#4A5568"))
    c.drawString(70, page_height - 365, f"Certificate ID: {cert_dict.get('certificate_id', 'N/A')}")
    c.drawString(70, page_height - 385, f"Issue Date: {cert_dict.get('issue_date', 'N/A')}")
    c.drawString(70, page_height - 405, f"Type: {cert_dict.get('certificate_type', 'Course Completion')}")

    # Signatures
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#2D3748"))
    c.drawString(320, page_height - 400, "___________________________")
    c.drawString(340, page_height - 418, "Authorized Signatory")

    c.drawString(page_width - 270, page_height - 400, "___________________________")
    c.drawString(page_width - 240, page_height - 418, "Director of Academics")

    # Bottom Divider
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(1)
    c.line(50, page_height - 440, page_width - 50, page_height - 440)

    # Verification Section (Bottom Box)
    # Embed QR Code if available
    qr_x = 70
    qr_y = 45
    qr_size = 90
    if qr_code_path and os.path.exists(qr_code_path):
        c.drawImage(qr_code_path, qr_x, qr_y, width=qr_size, height=qr_size)

    # QR Verification Instructions
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#0D233A"))
    c.drawString(175, 120, "TAMPER-PROOF CRYPTOGRAPHIC VERIFICATION")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#4A5568"))
    c.drawString(175, 104, "Scan the QR code to verify this certificate's authenticity instantly.")
    c.drawString(175, 90, f"Identity Token: {cert_dict.get('token', 'N/A')}")

    # Display SHA-256 hash preview if present
    sha_preview = cert_dict.get('sha256_hash', '')
    if sha_preview:
        c.setFont("Courier", 8)
        c.setFillColor(colors.HexColor("#718096"))
        c.drawString(175, 74, f"SHA-256 Digest: {sha_preview[:36]}...{sha_preview[-16:]}")
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(175, 58, "Any alteration of document content invalidates this digital signature.")

    c.showPage()
    c.save()
    return output_path
