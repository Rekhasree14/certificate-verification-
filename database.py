import os
import sqlite3
from werkzeug.security import generate_password_hash
from config import Config
from utils import (
    generate_unique_token,
    generate_qr_code,
    generate_certificate_pdf,
    calculate_file_sha256
)

def get_db_connection():
    """Establish connection to the SQLite database with Row factory."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(seed_sample_data=True):
    """
    Initialize database schema and seed default admin and sample certificates.
    Safe to run repeatedly.
    """
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CERTIFICATES_FOLDER, exist_ok=True)
    os.makedirs(Config.QRCODE_FOLDER, exist_ok=True)

    conn = get_db_connection()
    schema_path = os.path.join(Config.BASE_DIR, 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # Seed Default Admin Account
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (Config.DEFAULT_ADMIN_USERNAME,))
    admin = cursor.fetchone()
    if not admin:
        hashed_pw = generate_password_hash(Config.DEFAULT_ADMIN_PASSWORD)
        cursor.execute(
            """
            INSERT INTO users (name, email, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                Config.DEFAULT_ADMIN_NAME,
                Config.DEFAULT_ADMIN_EMAIL,
                Config.DEFAULT_ADMIN_USERNAME,
                hashed_pw,
                'admin'
            )
        )
        conn.commit()

    # Seed Sample Certificates if table is empty
    if seed_sample_data:
        cursor.execute("SELECT COUNT(*) as count FROM certificates")
        cert_count = cursor.fetchone()['count']
        if cert_count == 0:
            sample_certs = [
                {
                    "certificate_id": "CERT-1001",
                    "candidate_name": "Rahul Kumar",
                    "course_name": "Python Programming",
                    "institution_name": "National Institute of Technology",
                    "issue_date": "2026-05-15",
                    "certificate_type": "Course Completion"
                },
                {
                    "certificate_id": "CERT-1002",
                    "candidate_name": "Ananya Sharma",
                    "course_name": "Web Development",
                    "institution_name": "Delhi Technological University",
                    "issue_date": "2026-06-20",
                    "certificate_type": "Diploma"
                },
                {
                    "certificate_id": "CERT-1003",
                    "candidate_name": "Arjun Reddy",
                    "course_name": "Data Analytics",
                    "institution_name": "Indian Institute of Science",
                    "issue_date": "2026-07-10",
                    "certificate_type": "Professional Certificate"
                }
            ]

            for sc in sample_certs:
                token = generate_unique_token()
                qr_filename = f"{token}.png"
                qr_path = os.path.join(Config.QRCODE_FOLDER, qr_filename)
                generate_qr_code(token, "http://127.0.0.1:5000", qr_path)

                pdf_filename = f"{sc['certificate_id']}.pdf"
                pdf_path = os.path.join(Config.CERTIFICATES_FOLDER, pdf_filename)

                cert_meta = {
                    **sc,
                    "token": token,
                    "sha256_hash": ""
                }
                # Initial generation to calculate PDF hash
                generate_certificate_pdf(cert_meta, qr_path, pdf_path)
                file_hash = calculate_file_sha256(pdf_path)

                # Re-generate PDF with actual SHA-256 fingerprint displayed
                cert_meta["sha256_hash"] = file_hash
                generate_certificate_pdf(cert_meta, qr_path, pdf_path)
                final_hash = calculate_file_sha256(pdf_path)

                cursor.execute(
                    """
                    INSERT INTO certificates (
                        certificate_id, candidate_name, course_name,
                        institution_name, issue_date, certificate_type,
                        file_path, sha256_hash, token, qr_code_path, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sc['certificate_id'],
                        sc['candidate_name'],
                        sc['course_name'],
                        sc['institution_name'],
                        sc['issue_date'],
                        sc['certificate_type'],
                        pdf_path,
                        final_hash,
                        token,
                        os.path.join('static', 'qrcodes', qr_filename),
                        'VALID'
                    )
                )
            conn.commit()

    conn.close()

# --- User Functions ---

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def create_user(name, email, username, password, role='admin'):
    conn = get_db_connection()
    hashed_pw = generate_password_hash(password)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (name, email, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, email, username, hashed_pw, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

# --- Certificate Functions ---

def create_certificate(certificate_id, candidate_name, course_name, institution_name,
                       issue_date, certificate_type, file_path, sha256_hash, token,
                       qr_code_path, status='VALID'):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO certificates (
                certificate_id, candidate_name, course_name,
                institution_name, issue_date, certificate_type,
                file_path, sha256_hash, token, qr_code_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                certificate_id, candidate_name, course_name,
                institution_name, issue_date, certificate_type,
                file_path, sha256_hash, token, qr_code_path, status
            )
        )
        conn.commit()
        cert_id = cursor.lastrowid
        conn.close()
        return cert_id
    except sqlite3.IntegrityError as e:
        conn.close()
        raise e

def get_certificate_by_id(cert_id):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    conn.close()
    return cert

def get_certificate_by_token(token):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE token = ?", (token.strip(),)).fetchone()
    conn.close()
    return cert

def get_certificate_by_cert_id(certificate_id):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id.strip(),)).fetchone()
    conn.close()
    return cert

def get_certificate_by_hash(sha256_hash):
    conn = get_db_connection()
    cert = conn.execute("SELECT * FROM certificates WHERE sha256_hash = ?", (sha256_hash.strip(),)).fetchone()
    conn.close()
    return cert

def get_all_certificates(search_query=None, status_filter=None):
    conn = get_db_connection()
    sql = "SELECT * FROM certificates WHERE 1=1"
    params = []

    if search_query:
        sql += """ AND (
            candidate_name LIKE ? OR
            certificate_id LIKE ? OR
            course_name LIKE ? OR
            token LIKE ?
        )"""
        q = f"%{search_query.strip()}%"
        params.extend([q, q, q, q])

    if status_filter:
        sql += " AND status = ?"
        params.append(status_filter)

    sql += " ORDER BY id DESC"
    certs = conn.execute(sql, params).fetchall()
    conn.close()
    return certs

def update_certificate_status(cert_id, status):
    conn = get_db_connection()
    conn.execute(
        "UPDATE certificates SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, cert_id)
    )
    conn.commit()
    conn.close()

def reissue_certificate(cert_id, new_token, new_sha256, new_file_path, new_qr_path, new_issue_date=None):
    conn = get_db_connection()
    if new_issue_date:
        conn.execute(
            """
            UPDATE certificates
            SET token = ?, sha256_hash = ?, file_path = ?, qr_code_path = ?,
                issue_date = ?, status = 'VALID', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_token, new_sha256, new_file_path, new_qr_path, new_issue_date, cert_id)
        )
    else:
        conn.execute(
            """
            UPDATE certificates
            SET token = ?, sha256_hash = ?, file_path = ?, qr_code_path = ?,
                status = 'VALID', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_token, new_sha256, new_file_path, new_qr_path, cert_id)
        )
    conn.commit()
    conn.close()

def simulate_tampering(cert_id):
    """
    Simulates tampering of a certificate for college project presentation.
    Modifies the generated certificate PDF file on disk by appending arbitrary bytes,
    WITHOUT updating the stored hash in the database.
    This guarantees that the newly calculated hash differs from the stored hash!
    """
    cert = get_certificate_by_id(cert_id)
    if not cert or not cert['file_path'] or not os.path.exists(cert['file_path']):
        return False

    file_path = cert['file_path']
    with open(file_path, 'ab') as f:
        f.write(b"\n% TAMPERED DATA INJECTED FOR DEMONSTRATION PURPOSE %\n")

    return True

# --- Verification History Functions ---

def log_verification(certificate_id, token_entered, verification_result, verification_method):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO verifications (certificate_id, token_entered, verification_result, verification_method)
        VALUES (?, ?, ?, ?)
        """,
        (certificate_id, token_entered, verification_result, verification_method)
    )
    conn.commit()
    conn.close()

def get_verification_history(limit=100):
    conn = get_db_connection()
    query = """
        SELECT v.*, c.certificate_id as cert_code, c.candidate_name, c.course_name
        FROM verifications v
        LEFT JOIN certificates c ON v.certificate_id = c.id
        ORDER BY v.id DESC
        LIMIT ?
    """
    records = conn.execute(query, (limit,)).fetchall()
    conn.close()
    return records

def get_dashboard_stats():
    conn = get_db_connection()
    total_certs = conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0]
    valid_certs = conn.execute("SELECT COUNT(*) FROM certificates WHERE status = 'VALID'").fetchone()[0]
    revoked_certs = conn.execute("SELECT COUNT(*) FROM certificates WHERE status = 'REVOKED'").fetchone()[0]
    total_verifications = conn.execute("SELECT COUNT(*) FROM verifications").fetchone()[0]

    recent_certs = conn.execute("SELECT * FROM certificates ORDER BY id DESC LIMIT 5").fetchall()

    recent_verifications = conn.execute(
        """
        SELECT v.*, c.certificate_id as cert_code, c.candidate_name
        FROM verifications v
        LEFT JOIN certificates c ON v.certificate_id = c.id
        ORDER BY v.id DESC LIMIT 5
        """
    ).fetchall()

    conn.close()
    return {
        "total_certificates": total_certs,
        "valid_certificates": valid_certs,
        "revoked_certificates": revoked_certs,
        "total_verifications": total_verifications,
        "recent_certificates": recent_certs,
        "recent_verifications": recent_verifications
    }
