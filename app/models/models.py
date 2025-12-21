"""
Semptify Database Models
SQLAlchemy ORM models for all entities.

All datetime columns use DateTime(timezone=True) for proper UTC handling.
Use utc_now() from app.core.utc for all timestamp defaults.

╔══════════════════════════════════════════════════════════════════════════════╗
║                         PRIVACY FIRST DESIGN                                 ║
║                                                                              ║
║  SEMPTIFY NEVER STORES PERSONAL DATA. This includes:                         ║
║  - No email addresses                                                        ║
║  - No names (first, last, display)                                          ║
║  - No phone numbers, addresses, or any PII                                  ║
║                                                                              ║
║  User identity = anonymous random ID                                         ║
║  User data = stored in THEIR cloud storage                                   ║
║                                                                              ║
║  See app/core/privacy.py for enforcement rules.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utc import utc_now


# Type alias for timezone-aware DateTime columns
DateTimeTZ = DateTime(timezone=True)


# =============================================================================
# Enums for Timeline & Annotation System
# =============================================================================

class EventStatus(str, Enum):
    """
    Status of a timeline event in the case lifecycle.
    Used to track event progression and state.
    """
    # Process states
    START = "start"           # Event that initiates a process
    CONTINUED = "continued"   # Event continues/extends a process
    FINISH = "finish"         # Event concludes a process
    
    # Action states
    REPORTED = "reported"     # Issue/violation reported
    INVITED = "invited"       # Meeting/hearing scheduled (invitation)
    ATTENDED = "attended"     # Event was attended
    MISSED = "missed"         # Event was missed/no-show
    
    # Document states
    SERVED = "served"         # Document was served/delivered
    RECEIVED = "received"     # Document was received
    FILED = "filed"           # Document filed with court/agency
    RESPONDED = "responded"   # Response submitted
    
    # Outcome states
    PENDING = "pending"       # Awaiting action/decision
    RESOLVED = "resolved"     # Issue resolved
    ESCALATED = "escalated"   # Issue escalated to higher level
    USED = "used"             # Evidence used in proceeding
    
    # Default
    UNKNOWN = "unknown"


class ExtractionCode(str, Enum):
    """
    Extraction category codes for document annotations.
    Each code maps to a specific highlighter color.
    """
    DT = "DT"   # Dates & Deadlines (Amber)
    PT = "PT"   # Parties & Names (Blue)
    AMT = "$"   # Money & Amounts (Emerald)
    AD = "AD"   # Addresses & Locations (Violet)
    LG = "LG"   # Legal Terms & Citations (Red)
    NT = "NT"   # Notes & Footnotes (Orange)
    FM = "FM"   # Form Field Data (Pink)
    EV = "EV"   # Events & Actions (Cyan)
    DL = "DL"   # Critical Deadline (Deep Red)
    WS = "WS"   # Witness/Testimony (Lime)
    VL = "VL"   # Violation/Issue (Rose)
    ED = "ED"   # Evidence Markers (Teal)
    QT = "QT"   # Quoted Text (Purple)
    TL = "TL"   # Timeline Key Dates (Sky Blue)


class DetectionMethod(str, Enum):
    """How an annotation was detected/created."""
    PATTERN = "pattern"   # Regex pattern matching
    AI = "ai"             # AI/ML extraction
    CONTEXT = "context"   # Contextual analysis
    KEYWORD = "keyword"   # Keyword matching
    MANUAL = "manual"     # User manually created


# =============================================================================
# User Model (Storage-Based Auth)
# =============================================================================

class User(Base):
    """
    User account - storage-based authentication.
    
    PRIVACY: NO PERSONAL DATA IS STORED.
    - No email addresses
    - No names (display name, real name, etc.)
    - No phone numbers
    - No addresses
    
    Identity comes from cloud storage (Google Drive, Dropbox, OneDrive).
    The user_id is a random anonymous ID encoding provider + role.
    Example: GU7x9kM2pQ = Google + User + random unique string
    
    User's actual data (documents, case files) lives in THEIR cloud storage.
    We only store session management info.
    """
    __tablename__ = "users"

    # Primary key: anonymous random ID (10 chars: provider + role + 8 random)
    # Example: GU7x9kM2pQ (G=Google, U=User, rest=random)
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    
    # Storage provider info (to know where to redirect for re-auth)
    primary_provider: Mapped[str] = mapped_column(String(20), index=True)  # google_drive, dropbox, onedrive
    storage_user_id: Mapped[str] = mapped_column(String(100))  # Opaque ID from provider (NOT email)
    
    # Role preference (restored on return)
    default_role: Mapped[str] = mapped_column(String(20), default="user")  # user, manager, advocate, legal, admin
    
    # ⚠️ NO PERSONAL DATA FIELDS ⚠️
    # email - REMOVED (privacy)
    # display_name - REMOVED (privacy)
    # avatar_url - REMOVED (privacy)

    # Intensity Engine (tenant-specific feature)
    intensity_level: Mapped[str] = mapped_column(String(10), default="low")  # low, medium, high
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rent_payments: Mapped[list["RentPayment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    linked_providers: Mapped[list["LinkedProvider"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# =============================================================================
# Linked Storage Providers (Multi-Provider Support)
# =============================================================================

class LinkedProvider(Base):
    """
    Additional storage providers linked to a user account.
    
    PRIVACY: NO PERSONAL DATA IS STORED.
    - No email addresses
    - No display names
    
    A user authenticates with one provider initially (becomes primary).
    They can later link additional providers for backup/sync.
    """
    __tablename__ = "linked_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(24), ForeignKey("users.id"), index=True)
    
    # Provider info
    provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive
    storage_user_id: Mapped[str] = mapped_column(String(100))  # Opaque ID from provider (NOT email)
    
    # ⚠️ NO PERSONAL DATA FIELDS ⚠️
    # email - REMOVED (privacy)
    # display_name - REMOVED (privacy)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    linked_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="linked_providers")
# =============================================================================
# Document Vault
# =============================================================================

class Document(Base):
    """
    Document stored in the vault with certification.
    
    Privilege Levels:
    - is_privileged=False: Normal tenant document (visible to tenant, advocate, attorney)
    - is_privileged=True: Attorney-client privileged (visible ONLY to creating attorney + client)
    - is_work_product=True: Attorney work product (protected from discovery)
    """
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # File info
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    
    # Certification
    sha256_hash: Mapped[str] = mapped_column(String(64))
    certificate_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Metadata
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # lease, notice, photo, etc.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # comma-separated
    
    # ==========================================================================
    # ATTORNEY-CLIENT PRIVILEGE FLAGS
    # ==========================================================================
    is_privileged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    """Attorney-client privileged document. Only visible to creating attorney and the client."""
    
    is_work_product: Mapped[bool] = mapped_column(Boolean, default=False)
    """Attorney work product. Protected from discovery even in litigation."""
    
    created_by_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """Role of user who created this document (user, advocate, legal, admin)."""
    
    attorney_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    """If privileged, the attorney who created it (for privilege verification)."""
    
    privilege_waived: Mapped[bool] = mapped_column(Boolean, default=False)
    """If True, client has explicitly waived privilege on this document."""
    
    # ==========================================================================
    # CORRESPONDENCE METADATA - Track who sent what to whom
    # ==========================================================================
    is_correspondence: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    """True if this document is correspondence (email, letter, notice, etc.)"""
    
    correspondence_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    """Type: email, letter, certified_mail, text, legal_notice, court_filing"""
    
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    """Who sent this document"""
    
    sender_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """Sender type: me, landlord, attorney, court, agency"""
    
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    """Who received this document"""
    
    recipient_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """Recipient type: me, landlord, attorney, court, agency"""
    
    date_sent: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    """When the document/communication was sent"""
    
    date_received: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    """When the document/communication was received"""
    
    delivery_method: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    """How delivered: email, usps, certified, hand_delivered, text"""
    
    correspondence_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    """Link to full Correspondence record for detailed tracking"""
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")


# =============================================================================
# Timeline Events
# =============================================================================

class TimelineEvent(Base):
    """
    Events in the tenant's timeline.
    
    Enhanced with:
    - Event status tracking (start, continued, finish, etc.)
    - Event chaining (parent_event_id for linked sequences)
    - Annotation linking (footnote_number, highlight_color)
    - Urgency levels for prioritization
    """
    __tablename__ = "timeline_events"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(50))  # notice, payment, maintenance, communication, court
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # =========================================================================
    # ENHANCED: Event Status & Lifecycle
    # =========================================================================
    event_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    """EventStatus value: start, continued, finish, reported, invited, attended, etc."""
    
    # When it happened (enhanced with end date for ranges)
    event_date: Mapped[datetime] = mapped_column(DateTimeTZ, index=True)
    event_date_end: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    """For events spanning multiple days (e.g., notice period: served -> deadline)"""
    
    # =========================================================================
    # ENHANCED: Event Chaining (Link Related Events)
    # =========================================================================
    parent_event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    """Links to parent event for chains like: Notice Served → Response Due → Hearing"""
    
    sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    """Order in the chain (0=root, 1=first child, etc.)"""
    
    # =========================================================================
    # ENHANCED: Document & Annotation Linking
    # =========================================================================
    # Linked document (optional) - stores doc ID from file-based pipeline, not FK
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    source_extraction_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """Links to annotation marker, e.g., 'DT-3' for third date highlight"""
    
    footnote_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Global footnote number for citation purposes"""
    
    highlight_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """Annotation color category: date, party, amount, legal, etc."""
    
    # =========================================================================
    # ENHANCED: Urgency & Deadline Flags
    # =========================================================================
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    """Priority level: critical, high, normal, low"""
    
    is_deadline: Mapped[bool] = mapped_column(Boolean, default=False)
    """True if this event represents a deadline that must be met"""
    
    is_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    """Importance for court"""
    
    # =========================================================================
    # ENHANCED: Extraction Metadata
    # =========================================================================
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    """Confidence score from AI/pattern extraction (0.0 to 1.0)"""
    
    detection_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    """How extracted: pattern, ai, context, keyword, manual"""
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="timeline_events")


# =============================================================================
# Document Annotations (Footnote & Highlight Index)
# =============================================================================

class DocumentAnnotation(Base):
    """
    Individual annotations/highlights with footnote numbers.
    
    Links highlighted text in documents to timeline events,
    providing a comprehensive index of all extracted data.
    
    Numbering:
    - footnote_number: Global sequential (1, 2, 3...) for citations
    - category_number: Per-category (DT-1, DT-2, PT-1...) for quick reference
    """
    __tablename__ = "document_annotations"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # =========================================================================
    # Footnote Numbering System
    # =========================================================================
    footnote_number: Mapped[int] = mapped_column(Integer, index=True)
    """Global sequential number: 1, 2, 3... (unique per document)"""
    
    category_number: Mapped[int] = mapped_column(Integer)
    """Per-category number: the '3' in 'DT-3' (dates), or '1' in 'PT-1' (parties)"""
    
    extraction_code: Mapped[str] = mapped_column(String(10))
    """Category code: DT, PT, $, AD, LG, NT, FM, EV, DL, WS, VL, ED, QT, TL"""
    
    # =========================================================================
    # Content
    # =========================================================================
    highlight_text: Mapped[str] = mapped_column(Text)
    """The actual text that was highlighted/selected"""
    
    context_before: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Text immediately before the highlight (for context)"""
    
    context_after: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Text immediately after the highlight (for context)"""
    
    annotation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """User's note about this annotation"""
    
    # =========================================================================
    # Position (for overlay rendering)
    # =========================================================================
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    """X position as percentage of page width (0.0 to 1.0)"""
    
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    """Y position as percentage of page height (0.0 to 1.0)"""
    
    position_width: Mapped[float] = mapped_column(Float, default=0.0)
    """Width as percentage of page width"""
    
    position_height: Mapped[float] = mapped_column(Float, default=0.0)
    """Height as percentage of page height"""
    
    # =========================================================================
    # Timeline Link
    # =========================================================================
    linked_event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    """FK to timeline_events - links this annotation to a timeline event"""
    
    # =========================================================================
    # Extraction Metadata
    # =========================================================================
    detection_method: Mapped[str] = mapped_column(String(20), default="manual")
    """How detected: pattern, ai, context, keyword, manual"""
    
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    """Confidence score from extraction (0.0 to 1.0)"""
    
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    """User has verified this annotation is correct"""
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Rent Ledger
# =============================================================================

class RentPayment(Base):
    """
    Rent payment record for the ledger.
    """
    __tablename__ = "rent_payments"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Payment details
    amount: Mapped[int] = mapped_column(Integer)  # Store in cents to avoid float issues
    payment_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    due_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    
    # Status
    status: Mapped[str] = mapped_column(String(20))  # paid, late, partial, missed
    
    # Method and confirmation
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confirmation_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Linked receipt document (stores doc ID from file-based pipeline, not FK)
    receipt_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="rent_payments")


# =============================================================================
# Calendar / Deadlines
# =============================================================================

class CalendarEvent(Base):
    """
    Calendar event or deadline.
    """
    __tablename__ = "calendar_events"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Event details
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing
    start_datetime: Mapped[datetime] = mapped_column(DateTimeTZ)
    end_datetime: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Type and urgency
    event_type: Mapped[str] = mapped_column(String(50))  # deadline, hearing, reminder, appointment
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)  # Affects intensity engine
    
    # Reminders (days before)
    reminder_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Complaints
# =============================================================================

class Complaint(Base):
    """
    Formal complaint being filed with regulatory agencies.
    Extended for Complaint Wizard with full draft support.
    """
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # Agency info
    agency_id: Mapped[str] = mapped_column(String(50), index=True)  # e.g., mn_ag_consumer, hud_fair_housing

    # Type and status
    complaint_type: Mapped[str] = mapped_column(String(50))  # habitability, discrimination, retaliation, etc.
    status: Mapped[str] = mapped_column(String(20))  # draft, ready, filed, acknowledged, investigating, resolved, closed

    # Subject and description
    subject: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(String(500), default="")
    detailed_description: Mapped[Text] = mapped_column(Text, default="")

    # Incident info
    incident_dates: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of dates
    damages_claimed: Mapped[Optional[float]] = mapped_column(nullable=True)
    relief_sought: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Target/Respondent info
    target_type: Mapped[str] = mapped_column(String(50), default="landlord")  # landlord, property_manager, hoa
    target_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Evidence
    attached_document_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of doc IDs
    timeline_included: Mapped[bool] = mapped_column(Boolean, default=False)

    # Filing info
    filed_with: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Agency name
    filing_date: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    case_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confirmation_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)
# =============================================================================
# Witness Statements
# =============================================================================

class WitnessStatement(Base):
    """
    Third-party witness statement.
    """
    __tablename__ = "witness_statements"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Witness info
    witness_name: Mapped[str] = mapped_column(String(255))
    witness_relationship: Mapped[str] = mapped_column(String(100))  # neighbor, family, friend, professional
    witness_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Statement
    statement_text: Mapped[Text] = mapped_column(Text)
    statement_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    
    # Verification
    is_notarized: Mapped[bool] = mapped_column(Boolean, default=False)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # File-based doc ID
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Certified Mail Tracking
# =============================================================================

class CertifiedMail(Base):
    """
    Certified mail tracking record.
    """
    __tablename__ = "certified_mail"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # Mail details
    tracking_number: Mapped[str] = mapped_column(String(50))
    recipient_name: Mapped[str] = mapped_column(String(255))
    recipient_address: Mapped[str] = mapped_column(Text)
    
    # Purpose
    mail_type: Mapped[str] = mapped_column(String(50))  # notice, demand_letter, complaint, other
    subject: Mapped[str] = mapped_column(String(255))

    # Status tracking
    status: Mapped[str] = mapped_column(String(50))  # sent, in_transit, delivered, returned
    sent_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    delivered_date: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)

    # Linked document (copy of what was sent) - stores file-based doc ID
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Session (Persistent OAuth Sessions)
# =============================================================================

class Session(Base):
    """
    Persistent OAuth session.
    
    Replaces in-memory SESSIONS dict so sessions survive server restarts.
    Tokens are stored encrypted using the user's derived key.
    """
    __tablename__ = "sessions"

    # Primary key is the user_id (one session per user)
    user_id: Mapped[str] = mapped_column(String(24), primary_key=True)

    # Provider info
    provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive

    # Encrypted tokens (encrypted with user-specific key)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Session metadata
    authenticated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)

    # Role authorization tracking
    role_authorized_at: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)


# =============================================================================
# Storage Config (User's Storage Settings)
# =============================================================================

class StorageConfig(Base):
    """
    User's storage configuration.
    
    Persists storage-related settings so they survive across sessions:
    - Which cloud providers are connected
    - R2 bucket settings
    - Sync preferences
    - Default vault structure
    
    This is the key model that was missing - without it, users lose
    their storage configuration when sessions expire.
    """
    __tablename__ = "storage_configs"

    # Primary key is the user_id (one config per user)
    user_id: Mapped[str] = mapped_column(String(24), primary_key=True)

    # Primary storage provider (where auth_token.enc lives)
    primary_provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive

    # R2 Configuration (for document storage)
    r2_bucket_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    r2_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    r2_access_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    r2_secret_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Vault structure preferences
    vault_folder_path: Mapped[str] = mapped_column(String(500), default="/Semptify")  # Root folder in cloud storage
    auto_organize: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto-organize by document type

    # Sync settings
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)

    # Connected providers (JSON list of provider names)
    connected_providers: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # e.g., "google_drive,dropbox"

    # Feature flags
    backup_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    backup_provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Secondary provider for backup

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Fraud Analysis Results
# =============================================================================

class FraudAnalysisResult(Base):
    """
    Results from fraud pattern analysis on landlord/property.
    """
    __tablename__ = "fraud_analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Analysis target
    analysis_type: Mapped[str] = mapped_column(String(50))  # hud, mortgage, habitability, eviction
    target_entity: Mapped[str] = mapped_column(String(255), index=True)  # landlord/company name
    property_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Results
    risk_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    risk_level: Mapped[str] = mapped_column(String(20), default="unknown")  # low, medium, high, critical
    findings: Mapped[Text] = mapped_column(Text, default="")  # JSON formatted findings
    indicators: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of indicators
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Evidence links
    evidence_doc_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of doc IDs
    related_complaints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="completed")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Press Release Records
# =============================================================================

class PressReleaseRecord(Base):
    """
    Press release generation and media campaign tracking.
    """
    __tablename__ = "press_release_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Content
    release_type: Mapped[str] = mapped_column(String(50))  # discrimination, code_violations, fraud, etc.
    title: Mapped[str] = mapped_column(String(500))
    headline: Mapped[str] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(10), default="en")  # en, es, hmn, so
    content: Mapped[Text] = mapped_column(Text, default="")
    
    # Targeting
    target_outlets: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of outlets
    target_region: Mapped[str] = mapped_column(String(100), default="Minnesota")
    
    # Media kit reference
    media_kit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, published, sent
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Research Profiles
# =============================================================================

class ResearchProfile(Base):
    """
    Landlord/entity research profile with aggregated findings.
    """
    __tablename__ = "research_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # Entity identification
    entity_type: Mapped[str] = mapped_column(String(50))  # landlord, llc, property_manager
    entity_name: Mapped[str] = mapped_column(String(255), index=True)
    property_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # Research data (JSON format)
    assessor_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorder_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ucc_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispatch_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    news_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sos_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bankruptcy_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    insurance_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Aggregated findings
    normalized_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    fraud_flags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    
    # Sources tracking
    sources_checked: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress, complete, stale

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# Contact Manager
# =============================================================================

class Contact(Base):
    """
    Contact management for case-related people and organizations.
    Tracks landlords, attorneys, witnesses, inspectors, agencies, etc.
    """
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # Contact Type
    contact_type: Mapped[str] = mapped_column(String(50), index=True)
    # Types: landlord, property_manager, attorney, witness, inspector, 
    #        agency, court, legal_aid, tenant_org, other

    # Role in case
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Roles: opposing_party, opposing_counsel, my_witness, their_witness,
    #        inspector, caseworker, judge, mediator, etc.

    # Basic Info
    name: Mapped[str] = mapped_column(String(255), index=True)
    organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Contact Details
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone_alt: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Additional Info
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Comma-separated

    # Source tracking (where did this contact come from?)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Sources: manual, extracted, imported, agency_lookup

    source_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Interaction tracking
    last_contact_date: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class ContactInteraction(Base):
    """
    Log of interactions with contacts (calls, emails, meetings).
    """
    __tablename__ = "contact_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    contact_id: Mapped[str] = mapped_column(String(36), ForeignKey("contacts.id"), index=True)

    # Interaction details
    interaction_type: Mapped[str] = mapped_column(String(50))
    # Types: phone_call, email, letter, in_person, court_appearance, voicemail

    direction: Mapped[str] = mapped_column(String(20))  # incoming, outgoing

    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dates
    interaction_date: Mapped[datetime] = mapped_column(DateTimeTZ)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Attachments/Documents
    related_document_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Follow-up
    follow_up_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    follow_up_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Case Management - Core of Semptify
# =============================================================================

class Case(Base):
    """
    A legal case - the central organizing unit for Semptify.
    
    Everything ties back to a case:
    - Documents are filed FOR a case
    - Timeline events happen IN a case
    - Deadlines are calculated FROM case dates
    - Motions/Answers are generated FOR a case
    """
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)  # Owner/primary defendant
    
    # Case identification
    case_number: Mapped[str] = mapped_column(String(50), index=True)
    court: Mapped[str] = mapped_column(String(200))
    case_type: Mapped[str] = mapped_column(String(50))  # eviction, rent, deposit, habitability, other
    
    # Parties (JSON arrays for multiple)
    plaintiffs: Mapped[str] = mapped_column(Text)  # JSON array of plaintiff names
    defendants: Mapped[str] = mapped_column(Text)  # JSON array of defendant names
    
    # Property
    property_address: Mapped[str] = mapped_column(String(500))
    property_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    property_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    property_state: Mapped[str] = mapped_column(String(2), default="MN")
    property_zip: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Key dates
    date_filed: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    date_served: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    answer_deadline: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    hearing_date: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    
    # Financial
    amount_claimed: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(30), default="active")  # active, answered, settled, dismissed, judgment
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


class CaseDocument(Base):
    """
    Documents attached to a specific case.
    Links documents to their case for organization.
    """
    __tablename__ = "case_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    
    # Document info
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Document classification
    document_type: Mapped[str] = mapped_column(String(50))  # complaint, lease, notice, communication, receipt, photo, answer, motion, other
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # For court filings
    is_filed: Mapped[bool] = mapped_column(Boolean, default=False)
    filed_date: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


class CaseEvent(Base):
    """
    Timeline events specific to a case.
    """
    __tablename__ = "case_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id"), index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(50))  # filing, service, deadline, hearing, motion, communication
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # When
    event_date: Mapped[datetime] = mapped_column(DateTimeTZ, index=True)
    
    # Linked document
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)


# =============================================================================
# Correspondence Tracking - WHO sent WHAT to WHOM and WHEN
# =============================================================================

class Correspondence(Base):
    """
    📧 Correspondence Tracking - Track all communications in your case.
    
    Tracks:
    - WHO sent it (sender)
    - WHO received it (recipient) 
    - WHEN it was sent (date_sent)
    - WHEN it was received (date_received)
    - WHAT type of communication (email, letter, text, phone, certified mail)
    - HOW it was delivered (email, USPS, certified, hand-delivered, text)
    
    This gives a complete audit trail of all communications for court.
    """
    __tablename__ = "correspondence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    
    # ==========================================================================
    # WHO - Sender and Recipient
    # ==========================================================================
    sender_type: Mapped[str] = mapped_column(String(20))  # me, landlord, attorney, court, agency, other
    sender_name: Mapped[str] = mapped_column(String(255))
    sender_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sender_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    recipient_type: Mapped[str] = mapped_column(String(20))  # me, landlord, attorney, court, agency, other
    recipient_name: Mapped[str] = mapped_column(String(255))
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recipient_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Direction (incoming vs outgoing from user's perspective)
    direction: Mapped[str] = mapped_column(String(10), index=True)  # incoming, outgoing
    
    # ==========================================================================
    # WHAT - Communication Content
    # ==========================================================================
    communication_type: Mapped[str] = mapped_column(String(30), index=True)
    # Types: email, letter, certified_mail, text_message, phone_call, 
    #        voicemail, fax, in_person, legal_notice, court_filing
    
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full text if available
    
    # ==========================================================================
    # WHEN - Timing Information
    # ==========================================================================
    date_sent: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True, index=True)
    date_received: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    date_read: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)  # When you read it
    date_responded: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)  # When you responded
    
    # ==========================================================================
    # HOW - Delivery Method and Status
    # ==========================================================================
    delivery_method: Mapped[str] = mapped_column(String(30))
    # Methods: email, usps_regular, usps_certified, usps_priority, fedex, ups,
    #          hand_delivered, text, phone, fax, court_efiling
    
    delivery_status: Mapped[str] = mapped_column(String(20), default="unknown")
    # Status: sent, delivered, read, returned, bounced, unknown
    
    # Certified mail / tracking info
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confirmation_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    return_receipt_received: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================================================
    # Linked Evidence
    # ==========================================================================
    # Link to document(s) containing the actual correspondence
    document_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of doc IDs
    
    # Link to a contact
    contact_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Link to a case
    case_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # ==========================================================================
    # Importance Flags
    # ==========================================================================
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    is_legal_notice: Mapped[bool] = mapped_column(Boolean, default=False)  # Legally significant
    requires_response: Mapped[bool] = mapped_column(Boolean, default=False)
    response_deadline: Mapped[Optional[datetime]] = mapped_column(DateTimeTZ, nullable=True)
    response_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================================================
    # Email Import Metadata (for future email import)
    # ==========================================================================
    email_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Email Message-ID header
    email_thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Gmail thread ID
    email_labels: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Email labels/folders
    imported_from: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # gmail, outlook, manual
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Comma-separated
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, onupdate=utc_now)


# =============================================================================
# OAuth State (Database-Backed for Multi-Worker Support)
# =============================================================================

class OAuthState(Base):
    """
    OAuth state tokens for CSRF protection.
    
    Stored in database instead of in-memory dict to support:
    - Multiple uvicorn workers
    - Server restarts during OAuth flow
    - Production deployments
    
    States automatically expire after 15 minutes.
    """
    __tablename__ = "oauth_states"

    # The state token itself (random string)
    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # OAuth flow data
    provider: Mapped[str] = mapped_column(String(20))  # google_drive, dropbox, onedrive
    role: Mapped[str] = mapped_column(String(20), default="user")
    existing_uid: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    return_to: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeTZ, default=utc_now, index=True)