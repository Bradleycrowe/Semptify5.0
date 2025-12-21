"""
Case Management API - Core of Semptify
All operations center around a single case.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.database import get_db_session
from app.models.models import Case, CaseDocument, CaseEvent
from app.core.utc import utc_now

router = APIRouter(prefix="/api/cases", tags=["Cases"])


# =============================================================================
# Pydantic Models
# =============================================================================

class CaseCreate(BaseModel):
    """Create a new case."""
    case_number: str
    court: str
    case_type: str = "eviction"
    plaintiffs: List[str]
    defendants: List[str]
    property_address: str
    property_unit: Optional[str] = None
    property_city: Optional[str] = None
    property_state: str = "MN"
    property_zip: Optional[str] = None
    date_filed: Optional[str] = None
    date_served: Optional[str] = None
    amount_claimed: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None  # Optional, defaults to "local"


# Active case statuses - user can only have ONE case with these statuses
ACTIVE_STATUSES = ["active", "pending", "in_progress", "filed"]

# Completed statuses - allow creating new case when existing case has these
COMPLETED_STATUSES = ["paused", "judgment", "dismissed", "settled", "closed", "won", "lost"]


class CaseUpdate(BaseModel):
    """Update case details."""
    case_number: Optional[str] = None
    court: Optional[str] = None
    case_type: Optional[str] = None
    plaintiffs: Optional[List[str]] = None
    defendants: Optional[List[str]] = None
    property_address: Optional[str] = None
    property_unit: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    property_zip: Optional[str] = None
    date_filed: Optional[str] = None
    date_served: Optional[str] = None
    hearing_date: Optional[str] = None
    amount_claimed: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CaseResponse(BaseModel):
    """Case response with computed fields."""
    id: str
    case_number: str
    court: str
    case_type: str
    plaintiffs: List[str]
    defendants: List[str]
    property_address: str
    property_unit: Optional[str]
    property_city: Optional[str]
    property_state: str
    property_zip: Optional[str]
    date_filed: Optional[str]
    date_served: Optional[str]
    answer_deadline: Optional[str]
    hearing_date: Optional[str]
    amount_claimed: Optional[str]
    status: str
    notes: Optional[str]
    document_count: int = 0
    event_count: int = 0
    created_at: str
    updated_at: str


class DocumentCreate(BaseModel):
    """Add document to case."""
    document_type: str
    description: Optional[str] = None


class EventCreate(BaseModel):
    """Add event to case timeline."""
    event_type: str
    title: str
    description: Optional[str] = None
    event_date: str
    document_id: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None


def format_date(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string."""
    if not dt:
        return None
    return dt.isoformat()


def calculate_answer_deadline(date_served: Optional[datetime], case_type: str = "eviction") -> Optional[datetime]:
    """Calculate answer deadline based on MN rules."""
    if not date_served:
        return None
    # MN eviction: 7 days to answer
    # Other civil: typically 20-30 days
    if case_type == "eviction":
        return date_served + timedelta(days=7)
    else:
        return date_served + timedelta(days=20)


# =============================================================================
# Case CRUD Endpoints
# =============================================================================

@router.post("", response_model=dict)
async def create_case(case_data: CaseCreate):
    """
    Create a new case.
    
    This is the primary entry point - everything else ties to a case.
    RULE: One active case per user. User must pause or complete existing case first.
    """
    from sqlalchemy import select, and_
    
    user_id = case_data.user_id or "local"
    case_id = str(uuid.uuid4())
    
    # Parse dates
    date_filed = parse_date(case_data.date_filed)
    date_served = parse_date(case_data.date_served)
    
    # Calculate answer deadline
    answer_deadline = None
    if date_served:
        answer_deadline = calculate_answer_deadline(date_served, case_data.case_type)
    
    async with get_db_session() as session:
        # Check for existing active case for this user
        result = await session.execute(
            select(Case).where(
                and_(
                    Case.user_id == user_id,
                    Case.status.in_(ACTIVE_STATUSES)
                )
            )
        )
        existing_active = result.scalar_one_or_none()
        
        if existing_active:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "active_case_exists",
                    "message": f"You already have an active case: {existing_active.case_number}. Please pause or complete it before creating a new case.",
                    "existing_case_id": existing_active.id,
                    "existing_case_number": existing_active.case_number
                }
            )
        
        new_case = Case(
            id=case_id,
            user_id=user_id,
            case_number=case_data.case_number,
            court=case_data.court,
            case_type=case_data.case_type,
            plaintiffs=json.dumps(case_data.plaintiffs),
            defendants=json.dumps(case_data.defendants),
            property_address=case_data.property_address,
            property_unit=case_data.property_unit,
            property_city=case_data.property_city,
            property_state=case_data.property_state,
            property_zip=case_data.property_zip,
            date_filed=date_filed,
            date_served=date_served,
            answer_deadline=answer_deadline,
            amount_claimed=case_data.amount_claimed,
            notes=case_data.notes,
            status="active"
        )
        session.add(new_case)
        await session.commit()
    
    return {
        "success": True,
        "case_id": case_id,
        "message": "Case created successfully",
        "answer_deadline": format_date(answer_deadline)
    }


@router.get("/active", response_model=dict)
async def get_active_case(user_id: str = "local"):
    """Get the user's current active case (if any)."""
    from sqlalchemy import select, and_
    
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(
                and_(
                    Case.user_id == user_id,
                    Case.status.in_(ACTIVE_STATUSES)
                )
            )
        )
        case = result.scalar_one_or_none()
        
        if not case:
            return {"has_active_case": False, "case": None}
        
        return {
            "has_active_case": True,
            "case": {
                "id": case.id,
                "case_number": case.case_number,
                "court": case.court,
                "case_type": case.case_type,
                "plaintiffs": json.loads(case.plaintiffs) if case.plaintiffs else [],
                "defendants": json.loads(case.defendants) if case.defendants else [],
                "property_address": case.property_address,
                "status": case.status,
                "answer_deadline": format_date(case.answer_deadline),
                "created_at": format_date(case.created_at)
            }
        }


@router.post("/{case_id}/pause", response_model=dict)
async def pause_case(case_id: str):
    """Pause a case - allows user to create a new case."""
    from sqlalchemy import select
    
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        case.status = "paused"
        case.updated_at = utc_now()
        await session.commit()
        
        return {"success": True, "message": "Case paused. You can now create a new case."}


@router.post("/{case_id}/resume", response_model=dict)
async def resume_case(case_id: str):
    """Resume a paused case - will pause any currently active case."""
    from sqlalchemy import select, and_
    
    async with get_db_session() as session:
        # Get the case to resume
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        if case.status not in ["paused"]:
            raise HTTPException(status_code=400, detail="Only paused cases can be resumed")
        
        # Pause any currently active case for this user
        active_result = await session.execute(
            select(Case).where(
                and_(
                    Case.user_id == case.user_id,
                    Case.status.in_(ACTIVE_STATUSES),
                    Case.id != case_id
                )
            )
        )
        active_case = active_result.scalar_one_or_none()
        
        if active_case:
            active_case.status = "paused"
            active_case.updated_at = utc_now()
        
        # Resume the requested case
        case.status = "active"
        case.updated_at = utc_now()
        await session.commit()
        
        return {
            "success": True,
            "message": "Case resumed",
            "paused_case_id": active_case.id if active_case else None
        }


@router.post("/{case_id}/judgment", response_model=dict)
async def record_judgment(case_id: str, outcome: str = "judgment"):
    """
    Record judgment on a case - marks it complete.
    Outcome options: judgment, dismissed, settled, won, lost
    """
    from sqlalchemy import select
    
    valid_outcomes = ["judgment", "dismissed", "settled", "won", "lost", "closed"]
    if outcome not in valid_outcomes:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid outcome. Must be one of: {', '.join(valid_outcomes)}"
        )
    
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        case.status = outcome
        case.updated_at = utc_now()
        await session.commit()
        
        return {
            "success": True, 
            "message": f"Case marked as {outcome}. You can now create a new case."
        }


@router.get("", response_model=List[dict])
async def list_cases(user_id: str = "local", include_completed: bool = True):
    """List all cases for the user."""
    from sqlalchemy import select
    
    async with get_db_session() as session:
        query = select(Case).where(Case.user_id == user_id)
        
        if not include_completed:
            query = query.where(Case.status.in_(ACTIVE_STATUSES + ["paused"]))
        
        result = await session.execute(query.order_by(Case.created_at.desc()))
        cases = result.scalars().all()
        
        return [
            {
                "id": c.id,
                "case_number": c.case_number,
                "court": c.court,
                "case_type": c.case_type,
                "plaintiffs": json.loads(c.plaintiffs) if c.plaintiffs else [],
                "defendants": json.loads(c.defendants) if c.defendants else [],
                "property_address": c.property_address,
                "status": c.status,
                "answer_deadline": format_date(c.answer_deadline),
                "created_at": format_date(c.created_at)
            }
            for c in cases
        ]


@router.get("/{case_id}", response_model=dict)
async def get_case(case_id: str):
    """Get case details by ID."""
    from sqlalchemy import select, func
    
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Count documents
        doc_count = await session.execute(
            select(func.count(CaseDocument.id)).where(CaseDocument.case_id == case_id)
        )
        document_count = doc_count.scalar() or 0
        
        # Count events
        event_count_result = await session.execute(
            select(func.count(CaseEvent.id)).where(CaseEvent.case_id == case_id)
        )
        event_count = event_count_result.scalar() or 0
        
        return {
            "id": case.id,
            "case_number": case.case_number,
            "court": case.court,
            "case_type": case.case_type,
            "plaintiffs": json.loads(case.plaintiffs) if case.plaintiffs else [],
            "defendants": json.loads(case.defendants) if case.defendants else [],
            "property_address": case.property_address,
            "property_unit": case.property_unit,
            "property_city": case.property_city,
            "property_state": case.property_state,
            "property_zip": case.property_zip,
            "date_filed": format_date(case.date_filed),
            "date_served": format_date(case.date_served),
            "answer_deadline": format_date(case.answer_deadline),
            "hearing_date": format_date(case.hearing_date),
            "amount_claimed": case.amount_claimed,
            "status": case.status,
            "notes": case.notes,
            "document_count": document_count,
            "event_count": event_count,
            "created_at": format_date(case.created_at),
            "updated_at": format_date(case.updated_at)
        }


@router.put("/{case_id}", response_model=dict)
async def update_case(case_id: str, case_data: CaseUpdate):
    """Update case details."""
    from sqlalchemy import select
    
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Update fields
        if case_data.case_number is not None:
            case.case_number = case_data.case_number
        if case_data.court is not None:
            case.court = case_data.court
        if case_data.case_type is not None:
            case.case_type = case_data.case_type
        if case_data.plaintiffs is not None:
            case.plaintiffs = json.dumps(case_data.plaintiffs)
        if case_data.defendants is not None:
            case.defendants = json.dumps(case_data.defendants)
        if case_data.property_address is not None:
            case.property_address = case_data.property_address
        if case_data.property_unit is not None:
            case.property_unit = case_data.property_unit
        if case_data.property_city is not None:
            case.property_city = case_data.property_city
        if case_data.property_state is not None:
            case.property_state = case_data.property_state
        if case_data.property_zip is not None:
            case.property_zip = case_data.property_zip
        if case_data.date_filed is not None:
            case.date_filed = parse_date(case_data.date_filed)
        if case_data.date_served is not None:
            case.date_served = parse_date(case_data.date_served)
            # Recalculate answer deadline
            if case.date_served:
                case.answer_deadline = calculate_answer_deadline(case.date_served, case.case_type)
        if case_data.hearing_date is not None:
            case.hearing_date = parse_date(case_data.hearing_date)
        if case_data.amount_claimed is not None:
            case.amount_claimed = case_data.amount_claimed
        if case_data.status is not None:
            case.status = case_data.status
        if case_data.notes is not None:
            case.notes = case_data.notes
        
        await session.commit()
        
        return {"success": True, "message": "Case updated"}


@router.delete("/{case_id}", response_model=dict)
async def delete_case(case_id: str):
    """Delete a case and all associated documents/events."""
    from sqlalchemy import select, delete
    
    async with get_db_session() as session:
        # First check if case exists
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Delete associated documents
        await session.execute(
            delete(CaseDocument).where(CaseDocument.case_id == case_id)
        )
        
        # Delete associated events
        await session.execute(
            delete(CaseEvent).where(CaseEvent.case_id == case_id)
        )
        
        # Delete case
        await session.delete(case)
        await session.commit()
        
        return {"success": True, "message": "Case deleted"}


# =============================================================================
# Case Documents
# =============================================================================

@router.post("/{case_id}/documents", response_model=dict)
async def upload_case_document(
    case_id: str,
    file: UploadFile = File(...),
    document_type: str = Form("other"),
    description: str = Form(None)
):
    """Upload a document to a case."""
    from sqlalchemy import select
    
    # Verify case exists
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
    
    # Save file
    doc_id = str(uuid.uuid4())
    upload_dir = Path("uploads/cases") / case_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / f"{doc_id}_{file.filename}"
    content = await file.read()
    file_path.write_bytes(content)
    
    # Create database record
    async with get_db_session() as session:
        doc = CaseDocument(
            id=doc_id,
            case_id=case_id,
            filename=file.filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=file.content_type,
            document_type=document_type,
            description=description
        )
        session.add(doc)
        await session.commit()
    
    return {
        "success": True,
        "document_id": doc_id,
        "filename": file.filename,
        "message": "Document uploaded"
    }


@router.get("/{case_id}/documents", response_model=List[dict])
async def list_case_documents(case_id: str):
    """List all documents for a case."""
    from sqlalchemy import select
    
    async with get_db_session() as session:
        result = await session.execute(
            select(CaseDocument)
            .where(CaseDocument.case_id == case_id)
            .order_by(CaseDocument.uploaded_at.desc())
        )
        docs = result.scalars().all()
        
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "original_filename": d.original_filename,
                "document_type": d.document_type,
                "description": d.description,
                "file_size": d.file_size,
                "mime_type": d.mime_type,
                "is_filed": d.is_filed,
                "filed_date": format_date(d.filed_date),
                "uploaded_at": format_date(d.uploaded_at)
            }
            for d in docs
        ]


@router.delete("/{case_id}/documents/{doc_id}", response_model=dict)
async def delete_case_document(case_id: str, doc_id: str):
    """Delete a document from a case."""
    from sqlalchemy import select, delete
    
    async with get_db_session() as session:
        # Get document to delete file
        result = await session.execute(
            select(CaseDocument).where(
                CaseDocument.id == doc_id,
                CaseDocument.case_id == case_id
            )
        )
        doc = result.scalar_one_or_none()
        
        if doc and doc.file_path:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        
        # Delete from database
        await session.execute(
            delete(CaseDocument).where(
                CaseDocument.id == doc_id,
                CaseDocument.case_id == case_id
            )
        )
        await session.commit()
    
    return {"success": True, "message": "Document deleted"}


# =============================================================================
# Case Events (Timeline)
# =============================================================================

@router.post("/{case_id}/events", response_model=dict)
async def add_case_event(case_id: str, event_data: EventCreate):
    """Add an event to the case timeline."""
    from sqlalchemy import select
    
    # Verify case exists
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Case not found")
    
    event_id = str(uuid.uuid4())
    event_date = parse_date(event_data.event_date)
    
    async with get_db_session() as session:
        event = CaseEvent(
            id=event_id,
            case_id=case_id,
            event_type=event_data.event_type,
            title=event_data.title,
            description=event_data.description,
            event_date=event_date or utc_now(),
            document_id=event_data.document_id
        )
        session.add(event)
        await session.commit()
    
    return {
        "success": True,
        "event_id": event_id,
        "message": "Event added"
    }


@router.get("/{case_id}/events", response_model=List[dict])
async def list_case_events(case_id: str):
    """List all events for a case timeline."""
    from sqlalchemy import select
    
    async with get_db_session() as session:
        result = await session.execute(
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.event_date.desc())
        )
        events = result.scalars().all()
        
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "event_date": format_date(e.event_date),
                "document_id": e.document_id,
                "is_completed": e.is_completed,
                "created_at": format_date(e.created_at)
            }
            for e in events
        ]


@router.delete("/{case_id}/events/{event_id}", response_model=dict)
async def delete_case_event(case_id: str, event_id: str):
    """Delete an event from the case timeline."""
    from sqlalchemy import delete
    
    async with get_db_session() as session:
        await session.execute(
            delete(CaseEvent).where(
                CaseEvent.id == event_id,
                CaseEvent.case_id == case_id
            )
        )
        await session.commit()
    
    return {"success": True, "message": "Event deleted"}


# =============================================================================
# Document to Timeline Event Conversion
# =============================================================================

class DocumentToEventRequest(BaseModel):
    """Request to convert a document to a timeline event."""
    document_id: str
    event_date: str  # When the event in the document occurred
    summary: str  # User-provided summary of what the document shows
    event_type: Optional[str] = "document"


@router.post("/{case_id}/documents/{doc_id}/to-timeline", response_model=dict)
async def document_to_timeline_event(
    case_id: str,
    doc_id: str,
    event_date: str = Form(...),
    summary: str = Form(...),
    event_type: str = Form("document")
):
    """
    Convert a case document into a timeline event.
    
    Documents contain dates and describe events that occurred.
    This endpoint allows adding a document as a timestamped event
    on the case timeline with a user-provided summary.
    """
    from sqlalchemy import select
    
    async with get_db_session() as session:
        # Verify case exists
        case_result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        if not case_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get the document
        doc_result = await session.execute(
            select(CaseDocument).where(
                CaseDocument.id == doc_id,
                CaseDocument.case_id == case_id
            )
        )
        doc = doc_result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Parse the event date
        parsed_date = parse_date(event_date)
        if not parsed_date:
            raise HTTPException(status_code=400, detail="Invalid event date")
        
        # Create timeline event linked to document
        event_id = str(uuid.uuid4())
        event = CaseEvent(
            id=event_id,
            case_id=case_id,
            event_type=event_type,
            title=f"📄 {doc.filename or doc.original_filename}",
            description=summary,
            event_date=parsed_date,
            document_id=doc_id
        )
        session.add(event)
        await session.commit()
    
    return {
        "success": True,
        "event_id": event_id,
        "message": f"Document added to timeline as '{event_type}' event"
    }


@router.get("/{case_id}/timeline", response_model=dict)
async def get_case_timeline(case_id: str, include_documents: bool = True):
    """
    Get complete case timeline including events and documents.
    
    Returns events in chronological order with document indicators.
    Documents can be filtered to show only those linked to events
    or all documents with their upload dates.
    """
    from sqlalchemy import select
    
    async with get_db_session() as session:
        # Get case events
        events_result = await session.execute(
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.event_date.asc())
        )
        events = events_result.scalars().all()
        
        # Get documents if requested
        documents = []
        if include_documents:
            docs_result = await session.execute(
                select(CaseDocument)
                .where(CaseDocument.case_id == case_id)
                .order_by(CaseDocument.uploaded_at.asc())
            )
            documents = docs_result.scalars().all()
        
        # Build timeline combining events and unlinked documents
        timeline_items = []
        linked_doc_ids = {e.document_id for e in events if e.document_id}
        
        # Add events
        for e in events:
            timeline_items.append({
                "id": e.id,
                "type": "event",
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "date": format_date(e.event_date),
                "document_id": e.document_id,
                "has_document": e.document_id is not None,
                "is_completed": e.is_completed
            })
        
        # Add unlinked documents as potential events
        for doc in documents:
            if doc.id not in linked_doc_ids:
                timeline_items.append({
                    "id": f"doc_{doc.id}",
                    "type": "unlinked_document",
                    "event_type": doc.document_type or "document",
                    "title": f"📄 {doc.filename or doc.original_filename}",
                    "description": doc.description or f"Uploaded: {doc.document_type or 'document'}",
                    "date": format_date(doc.uploaded_at),
                    "document_id": doc.id,
                    "has_document": True,
                    "needs_date": True  # Flag to indicate user should add event date
                })
        
        # Sort by date
        timeline_items.sort(key=lambda x: x["date"] or "")
        
        return {
            "case_id": case_id,
            "total_events": len(events),
            "total_documents": len(documents),
            "unlinked_documents": len(documents) - len(linked_doc_ids),
            "timeline": timeline_items
        }


# =============================================================================
# Case Actions - Generate Documents
# =============================================================================

@router.get("/{case_id}/generate/answer", response_model=dict)
async def generate_answer(case_id: str):
    """Generate data needed for an answer form."""
    from sqlalchemy import select
    
    async with get_db_session() as session:
        result = await session.execute(
            select(Case).where(Case.id == case_id)
        )
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return {
            "case_id": case.id,
            "case_number": case.case_number,
            "court": case.court,
            "plaintiffs": json.loads(case.plaintiffs) if case.plaintiffs else [],
            "defendants": json.loads(case.defendants) if case.defendants else [],
            "property_address": case.property_address,
            "date_filed": format_date(case.date_filed),
            "answer_deadline": format_date(case.answer_deadline),
            "amount_claimed": case.amount_claimed,
            # Pre-populate common defenses based on case type
            "suggested_defenses": get_suggested_defenses(case.case_type)
        }


def get_suggested_defenses(case_type: str) -> List[dict]:
    """Get suggested defenses based on case type."""
    if case_type == "eviction":
        return [
            {"code": "improper_notice", "label": "Improper Notice", "description": "The notice did not comply with statutory requirements"},
            {"code": "rent_paid", "label": "Rent Was Paid", "description": "All rent due was paid before the action was filed"},
            {"code": "habitability", "label": "Breach of Habitability", "description": "Landlord failed to maintain habitable conditions"},
            {"code": "retaliation", "label": "Retaliatory Eviction", "description": "Eviction is in retaliation for exercising legal rights"},
            {"code": "discrimination", "label": "Discrimination", "description": "Eviction is based on protected class status"},
            {"code": "improper_service", "label": "Improper Service", "description": "Summons and complaint were not properly served"},
            {"code": "no_license", "label": "No Rental License", "description": "Property lacks required rental license"},
        ]
    elif case_type == "deposit":
        return [
            {"code": "no_itemization", "label": "No Itemization", "description": "Landlord failed to provide itemized statement within 21 days"},
            {"code": "normal_wear", "label": "Normal Wear and Tear", "description": "Deductions were for normal wear and tear"},
            {"code": "pre_existing", "label": "Pre-Existing Damage", "description": "Damage existed before tenancy began"},
        ]
    return []
