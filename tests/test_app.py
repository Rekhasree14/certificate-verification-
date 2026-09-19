import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import tempfile
import shutil
from werkzeug.security import check_password_hash

from app import app
from config import Config
import database
from database import (
    init_db,
    get_user_by_username,
    get_certificate_by_cert_id,
    get_certificate_by_token,
    update_certificate_status,
    simulate_tampering,
    get_verification_history
)
from utils import calculate_file_sha256

@pytest.fixture
def client():
    # Setup test database and folders
    test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(test_db_fd)

    test_upload_dir = tempfile.mkdtemp()
    test_cert_dir = tempfile.mkdtemp()
    test_qr_dir = tempfile.mkdtemp()

    original_db = Config.DATABASE_PATH
    original_uploads = Config.UPLOAD_FOLDER
    original_certs = Config.CERTIFICATES_FOLDER
    original_qr = Config.QRCODE_FOLDER

    Config.DATABASE_PATH = test_db_path
    Config.UPLOAD_FOLDER = test_upload_dir
    Config.CERTIFICATES_FOLDER = test_cert_dir
    Config.QRCODE_FOLDER = test_qr_dir

    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'

    # Initialize DB with sample data
    init_db(seed_sample_data=True)

    with app.test_client() as client:
        yield client

    # Cleanup
    Config.DATABASE_PATH = original_db
    Config.UPLOAD_FOLDER = original_uploads
    Config.CERTIFICATES_FOLDER = original_certs
    Config.QRCODE_FOLDER = original_qr

    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    shutil.rmtree(test_upload_dir, ignore_errors=True)
    shutil.rmtree(test_cert_dir, ignore_errors=True)
    shutil.rmtree(test_qr_dir, ignore_errors=True)

def test_database_initialization(client):
    """Test that default admin and 3 sample certificates are properly seeded."""
    admin = get_user_by_username('admin')
    assert admin is not None
    assert check_password_hash(admin['password_hash'], 'admin123')

    cert1 = get_certificate_by_cert_id('CERT-1001')
    cert2 = get_certificate_by_cert_id('CERT-1002')
    cert3 = get_certificate_by_cert_id('CERT-1003')

    assert cert1 is not None
    assert cert1['candidate_name'] == 'Rahul Kumar'
    assert len(cert1['token']) > 20
    assert len(cert1['sha256_hash']) == 64

    assert cert2 is not None
    assert cert2['candidate_name'] == 'Ananya Sharma'

    assert cert3 is not None
    assert cert3['candidate_name'] == 'Arjun Reddy'

def test_admin_login(client):
    """Test valid and invalid login flows."""
    # Invalid login
    res_bad = client.post('/login', data={'username': 'admin', 'password': 'wrongpassword'})
    assert b'Invalid username or password' in res_bad.data

    # Valid login
    res_good = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert res_good.status_code == 200
    assert b'Administrative Dashboard' in res_good.data

def test_certificate_issuance(client):
    """Test issuing a new certificate with automatic token, QR, and PDF generation."""
    # Log in first
    client.post('/login', data={'username': 'admin', 'password': 'admin123'})

    res = client.post('/certificates/issue', data={
        'certificate_id': 'CERT-TEST-999',
        'candidate_name': 'Test Student',
        'course_name': 'Software Engineering',
        'institution_name': 'Test Tech University',
        'issue_date': '2026-09-20',
        'certificate_type': 'Course Completion'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'successfully issued' in res.data

    cert = get_certificate_by_cert_id('CERT-TEST-999')
    assert cert is not None
    assert cert['candidate_name'] == 'Test Student'
    assert os.path.exists(cert['file_path'])
    assert len(cert['sha256_hash']) == 64

def test_verification_valid_certificate(client):
    """Test verifying a valid certificate using its unique identity token."""
    cert = get_certificate_by_cert_id('CERT-1001')
    assert cert is not None

    res = client.get(f'/verify/{cert["token"]}')
    assert res.status_code == 200
    assert b'CERTIFICATE VERIFIED' in res.data
    assert b'MATCHED' in res.data
    assert b'Rahul Kumar' in res.data

    # Check verification logged
    history = get_verification_history(limit=5)
    assert len(history) > 0
    assert history[0]['verification_result'] == 'VALID'

def test_verification_invalid_token(client):
    """Test verification with a fake/non-existent token."""
    fake_token = '00000000-0000-0000-0000-000000000000'
    res = client.get(f'/verify/{fake_token}')
    assert res.status_code == 200
    assert b'CERTIFICATE NOT FOUND' in res.data

def test_tampering_detection(client):
    """Test that modifying the certificate file causes SHA-256 mismatch and TAMPERED status."""
    cert = get_certificate_by_cert_id('CERT-1002')
    assert cert is not None

    # Before tampering: Should be VALID
    res_before = client.get(f'/verify/{cert["token"]}')
    assert b'CERTIFICATE VERIFIED' in res_before.data

    # Simulate tampering on the certificate file on disk
    success = simulate_tampering(cert['id'])
    assert success is True

    # After tampering: Must detect MISMATCH and TAMPERED
    res_after = client.get(f'/verify/{cert["token"]}')
    assert b'CERTIFICATE TAMPERED' in res_after.data
    assert b'MISMATCH' in res_after.data

def test_revocation_workflow(client):
    """Test revoking a certificate and confirming verification reflects revocation."""
    cert = get_certificate_by_cert_id('CERT-1003')
    assert cert is not None

    # Admin revokes
    update_certificate_status(cert['id'], 'REVOKED')

    res = client.get(f'/verify/{cert["token"]}')
    assert res.status_code == 200
    assert b'CERTIFICATE REVOKED' in res.data
