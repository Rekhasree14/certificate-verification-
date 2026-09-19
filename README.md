# Tamper-Proof Digital Certificate Verification System Using Unique Identity Tokens

A secure, offline-capable digital certificate issuing and verification web application developed using **Python, Flask, SQLite, SHA-256 cryptographic hashing, UUID unique identity tokens, QR codes, and ReportLab PDF generation**.

Designed for colleges, universities, training institutes, and examination boards to issue verifiable digital credentials and detect fraudulent or tampered certificates.

---

## 🌟 Key Features

1. **Secure Admin Authentication:**
   - Werkzeug password hashing (PBKDF2/SHA-256). No plaintext passwords.
   - Session-based access control for administrative endpoints.

2. **Automated Certificate PDF Generation:**
   - Generates high-resolution, landscape A4 certificates using `ReportLab`.
   - Incorporates institution headers, ornate borders, candidate details, issue dates, unique identity tokens, embedded QR codes, and SHA-256 cryptographic fingerprints.

3. **Unique Identity Tokens (UUIDv4):**
   - Cryptographically strong, collision-resistant tokens assigned to every issued credential.

4. **Cryptographic SHA-256 Integrity Verification:**
   - Calculates the SHA-256 digest of certificate documents.
   - Any post-issuance alteration of even 1 single byte alters the digest completely, instantly triggering a `TAMPERED / MISMATCH` detection.

5. **Dynamic QR Code Generation:**
   - Generates QR codes pointing to the verification endpoint `/verify/<token>`.
   - Direct instant verification when scanned on mobile devices or webcam readers.

6. **Tamper Demonstration Feature for College Viva/Presentations:**
   - Built-in simulation tool allowing students to demonstrate before-and-after tampering in real-time.
   - Shows live comparison of **Stored Hash vs Calculated Hash** on the verification screen.

7. **Verification Audit Trail:**
   - Every verification attempt (via Token, QR Code, or File Upload) is logged with timestamps, method, and outcome.

8. **Certificate Revocation & Reissuance:**
   - Revoke compromised or cancelled certificates.
   - Reissue updated credentials with token regeneration and new hash calculation.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+ / Flask
- **Database:** SQLite (Relational DBMS with foreign keys and indexes)
- **Security & Cryptography:** `hashlib` (SHA-256), `werkzeug.security` (Password Hashing), `uuid` (UUID4)
- **Document & QR Generation:** `reportlab` (PDF generation), `qrcode` + `Pillow` (QR codes)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons
- **Testing:** `pytest`

---

## 📁 Project Structure

```text
tamper_proof_verification_system/
│
├── app.py                      # Flask application routes, auth, verification & controller logic
├── database.py                 # SQLite database helper, CRUD, seeding & tampering simulation
├── utils.py                    # Cryptography (SHA-256), UUID tokens, QR generator, ReportLab PDF
├── config.py                   # Configuration settings, file paths, and upload limits
├── schema.sql                  # Database tables (users, certificates, verifications) and indexes
├── requirements.txt            # Python package dependencies
├── README.md                   # Complete documentation and setup guide
│
├── database/
│   └── certificates.db         # SQLite database file (created automatically on startup)
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Main layout with responsive navbar, alerts, footer
│   ├── login.html              # Admin login page with demo credentials
│   ├── register.html           # Administrator registration page
│   ├── dashboard.html          # Admin dashboard with metrics and quick actions
│   ├── upload_certificate.html # Issue certificate form
│   ├── certificates.html       # Repository of all issued certificates with search
│   ├── certificate_details.html# Certificate inspection, live hash check, actions
│   ├── verify.html             # Public verification portal (Token & File Upload)
│   ├── verification_result.html# Comprehensive verification result card
│   ├── verifications.html      # Complete audit log of verification attempts
│   └── error.html              # 404, 500, 403 error handler
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom styling, verification badges, dark code boxes
│   ├── js/
│   │   └── script.js           # Copy-to-clipboard, auto-dismiss alerts, live search
│   └── qrcodes/                # Generated QR code image files (.png)
│
├── uploads/                    # Directory for user-uploaded certificates
├── generated_certificates/     # Directory for auto-generated PDF certificates
└── tests/
    └── test_app.py             # Automated pytest suite
```

---

## 🚀 Installation & Setup (Windows)

### Prerequisites
- Python 3.10, 3.11, or 3.12 installed on your Windows laptop.
- Make sure Python is added to your Windows PATH during installation.

### 1. Open PowerShell or Command Prompt
Navigate to the project folder:
```powershell
cd "c:\Users\srsre\OneDrive\Desktop\tamper proof verification system"
```

### 2. Create and Activate a Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the Application
```powershell
python app.py
```

When started, the terminal will display:
```text
=================================================================
 TAMPER-PROOF DIGITAL CERTIFICATE VERIFICATION SYSTEM
=================================================================
 Server running at: http://127.0.0.1:5000
 Admin Credentials -> Username: admin | Password: admin123
=================================================================
```

Open your web browser and visit:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Default Credentials

An administrator account is automatically created on first launch:

| Field | Value |
| :--- | :--- |
| **Username** | `admin` |
| **Password** | `admin123` |
| **Role** | System Administrator |

*(Passwords are securely hashed using Werkzeug and never stored in plaintext.)*

---

## 🧪 Pre-Seeded Sample Certificates

On first startup, the system automatically initializes the database and creates 3 sample certificates with generated PDFs, QR codes, and SHA-256 hashes:

1. **CERT-1001:** Rahul Kumar — *Python Programming* (National Institute of Technology)
2. **CERT-1002:** Ananya Sharma — *Web Development* (Delhi Technological University)
3. **CERT-1003:** Arjun Reddy — *Data Analytics* (Indian Institute of Science)

---

## 🎓 How to Demonstrate in College Viva / Project Presentation

Follow these steps to give an impressive live demonstration:

### Step 1: Normal Verification (Valid Certificate)
1. Log in to the Admin Dashboard (`admin` / `admin123`).
2. Go to **All Certificates** and open **CERT-1001** (Rahul Kumar).
3. Copy the **Unique Identity Token**.
4. Click **Verify Status Now** (or open the Public Verification Portal at `/verify` in an incognito window).
5. The result will display:
   - **Token Status:** `VALID` (Green)
   - **SHA-256 Hash Status:** `MATCHED` (Green)
   - **Certificate Status:** `VALID` (Green)
   - Stored Hash and Calculated Hash are identical.

### Step 2: Tampering Demonstration (Simulating Document Tampering)
1. Go to **Certificate Details** for **CERT-1002** (Ananya Sharma).
2. Look at the bottom right under **Presentation Demo Tool**.
3. Click the red button: **"Simulate Tampering (Inject Data)"**.
4. The system injects unauthorized byte modifications into the physical PDF certificate file on disk without changing the database hash.
5. Click **Verify Status Now** (or scan its QR code).
6. The system recalculates the SHA-256 hash of the modified document in real-time, compares it with the stored original hash, and displays:
   - **Token Status:** `FOUND`
   - **SHA-256 Hash Status:** `MISMATCH` (Red)
   - **Certificate Status:** `TAMPERED / INVALID` (Red)
   - A side-by-side comparison of the original stored hash vs the altered current hash.

### Step 3: Revocation & Reissuance Demonstration
1. In Certificate Details, click **Revoke Certificate**.
2. Re-verifying will display **CERTIFICATE REVOKED**.
3. Click **Reissue / Regenerate Token**. The system generates a brand new token, a new QR code, recalculates the SHA-256 hash, and restores status to **VALID**.

---

## 🧪 Running Automated Tests

Run the complete automated test suite using `pytest`:

```powershell
pytest -v tests/test_app.py
```

This verifies:
- Database schema and initial seeding
- Admin authentication & password hashing
- Certificate issuance and PDF/QR creation
- Cryptographic SHA-256 calculations
- Legitimate token verification
- Tamper detection (hash mismatch)
- Revocation and reissue workflows

---

## ❓ Troubleshooting

1. **Port 5000 is already in use:**
   - Run on another port:
     ```powershell
     python -c "from app import app, init_db; init_db(); app.run(port=5001)"
     ```
   - Then open `http://127.0.0.1:5001`.

2. **ModuleNotFoundError:**
   - Ensure your virtual environment is active (`venv\Scripts\activate`) and run:
     ```powershell
     pip install -r requirements.txt
     ```

3. **Resetting the Database to Fresh State:**
   - Delete `database/certificates.db` and restart `python app.py`. The system will automatically recreate the tables and re-seed the sample data.
