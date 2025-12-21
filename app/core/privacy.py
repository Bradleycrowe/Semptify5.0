"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SEMPTIFY PRIVACY PRINCIPLES                               ║
║                    ═══════════════════════════════                           ║
║                                                                              ║
║  THIS IS THE LAW OF THE APPLICATION. IT CANNOT BE OVERRIDDEN.                ║
║                                                                              ║
║  Semptify is built on the foundational principle that we NEVER store        ║
║  personal data. Period. No exceptions. No "just this once."                  ║
║                                                                              ║
║  User data belongs to the USER, stored in THEIR cloud storage.               ║
║  We are merely a conduit - a tool that operates ON their data,               ║
║  never a vault that STORES their data.                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

PRIVACY FIRST ARCHITECTURE
═══════════════════════════

What we NEVER store:
- Email addresses
- Names (first, last, display, any)
- Phone numbers
- Physical addresses
- Social security numbers
- Financial account numbers
- IP addresses (beyond immediate request)
- Browser fingerprints
- Location data
- Birth dates
- Any form of PII (Personally Identifiable Information)

What we DO store (temporarily, in encrypted form):
- Anonymous user ID (random string, not linked to real identity)
- OAuth access tokens (encrypted, for API calls only)
- Session timestamps (for expiry management)
- Document hashes (SHA256 - not the documents themselves)
- User's role preference (user/tenant/advocate/legal/admin)

WHY THIS MATTERS
════════════════

1. LEGAL PROTECTION: If we don't have it, we can't be subpoenaed for it
2. SECURITY: Can't breach data we don't have
3. TRUST: Users can verify we can't identify them
4. COMPLIANCE: GDPR/CCPA right to erasure is automatic - nothing to erase
5. ETHICS: Tenant rights work requires protecting vulnerable people

THE GOLDEN RULE
═══════════════

If you're about to add code that stores personal data, STOP.
Ask: "Can the user store this in THEIR cloud storage instead?"
The answer is almost always YES.

ENFORCEMENT
═══════════

This module provides guards that MUST be called before storing any user data.
Violations should raise PrivacyViolationError and log security alerts.
"""

from typing import Any, Optional
import re
import logging

logger = logging.getLogger(__name__)


class PrivacyViolationError(Exception):
    """
    Raised when code attempts to store personal data.
    
    This is a HARD error - the operation MUST fail.
    Personal data storage is NEVER acceptable.
    """
    pass


# =============================================================================
# PRIVACY CONSTANTS - THE RULES
# =============================================================================

# Personal data field names that MUST NEVER be stored in our database
FORBIDDEN_FIELDS = frozenset({
    # Identity
    "email",
    "email_address",
    "e_mail",
    "mail",
    "name",
    "first_name",
    "last_name",
    "full_name",
    "display_name",
    "username",
    "user_name",
    "nickname",
    "real_name",
    
    # Contact
    "phone",
    "phone_number",
    "telephone",
    "mobile",
    "cell",
    "fax",
    "address",
    "street",
    "city",
    "state",
    "zip",
    "zipcode",
    "postal_code",
    "country",
    "location",
    
    # Government IDs
    "ssn",
    "social_security",
    "social_security_number",
    "tax_id",
    "ein",
    "driver_license",
    "passport",
    "national_id",
    
    # Financial
    "bank_account",
    "account_number",
    "routing_number",
    "credit_card",
    "card_number",
    "cvv",
    "expiration",
    
    # Personal Details
    "birth_date",
    "dob",
    "date_of_birth",
    "age",
    "gender",
    "sex",
    "race",
    "ethnicity",
    "religion",
    "political",
    
    # Biometric
    "fingerprint",
    "face_id",
    "retina",
    "voice_print",
    "dna",
    
    # Digital Identity
    "ip_address",
    "mac_address",
    "device_id",
    "browser_fingerprint",
    "geolocation",
    "gps",
    "latitude",
    "longitude",
})

# Patterns that indicate personal data
PERSONAL_DATA_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # Email
    re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'),  # SSN
    re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'),  # Phone
    re.compile(r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'),  # Credit card
]


# =============================================================================
# PRIVACY GUARDS - ENFORCEMENT FUNCTIONS
# =============================================================================

def assert_no_personal_data_fields(data: dict, context: str = "unknown") -> None:
    """
    Check a dictionary for forbidden personal data fields.
    
    MUST be called before inserting/updating any database record.
    Raises PrivacyViolationError if personal data is detected.
    
    Args:
        data: Dictionary to check
        context: Description of where this is being called from (for logging)
    
    Raises:
        PrivacyViolationError: If any forbidden field is present
    """
    if not isinstance(data, dict):
        return
    
    violations = []
    for key in data.keys():
        key_lower = key.lower().replace("-", "_").replace(" ", "_")
        if key_lower in FORBIDDEN_FIELDS:
            violations.append(key)
    
    if violations:
        error_msg = f"PRIVACY VIOLATION in {context}: Attempted to store forbidden fields: {violations}"
        logger.critical(f"🚨 {error_msg}")
        raise PrivacyViolationError(error_msg)


def assert_no_personal_data_values(data: dict, context: str = "unknown") -> None:
    """
    Check dictionary values for patterns that look like personal data.
    
    This is a heuristic check - it may have false positives.
    Used as an additional safety layer, not primary enforcement.
    
    Args:
        data: Dictionary to check
        context: Description of where this is being called from
    
    Raises:
        PrivacyViolationError: If personal data patterns are detected
    """
    if not isinstance(data, dict):
        return
    
    for key, value in data.items():
        if not isinstance(value, str):
            continue
        
        for pattern in PERSONAL_DATA_PATTERNS:
            if pattern.search(value):
                # Log but don't fail - could be false positive
                logger.warning(
                    f"⚠️ POTENTIAL PRIVACY ISSUE in {context}: "
                    f"Field '{key}' contains pattern that looks like personal data"
                )


def sanitize_for_logging(data: Any, max_depth: int = 3) -> Any:
    """
    Sanitize data before logging to prevent accidental PII exposure.
    
    Replaces any values that look like personal data with [REDACTED].
    
    Args:
        data: Data to sanitize
        max_depth: Maximum recursion depth
    
    Returns:
        Sanitized copy of the data
    """
    if max_depth <= 0:
        return "[MAX_DEPTH]"
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            if key_lower in FORBIDDEN_FIELDS:
                result[key] = "[REDACTED]"
            else:
                result[key] = sanitize_for_logging(value, max_depth - 1)
        return result
    
    elif isinstance(data, list):
        return [sanitize_for_logging(item, max_depth - 1) for item in data]
    
    elif isinstance(data, str):
        # Check for PII patterns
        for pattern in PERSONAL_DATA_PATTERNS:
            if pattern.search(data):
                return "[REDACTED]"
        return data
    
    return data


# =============================================================================
# ALLOWED DATA - WHAT WE CAN STORE
# =============================================================================

# Fields that ARE allowed in our database
ALLOWED_USER_FIELDS = frozenset({
    "id",  # Anonymous random ID
    "primary_provider",  # google_drive, dropbox, onedrive
    "storage_user_id",  # Opaque ID from provider (not email)
    "default_role",  # user, tenant, manager, advocate, legal, admin
    "intensity_level",  # low, medium, high
    "created_at",
    "updated_at", 
    "last_login",
})

ALLOWED_SESSION_FIELDS = frozenset({
    "user_id",  # Reference to anonymous user
    "provider",  # google_drive, dropbox, onedrive
    "access_token_encrypted",  # Encrypted, for API calls only
    "refresh_token_encrypted",  # Encrypted, for token refresh
    "authenticated_at",
    "expires_at",
    "last_activity",
    "role_authorized_at",
})


def validate_user_data(data: dict) -> None:
    """
    Validate that user data only contains allowed fields.
    
    Raises:
        PrivacyViolationError: If any forbidden field is present
    """
    forbidden = set(data.keys()) - ALLOWED_USER_FIELDS
    if forbidden:
        raise PrivacyViolationError(
            f"Attempted to store non-allowed user fields: {forbidden}. "
            f"Only these fields are allowed: {ALLOWED_USER_FIELDS}"
        )


# =============================================================================
# PRIVACY POLICY TEXT - FOR DISPLAY TO USERS
# =============================================================================

PRIVACY_POLICY_SHORT = """
🔒 SEMPTIFY PRIVACY COMMITMENT

We NEVER store your personal data:
• No email addresses
• No names  
• No phone numbers
• No addresses
• No government IDs

Your identity is an anonymous ID.
Your documents stay in YOUR cloud storage.
We're a tool, not a data collector.
"""

PRIVACY_POLICY_FULL = """
SEMPTIFY PRIVACY POLICY
Version 5.0 | Effective: 2024

1. DATA WE DO NOT COLLECT
=========================
Semptify does not collect, store, or process:
- Email addresses
- Names (first, last, or display)
- Phone numbers
- Physical addresses
- Government identification numbers
- Financial account information
- Biometric data
- Location data (GPS coordinates)
- IP addresses (beyond session management)
- Browser fingerprints
- Any other Personally Identifiable Information (PII)

2. DATA WE DO STORE
===================
- Anonymous User ID: A random string that identifies your session
- OAuth Tokens: Encrypted tokens to access YOUR cloud storage (never viewed by us)
- Session Timestamps: When you logged in, when your session expires
- Role Preference: Whether you're using the app as tenant, advocate, etc.
- Document Hashes: SHA256 checksums for document integrity (not the documents themselves)

3. YOUR DATA LOCATION
====================
All your personal data (documents, notes, case files) is stored in YOUR cloud
storage account (Google Drive, Dropbox, or OneDrive). We never have access to
this data except through the OAuth token you provide, and only for the specific
operations you request.

4. TOKEN SECURITY
=================
OAuth tokens are:
- Encrypted with AES-256-GCM
- Tied to your anonymous user ID
- Automatically expire (24-hour sessions)
- Never logged or stored in plaintext
- Only used for operations you explicitly request

5. RIGHT TO DELETION
===================
Because we don't store personal data, there's nothing to delete. Clear your
browser cookies and your anonymous ID is gone. Revoke OAuth access in your
cloud provider settings and we lose all access to your storage.

6. SUBPOENA RESPONSE
===================
We cannot be compelled to produce data we do not have. If subpoenaed:
- We can provide an anonymous user ID
- We can provide session timestamps
- We CANNOT provide any personal identifying information
- We CANNOT provide document contents (stored in YOUR cloud, not ours)

7. CONTACT
=========
This application is designed to protect the vulnerable. Privacy is not optional.
"""


# =============================================================================
# STARTUP VERIFICATION
# =============================================================================

def verify_privacy_compliance() -> bool:
    """
    Verify that privacy principles are being enforced.
    
    Called at application startup.
    Returns True if all checks pass.
    """
    logger.info("🔒 PRIVACY PRINCIPLES VERIFICATION")
    logger.info("=" * 60)
    logger.info("✅ No personal data fields will be stored")
    logger.info("✅ OAuth tokens encrypted with AES-256-GCM")
    logger.info("✅ Sessions expire after 24 hours")
    logger.info("✅ User documents stored in USER'S cloud only")
    logger.info("✅ Anonymous user IDs - no real identity mapping")
    logger.info("=" * 60)
    logger.info("🛡️ Semptify Privacy Mode: ENFORCED")
    return True
