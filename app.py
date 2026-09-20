import os
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

from config import Config
from database import (
    init_db,
    get_user_by_username,
    get_user_by_id,
    create_user,
    create_certificate,
    get_certificate_by_id,
    get_certificate_by_token,
    get_certificate_by_cert_id,
    get_certificate_by_hash,
    get_all_certificates,
    update_certificate_status,
    reissue_certificate,
    simulate_tampering,
    log_verification,
    get_verification_history,
    get_dashboard_stats
)
from utils import (
    generate_unique_token,
    generate_qr_code,
    generate_certificate_pdf,
    calculate_file_sha256,
    calculate_data_sha256
)

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload and output directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.CERTIFICATES_FOLDER, exist_ok=True)
os.makedirs(Config.QRCODE_FOLDER, exist_ok=True)

# Helper function to check allowed file extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to inject user info into templates
@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
    return {'current_user': user, 'now': datetime.now()}

# -----------------
# Auth Routes
# -----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return render_template('login.html')

        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not name or not email or not username or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        user_id = create_user(name, email, username, password)
        if user_id:
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username or Email already registered. Please choose another.', 'danger')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been securely logged out.', 'info')
    return redirect(url_for('login'))

# -----------------
# Core Application Routes
# -----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    stats = get_dashboard_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/certificates')
@login_required
def certificates():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    cert_list = get_all_certificates(search_query=search_query or None, status_filter=status_filter or None)
    return render_template('certificates.html', certificates=cert_list, search_query=search_query, status_filter=status_filter)

@app.route('/certificates/issue', methods=['GET', 'POST'])
@login_required
def issue_certificate():
    if request.method == 'POST':
        certificate_id = request.form.get('certificate_id', '').strip().upper()
        candidate_name = request.form.get('candidate_name', '').strip()
        course_name = request.form.get('course_name', '').strip()
        institution_name = request.form.get('institution_name', '').strip()
        issue_date = request.form.get('issue_date', '').strip()
        certificate_type = request.form.get('certificate_type', 'Course Completion').strip()

        # Input validation
        if not certificate_id or not candidate_name or not course_name or not institution_name or not issue_date:
            flash('All certificate fields are required.', 'danger')
            return render_template('upload_certificate.html')

        # Check for duplicate certificate ID
        if get_certificate_by_cert_id(certificate_id):
            flash(f'Certificate ID "{certificate_id}" already exists. Please use a unique ID.', 'danger')
            return render_template('upload_certificate.html')

        # Generate unique identity token
        token = generate_unique_token()

        # Generate QR Code
        qr_filename = f"{token}.png"
        qr_path = os.path.join(Config.QRCODE_FOLDER, qr_filename)
        base_url = request.host_url
        generate_qr_code(token, base_url, qr_path)

        # Handle file: either uploaded file OR auto-generated ReportLab PDF
        uploaded_file = request.files.get('certificate_file')
        if uploaded_file and uploaded_file.filename != '':
            if not allowed_file(uploaded_file.filename):
                flash('Invalid file type! Allowed formats: PDF, PNG, JPG, JPEG.', 'danger')
                return render_template('upload_certificate.html')

            ext = uploaded_file.filename.rsplit('.', 1)[1].lower()
            safe_name = f"{certificate_id}_{token[:8]}.{ext}"
            saved_file_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
            uploaded_file.save(saved_file_path)

            # Calculate SHA-256 of uploaded file
            sha256_hash = calculate_file_sha256(saved_file_path)
            file_path = saved_file_path
        else:
            # Auto-generate professional PDF certificate
            pdf_filename = f"{certificate_id}.pdf"
            pdf_path = os.path.join(Config.CERTIFICATES_FOLDER, pdf_filename)

            cert_data = {
                "certificate_id": certificate_id,
                "candidate_name": candidate_name,
                "course_name": course_name,
                "institution_name": institution_name,
                "issue_date": issue_date,
                "certificate_type": certificate_type,
                "token": token,
                "sha256_hash": ""
            }

            # Generate first pass to calculate hash
            generate_certificate_pdf(cert_data, qr_path, pdf_path)
            first_hash = calculate_file_sha256(pdf_path)

            # Re-generate PDF with actual SHA-256 fingerprint displayed
            cert_data["sha256_hash"] = first_hash
            generate_certificate_pdf(cert_data, qr_path, pdf_path)
            sha256_hash = calculate_file_sha256(pdf_path)
            file_path = pdf_path

        # Save to Database
        try:
            cert_id = create_certificate(
                certificate_id=certificate_id,
                candidate_name=candidate_name,
                course_name=course_name,
                institution_name=institution_name,
                issue_date=issue_date,
                certificate_type=certificate_type,
                file_path=file_path,
                sha256_hash=sha256_hash,
                token=token,
                qr_code_path=os.path.join('static', 'qrcodes', qr_filename),
                status='VALID'
            )
            flash(f'Certificate {certificate_id} successfully issued with Unique Token!', 'success')
            return redirect(url_for('certificate_details', cert_id=cert_id))
        except Exception as e:
            flash(f'Database error occurred: {str(e)}', 'danger')
            return render_template('upload_certificate.html')

    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('upload_certificate.html', today_date=today_date)

@app.route('/certificates/<int:cert_id>')
@login_required
def certificate_details(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert:
        abort(404)

    # Current calculated file hash on disk to show live integrity status
    current_hash = None
    if cert['file_path'] and os.path.exists(cert['file_path']):
        current_hash = calculate_file_sha256(cert['file_path'])

    return render_template('certificate_details.html', cert=cert, current_hash=current_hash)

@app.route('/certificates/<int:cert_id>/download')
def download_certificate(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert or not cert['file_path'] or not os.path.exists(cert['file_path']):
        flash('Certificate file not found.', 'danger')
        return redirect(url_for('certificates'))

    filename = os.path.basename(cert['file_path'])
    return send_file(cert['file_path'], as_attachment=True, download_name=filename)

@app.route('/certificates/<int:cert_id>/revoke', methods=['POST'])
@login_required
def revoke_certificate(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert:
        abort(404)

    update_certificate_status(cert_id, 'REVOKED')
    flash(f'Certificate {cert["certificate_id"]} has been revoked.', 'warning')
    return redirect(url_for('certificate_details', cert_id=cert_id))

@app.route('/certificates/<int:cert_id>/reissue', methods=['POST'])
@login_required
def reissue_cert(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert:
        abort(404)

    # Generate new unique identity token
    new_token = generate_unique_token()

    # Generate new QR code
    qr_filename = f"{new_token}.png"
    new_qr_path = os.path.join(Config.QRCODE_FOLDER, qr_filename)
    generate_qr_code(new_token, request.host_url, new_qr_path)

    # Regenerate PDF with new token
    new_issue_date = datetime.now().strftime('%Y-%m-%d')
    pdf_filename = f"{cert['certificate_id']}_reissued.pdf"
    new_pdf_path = os.path.join(Config.CERTIFICATES_FOLDER, pdf_filename)

    cert_data = {
        "certificate_id": cert['certificate_id'],
        "candidate_name": cert['candidate_name'],
        "course_name": cert['course_name'],
        "institution_name": cert['institution_name'],
        "issue_date": new_issue_date,
        "certificate_type": cert['certificate_type'],
        "token": new_token,
        "sha256_hash": ""
    }
    generate_certificate_pdf(cert_data, new_qr_path, new_pdf_path)
    first_hash = calculate_file_sha256(new_pdf_path)

    cert_data["sha256_hash"] = first_hash
    generate_certificate_pdf(cert_data, new_qr_path, new_pdf_path)
    new_sha256 = calculate_file_sha256(new_pdf_path)

    # Update database record
    reissue_certificate(
        cert_id=cert_id,
        new_token=new_token,
        new_sha256=new_sha256,
        new_file_path=new_pdf_path,
        new_qr_path=os.path.join('static', 'qrcodes', qr_filename),
        new_issue_date=new_issue_date
    )

    flash(f'Certificate {cert["certificate_id"]} successfully reissued with new Token and Hash!', 'success')
    return redirect(url_for('certificate_details', cert_id=cert_id))

@app.route('/certificates/<int:cert_id>/tamper-demo', methods=['POST'])
@login_required
def tamper_demo(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert:
        abort(404)

    success = simulate_tampering(cert_id)
    if success:
        flash(
            f'DEMO ALERT: Certificate {cert["certificate_id"]} file has been intentionally modified on disk! '
            'The stored hash in the database is unchanged. Verify this certificate now to see tamper detection in action!',
            'danger'
        )
    else:
        flash('Could not simulate tampering: Certificate file missing.', 'danger')

    return redirect(url_for('certificate_details', cert_id=cert_id))

# -----------------
# Verification Routes
# -----------------

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        # Check if verifying by uploaded file
        uploaded_file = request.files.get('verify_file')
        if uploaded_file and uploaded_file.filename != '':
            if not allowed_file(uploaded_file.filename):
                flash('Invalid file format. Please upload a PDF or image.', 'danger')
                return render_template('verify.html')

            temp_filename = f"temp_verify_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(uploaded_file.filename)}"
            temp_path = os.path.join(Config.UPLOAD_FOLDER, temp_filename)
            uploaded_file.save(temp_path)

            uploaded_hash = calculate_file_sha256(temp_path)
            # Remove temp file after hash calculation
            try:
                os.remove(temp_path)
            except OSError:
                pass

            # Check if there is an entered token alongside the file
            token_entered = request.form.get('token', '').strip()
            cert = None
            if token_entered:
                cert = get_certificate_by_token(token_entered)
            elif uploaded_hash:
                cert = get_certificate_by_hash(uploaded_hash)

            if not cert:
                log_verification(
                    certificate_id=None,
                    token_entered=token_entered or 'FILE_UPLOAD',
                    verification_result='INVALID',
                    verification_method='FILE_UPLOAD'
                )
                return render_template(
                    'verification_result.html',
                    status='INVALID',
                    reason='No certificate in our database matches the uploaded file hash or token.',
                    token_status='NOT_FOUND',
                    hash_status='NO_MATCH',
                    calculated_hash=uploaded_hash,
                    stored_hash='N/A',
                    cert=None
                )

            # Certificate record exists, now verify hash
            stored_hash = cert['sha256_hash']
            is_hash_match = (uploaded_hash == stored_hash)

            if cert['status'] == 'REVOKED':
                result_status = 'REVOKED'
                reason = 'This certificate has been revoked by the issuing authority.'
            elif is_hash_match:
                result_status = 'VALID'
                reason = 'Certificate is authentic and has not been modified.'
            else:
                result_status = 'TAMPERED'
                reason = 'Uploaded file content has been altered! The computed SHA-256 hash does not match the original stored hash.'

            log_verification(
                certificate_id=cert['id'],
                token_entered=cert['token'],
                verification_result=result_status,
                verification_method='FILE_UPLOAD'
            )

            return render_template(
                'verification_result.html',
                status=result_status,
                reason=reason,
                token_status='VALID',
                hash_status='MATCHED' if is_hash_match else 'MISMATCH',
                calculated_hash=uploaded_hash,
                stored_hash=stored_hash,
                cert=cert
            )

        # Verification by Token
        token = request.form.get('token', '').strip()
        if not token:
            flash('Please enter a Unique Identity Token or upload a certificate file.', 'warning')
            return render_template('verify.html')

        return redirect(url_for('verify_token', token=token))

    return render_template('verify.html')

@app.route('/verify/<token>')
def verify_token(token):
    token = token.strip()
    is_qr = request.args.get('qr', 'false').lower() == 'true'
    method = 'QR' if is_qr else 'TOKEN'

    cert = get_certificate_by_token(token)

    if not cert:
        # Certificate not found
        log_verification(
            certificate_id=None,
            token_entered=token,
            verification_result='INVALID',
            verification_method=method
        )
        return render_template(
            'verification_result.html',
            status='INVALID',
            reason='The provided identity token was not found in our database records.',
            token_status='NOT_FOUND',
            hash_status='UNKNOWN',
            calculated_hash='N/A',
            stored_hash='N/A',
            cert=None
        )

    stored_hash = cert['sha256_hash']
    current_hash = None

    # Calculate current file hash from disk
    if cert['file_path'] and os.path.exists(cert['file_path']):
        current_hash = calculate_file_sha256(cert['file_path'])
    else:
        # Fallback to canonical data hash if file is missing
        current_hash = calculate_data_sha256(dict(cert))

    is_hash_match = (current_hash == stored_hash)

    # Determine verification status
    if cert['status'] == 'REVOKED':
        result_status = 'REVOKED'
        reason = 'This certificate was revoked by the issuing authority.'
    elif is_hash_match:
        result_status = 'VALID'
        reason = 'Certificate is authentic and has not been modified.'
    else:
        result_status = 'TAMPERED'
        reason = 'Certificate tampering detected! The current file/data SHA-256 hash does not match the original issued hash.'

    log_verification(
        certificate_id=cert['id'],
        token_entered=token,
        verification_result=result_status,
        verification_method=method
    )

    return render_template(
        'verification_result.html',
        status=result_status,
        reason=reason,
        token_status='VALID' if cert['status'] != 'REVOKED' else 'REVOKED',
        hash_status='MATCHED' if is_hash_match else 'MISMATCH',
        calculated_hash=current_hash,
        stored_hash=stored_hash,
        cert=cert
    )

@app.route('/verifications')
@login_required
def verifications():
    history = get_verification_history(limit=150)
    return render_template('verifications.html', history=history)

# -----------------
# Error Handlers
# -----------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', code=404, message='The requested page or certificate was not found.'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', code=500, message='An internal server error occurred. Please try again.'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error.html', code=403, message='Access forbidden. You do not have permission to view this resource.'), 403

if __name__ == '__main__':
    # Initialize database on startup
    init_db(seed_sample_data=True)
    print("=" * 65)
    print(" TAMPER-PROOF DIGITAL CERTIFICATE VERIFICATION SYSTEM")
    print("=" * 65)
    print(" Server running at: http://127.0.0.1:5000")
    print(" Admin Credentials -> Username: admin | Password: admin123")
    print("=" * 65)
    app.run(debug=True, host='127.0.0.1', port=5000)
