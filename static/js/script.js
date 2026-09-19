// JavaScript Utilities for Tamper-Proof Certificate Verification System

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alert messages after 6 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Copy to clipboard function
    window.copyToClipboard = function(text, elementId) {
        navigator.clipboard.writeText(text).then(function() {
            const btn = document.getElementById(elementId);
            if (btn) {
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
                btn.classList.remove('btn-outline-secondary');
                btn.classList.add('btn-success');
                setTimeout(function() {
                    btn.innerHTML = originalHtml;
                    btn.classList.remove('btn-success');
                    btn.classList.add('btn-outline-secondary');
                }, 2000);
            }
        }).catch(function(err) {
            console.error('Failed to copy: ', err);
        });
    };

    // Table quick search filter if input exists
    const tableSearchInput = document.getElementById('tableSearchInput');
    if (tableSearchInput) {
        tableSearchInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('.filterable-table tbody tr');
            rows.forEach(function(row) {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    }
});
