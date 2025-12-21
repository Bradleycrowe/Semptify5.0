"""
📧 Correspondence Router
=========================
Track WHO sent WHAT to WHOM and WHEN.

Features:
- Log all correspondence (emails, letters, notices, calls)
- Track sender/recipient with dates
- Link to documents for evidence
- Filter by direction (incoming/outgoing)
- Track response deadlines
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_user, StorageUser
from app.models.models import Correspondence, Document, Contact
from app.core.utc import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/correspondence", tags=["correspondence"])


# =============================================================================
# Pydantic Models
# =============================================================================

class CorrespondenceCreate(BaseModel):
    """Create new correspondence record."""
    sender_type: str = Field(..., description="me, landlord, attorney, court, agency, other")
    sender_name: str
    sender_email: Optional[str] = None
    sender_phone: Optional[str] = None
    sender_address: Optional[str] = None
    
    recipient_type: str = Field(..., description="me, landlord, attorney, court, agency, other")
    recipient_name: str
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_address: Optional[str] = None
    
    direction: str = Field(..., description="incoming or outgoing")
    communication_type: str = Field(..., description="email, letter, certified_mail, text_message, phone_call, etc.")
    subject: Optional[str] = None
    summary: Optional[str] = None
    full_content: Optional[str] = None
    
    date_sent: Optional[datetime] = None
    date_received: Optional[datetime] = None
    date_read: Optional[datetime] = None
    
    delivery_method: str = Field(..., description="email, usps_regular, usps_certified, text, phone, etc.")
    delivery_status: str = Field(default="unknown")
    tracking_number: Optional[str] = None
    confirmation_number: Optional[str] = None
    
    document_ids: Optional[List[str]] = None
    contact_id: Optional[str] = None
    case_id: Optional[str] = None
    
    is_important: bool = False
    is_legal_notice: bool = False
    requires_response: bool = False
    response_deadline: Optional[datetime] = None
    
    notes: Optional[str] = None
    tags: Optional[str] = None


class CorrespondenceUpdate(BaseModel):
    """Update correspondence record."""
    sender_type: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    recipient_type: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    
    communication_type: Optional[str] = None
    subject: Optional[str] = None
    summary: Optional[str] = None
    
    date_sent: Optional[datetime] = None
    date_received: Optional[datetime] = None
    date_read: Optional[datetime] = None
    date_responded: Optional[datetime] = None
    
    delivery_method: Optional[str] = None
    delivery_status: Optional[str] = None
    tracking_number: Optional[str] = None
    return_receipt_received: Optional[bool] = None
    
    document_ids: Optional[List[str]] = None
    
    is_important: Optional[bool] = None
    is_legal_notice: Optional[bool] = None
    requires_response: Optional[bool] = None
    response_deadline: Optional[datetime] = None
    response_sent: Optional[bool] = None
    
    notes: Optional[str] = None
    tags: Optional[str] = None


class CorrespondenceResponse(BaseModel):
    """Correspondence record response."""
    id: str
    user_id: str
    sender_type: str
    sender_name: str
    sender_email: Optional[str]
    recipient_type: str
    recipient_name: str
    recipient_email: Optional[str]
    direction: str
    communication_type: str
    subject: Optional[str]
    summary: Optional[str]
    date_sent: Optional[datetime]
    date_received: Optional[datetime]
    date_read: Optional[datetime]
    date_responded: Optional[datetime]
    delivery_method: str
    delivery_status: str
    tracking_number: Optional[str]
    return_receipt_received: bool
    document_ids: Optional[List[str]]
    contact_id: Optional[str]
    case_id: Optional[str]
    is_important: bool
    is_legal_notice: bool
    requires_response: bool
    response_deadline: Optional[datetime]
    response_sent: bool
    notes: Optional[str]
    tags: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/", response_model=List[CorrespondenceResponse])
async def list_correspondence(
    direction: Optional[str] = Query(None, description="incoming or outgoing"),
    communication_type: Optional[str] = Query(None),
    sender_type: Optional[str] = Query(None),
    recipient_type: Optional[str] = Query(None),
    is_important: Optional[bool] = Query(None),
    requires_response: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Search in subject and summary"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """List all correspondence with filters."""
    query = select(Correspondence).where(Correspondence.user_id == user.user_id)
    
    if direction:
        query = query.where(Correspondence.direction == direction)
    if communication_type:
        query = query.where(Correspondence.communication_type == communication_type)
    if sender_type:
        query = query.where(Correspondence.sender_type == sender_type)
    if recipient_type:
        query = query.where(Correspondence.recipient_type == recipient_type)
    if is_important is not None:
        query = query.where(Correspondence.is_important == is_important)
    if requires_response is not None:
        query = query.where(Correspondence.requires_response == requires_response)
    if search:
        query = query.where(
            or_(
                Correspondence.subject.ilike(f"%{search}%"),
                Correspondence.summary.ilike(f"%{search}%"),
                Correspondence.sender_name.ilike(f"%{search}%"),
                Correspondence.recipient_name.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(desc(Correspondence.date_sent), desc(Correspondence.created_at))
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    responses = []
    for item in items:
        doc_ids = json.loads(item.document_ids) if item.document_ids else None
        responses.append(CorrespondenceResponse(
            id=item.id,
            user_id=item.user_id,
            sender_type=item.sender_type,
            sender_name=item.sender_name,
            sender_email=item.sender_email,
            recipient_type=item.recipient_type,
            recipient_name=item.recipient_name,
            recipient_email=item.recipient_email,
            direction=item.direction,
            communication_type=item.communication_type,
            subject=item.subject,
            summary=item.summary,
            date_sent=item.date_sent,
            date_received=item.date_received,
            date_read=item.date_read,
            date_responded=item.date_responded,
            delivery_method=item.delivery_method,
            delivery_status=item.delivery_status,
            tracking_number=item.tracking_number,
            return_receipt_received=item.return_receipt_received,
            document_ids=doc_ids,
            contact_id=item.contact_id,
            case_id=item.case_id,
            is_important=item.is_important,
            is_legal_notice=item.is_legal_notice,
            requires_response=item.requires_response,
            response_deadline=item.response_deadline,
            response_sent=item.response_sent,
            notes=item.notes,
            tags=item.tags,
            created_at=item.created_at,
            updated_at=item.updated_at
        ))
    
    return responses


@router.post("/", response_model=CorrespondenceResponse)
async def create_correspondence(
    data: CorrespondenceCreate,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Create new correspondence record."""
    corr = Correspondence(
        id=str(uuid4()),
        user_id=user.user_id,
        sender_type=data.sender_type,
        sender_name=data.sender_name,
        sender_email=data.sender_email,
        sender_phone=data.sender_phone,
        sender_address=data.sender_address,
        recipient_type=data.recipient_type,
        recipient_name=data.recipient_name,
        recipient_email=data.recipient_email,
        recipient_phone=data.recipient_phone,
        recipient_address=data.recipient_address,
        direction=data.direction,
        communication_type=data.communication_type,
        subject=data.subject,
        summary=data.summary,
        full_content=data.full_content,
        date_sent=data.date_sent,
        date_received=data.date_received,
        date_read=data.date_read,
        delivery_method=data.delivery_method,
        delivery_status=data.delivery_status,
        tracking_number=data.tracking_number,
        confirmation_number=data.confirmation_number,
        document_ids=json.dumps(data.document_ids) if data.document_ids else None,
        contact_id=data.contact_id,
        case_id=data.case_id,
        is_important=data.is_important,
        is_legal_notice=data.is_legal_notice,
        requires_response=data.requires_response,
        response_deadline=data.response_deadline,
        notes=data.notes,
        tags=data.tags,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    
    db.add(corr)
    await db.commit()
    await db.refresh(corr)
    
    logger.info(f"📧 Created correspondence: {data.communication_type} from {data.sender_name} to {data.recipient_name}")
    
    return CorrespondenceResponse(
        id=corr.id,
        user_id=corr.user_id,
        sender_type=corr.sender_type,
        sender_name=corr.sender_name,
        sender_email=corr.sender_email,
        recipient_type=corr.recipient_type,
        recipient_name=corr.recipient_name,
        recipient_email=corr.recipient_email,
        direction=corr.direction,
        communication_type=corr.communication_type,
        subject=corr.subject,
        summary=corr.summary,
        date_sent=corr.date_sent,
        date_received=corr.date_received,
        date_read=corr.date_read,
        date_responded=corr.date_responded,
        delivery_method=corr.delivery_method,
        delivery_status=corr.delivery_status,
        tracking_number=corr.tracking_number,
        return_receipt_received=corr.return_receipt_received,
        document_ids=data.document_ids,
        contact_id=corr.contact_id,
        case_id=corr.case_id,
        is_important=corr.is_important,
        is_legal_notice=corr.is_legal_notice,
        requires_response=corr.requires_response,
        response_deadline=corr.response_deadline,
        response_sent=corr.response_sent,
        notes=corr.notes,
        tags=corr.tags,
        created_at=corr.created_at,
        updated_at=corr.updated_at
    )


@router.get("/stats/summary")
async def correspondence_summary(
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Get correspondence statistics summary."""
    query = select(Correspondence).where(Correspondence.user_id == user.user_id)
    result = await db.execute(query)
    all_corr = result.scalars().all()
    
    total = len(all_corr)
    incoming = sum(1 for c in all_corr if c.direction == "incoming")
    outgoing = sum(1 for c in all_corr if c.direction == "outgoing")
    requires_response = sum(1 for c in all_corr if c.requires_response and not c.response_sent)
    important = sum(1 for c in all_corr if c.is_important)
    legal_notices = sum(1 for c in all_corr if c.is_legal_notice)
    
    type_counts = {}
    for c in all_corr:
        t = c.communication_type
        type_counts[t] = type_counts.get(t, 0) + 1
    
    now = utc_now()
    overdue = sum(1 for c in all_corr 
                  if c.requires_response and not c.response_sent 
                  and c.response_deadline and c.response_deadline < now)
    
    return {
        "total": total,
        "incoming": incoming,
        "outgoing": outgoing,
        "requires_response": requires_response,
        "overdue_responses": overdue,
        "important": important,
        "legal_notices": legal_notices,
        "by_type": type_counts
    }


@router.get("/pending/responses")
async def pending_responses(
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Get correspondence requiring response."""
    query = select(Correspondence).where(
        and_(
            Correspondence.user_id == user.user_id,
            Correspondence.requires_response == True,
            Correspondence.response_sent == False
        )
    ).order_by(Correspondence.response_deadline)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    now = utc_now()
    responses = []
    for item in items:
        is_overdue = item.response_deadline and item.response_deadline < now
        days_remaining = None
        if item.response_deadline:
            delta = item.response_deadline - now
            days_remaining = delta.days
        
        responses.append({
            "id": item.id,
            "communication_type": item.communication_type,
            "sender_name": item.sender_name,
            "subject": item.subject,
            "date_received": item.date_received,
            "response_deadline": item.response_deadline,
            "is_overdue": is_overdue,
            "days_remaining": days_remaining,
            "is_legal_notice": item.is_legal_notice
        })
    
    return responses


@router.get("/{correspondence_id}", response_model=CorrespondenceResponse)
async def get_correspondence(
    correspondence_id: str,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Get single correspondence record."""
    query = select(Correspondence).where(
        and_(
            Correspondence.id == correspondence_id,
            Correspondence.user_id == user.user_id
        )
    )
    result = await db.execute(query)
    corr = result.scalar_one_or_none()
    
    if not corr:
        raise HTTPException(status_code=404, detail="Correspondence not found")
    
    doc_ids = json.loads(corr.document_ids) if corr.document_ids else None
    
    return CorrespondenceResponse(
        id=corr.id,
        user_id=corr.user_id,
        sender_type=corr.sender_type,
        sender_name=corr.sender_name,
        sender_email=corr.sender_email,
        recipient_type=corr.recipient_type,
        recipient_name=corr.recipient_name,
        recipient_email=corr.recipient_email,
        direction=corr.direction,
        communication_type=corr.communication_type,
        subject=corr.subject,
        summary=corr.summary,
        date_sent=corr.date_sent,
        date_received=corr.date_received,
        date_read=corr.date_read,
        date_responded=corr.date_responded,
        delivery_method=corr.delivery_method,
        delivery_status=corr.delivery_status,
        tracking_number=corr.tracking_number,
        return_receipt_received=corr.return_receipt_received,
        document_ids=doc_ids,
        contact_id=corr.contact_id,
        case_id=corr.case_id,
        is_important=corr.is_important,
        is_legal_notice=corr.is_legal_notice,
        requires_response=corr.requires_response,
        response_deadline=corr.response_deadline,
        response_sent=corr.response_sent,
        notes=corr.notes,
        tags=corr.tags,
        created_at=corr.created_at,
        updated_at=corr.updated_at
    )


@router.patch("/{correspondence_id}", response_model=CorrespondenceResponse)
async def update_correspondence(
    correspondence_id: str,
    data: CorrespondenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Update correspondence record."""
    query = select(Correspondence).where(
        and_(
            Correspondence.id == correspondence_id,
            Correspondence.user_id == user.user_id
        )
    )
    result = await db.execute(query)
    corr = result.scalar_one_or_none()
    
    if not corr:
        raise HTTPException(status_code=404, detail="Correspondence not found")
    
    update_data = data.dict(exclude_unset=True)
    if "document_ids" in update_data:
        update_data["document_ids"] = json.dumps(update_data["document_ids"]) if update_data["document_ids"] else None
    
    for key, value in update_data.items():
        setattr(corr, key, value)
    
    corr.updated_at = utc_now()
    
    await db.commit()
    await db.refresh(corr)
    
    logger.info(f"📧 Updated correspondence: {correspondence_id}")
    
    doc_ids = json.loads(corr.document_ids) if corr.document_ids else None
    
    return CorrespondenceResponse(
        id=corr.id,
        user_id=corr.user_id,
        sender_type=corr.sender_type,
        sender_name=corr.sender_name,
        sender_email=corr.sender_email,
        recipient_type=corr.recipient_type,
        recipient_name=corr.recipient_name,
        recipient_email=corr.recipient_email,
        direction=corr.direction,
        communication_type=corr.communication_type,
        subject=corr.subject,
        summary=corr.summary,
        date_sent=corr.date_sent,
        date_received=corr.date_received,
        date_read=corr.date_read,
        date_responded=corr.date_responded,
        delivery_method=corr.delivery_method,
        delivery_status=corr.delivery_status,
        tracking_number=corr.tracking_number,
        return_receipt_received=corr.return_receipt_received,
        document_ids=doc_ids,
        contact_id=corr.contact_id,
        case_id=corr.case_id,
        is_important=corr.is_important,
        is_legal_notice=corr.is_legal_notice,
        requires_response=corr.requires_response,
        response_deadline=corr.response_deadline,
        response_sent=corr.response_sent,
        notes=corr.notes,
        tags=corr.tags,
        created_at=corr.created_at,
        updated_at=corr.updated_at
    )


@router.delete("/{correspondence_id}")
async def delete_correspondence(
    correspondence_id: str,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Delete correspondence record."""
    query = select(Correspondence).where(
        and_(
            Correspondence.id == correspondence_id,
            Correspondence.user_id == user.user_id
        )
    )
    result = await db.execute(query)
    corr = result.scalar_one_or_none()
    
    if not corr:
        raise HTTPException(status_code=404, detail="Correspondence not found")
    
    await db.delete(corr)
    await db.commit()
    
    logger.info(f"🗑️ Deleted correspondence: {correspondence_id}")
    
    return {"status": "deleted", "id": correspondence_id}


# =============================================================================
# Quick Log Endpoints
# =============================================================================

@router.post("/quick/email-received")
async def quick_log_email_received(
    sender_name: str,
    sender_email: str,
    subject: str,
    summary: Optional[str] = None,
    date_received: Optional[datetime] = None,
    requires_response: bool = False,
    response_deadline: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Quick log an incoming email."""
    corr = Correspondence(
        id=str(uuid4()),
        user_id=user.user_id,
        sender_type="landlord",
        sender_name=sender_name,
        sender_email=sender_email,
        recipient_type="me",
        recipient_name="Me",
        direction="incoming",
        communication_type="email",
        subject=subject,
        summary=summary,
        date_sent=date_received,
        date_received=date_received or utc_now(),
        delivery_method="email",
        delivery_status="delivered",
        requires_response=requires_response,
        response_deadline=response_deadline,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    
    db.add(corr)
    await db.commit()
    
    return {"status": "logged", "id": corr.id}


@router.post("/quick/email-sent")
async def quick_log_email_sent(
    recipient_name: str,
    recipient_email: str,
    subject: str,
    summary: Optional[str] = None,
    date_sent: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Quick log an outgoing email."""
    corr = Correspondence(
        id=str(uuid4()),
        user_id=user.user_id,
        sender_type="me",
        sender_name="Me",
        recipient_type="landlord",
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        direction="outgoing",
        communication_type="email",
        subject=subject,
        summary=summary,
        date_sent=date_sent or utc_now(),
        delivery_method="email",
        delivery_status="sent",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    
    db.add(corr)
    await db.commit()
    
    return {"status": "logged", "id": corr.id}


@router.post("/quick/letter-received")
async def quick_log_letter_received(
    sender_name: str,
    subject: str,
    date_received: datetime,
    is_certified: bool = False,
    tracking_number: Optional[str] = None,
    summary: Optional[str] = None,
    is_legal_notice: bool = False,
    requires_response: bool = False,
    response_deadline: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Quick log a received letter."""
    corr = Correspondence(
        id=str(uuid4()),
        user_id=user.user_id,
        sender_type="landlord",
        sender_name=sender_name,
        recipient_type="me",
        recipient_name="Me",
        direction="incoming",
        communication_type="certified_mail" if is_certified else "letter",
        subject=subject,
        summary=summary,
        date_received=date_received,
        delivery_method="usps_certified" if is_certified else "usps_regular",
        delivery_status="delivered",
        tracking_number=tracking_number,
        is_legal_notice=is_legal_notice,
        requires_response=requires_response,
        response_deadline=response_deadline,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    
    db.add(corr)
    await db.commit()
    
    return {"status": "logged", "id": corr.id}


@router.post("/quick/phone-call")
async def quick_log_phone_call(
    direction: str,
    other_party_name: str,
    other_party_phone: Optional[str] = None,
    summary: str = "",
    date_time: Optional[datetime] = None,
    duration_minutes: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: StorageUser = Depends(require_user)
):
    """Quick log a phone call."""
    if direction == "incoming":
        sender_type = "landlord"
        sender_name = other_party_name
        recipient_type = "me"
        recipient_name = "Me"
    else:
        sender_type = "me"
        sender_name = "Me"
        recipient_type = "landlord"
        recipient_name = other_party_name
    
    call_time = date_time or utc_now()
    
    corr = Correspondence(
        id=str(uuid4()),
        user_id=user.user_id,
        sender_type=sender_type,
        sender_name=sender_name,
        sender_phone=other_party_phone if direction == "incoming" else None,
        recipient_type=recipient_type,
        recipient_name=recipient_name,
        recipient_phone=other_party_phone if direction == "outgoing" else None,
        direction=direction,
        communication_type="phone_call",
        subject=f"Phone call with {other_party_name}",
        summary=summary,
        date_sent=call_time,
        date_received=call_time,
        delivery_method="phone",
        delivery_status="completed",
        created_at=utc_now(),
        updated_at=utc_now()
    )
    
    db.add(corr)
    await db.commit()
    
    return {"status": "logged", "id": corr.id}
