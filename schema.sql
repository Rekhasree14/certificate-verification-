-- Database Schema for Tamper-Proof Digital Certificate Verification System

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Certificates Table
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id TEXT UNIQUE NOT NULL,
    candidate_name TEXT NOT NULL,
    course_name TEXT NOT NULL,
    institution_name TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    certificate_type TEXT NOT NULL DEFAULT 'Course Completion',
    file_path TEXT,
    sha256_hash TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    qr_code_path TEXT,
    status TEXT NOT NULL DEFAULT 'VALID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verifications Log Table
CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_id INTEGER,
    token_entered TEXT NOT NULL,
    verification_result TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (certificate_id) REFERENCES certificates (id) ON DELETE SET NULL
);

-- Indexes for optimal lookup speed
CREATE INDEX IF NOT EXISTS idx_certificates_token ON certificates(token);
CREATE INDEX IF NOT EXISTS idx_certificates_cert_id ON certificates(certificate_id);
CREATE INDEX IF NOT EXISTS idx_verifications_cert_id ON verifications(certificate_id);
CREATE INDEX IF NOT EXISTS idx_verifications_verified_at ON verifications(verified_at DESC);
