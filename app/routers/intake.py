"""
Document Intake API Router

Provides endpoints for:
- Document upload and intake
- Processing status tracking
- Extraction results retrieval
- Issue detection results
- Batch processing
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.core.security import get_user_id
from app.services.document_intake import (
    get_intake_engine,
    DocumentType,
    IntakeStatus,
    IssueSeverity,
    LanguageCode,
)
from app.core.event_bus import event_bus, EventType as BusEventType

# Import flow orchestrator for complete pipeline
try:
    from app.services.document_flow_orchestrator import DocumentFlowOrchestrator
    FLOW_AVAILABLE = True
except ImportError:
    FLOW_AVAILABLE = False


router = APIRouter(prefix="/api/intake", tags=["Document Intake"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class IntakeStatusResponse(BaseModel):
    """Processing status response."""
    id: str
    status: str
    status_message: str
    progress_percent: int


class ExtractedDateResponse(BaseModel):
    """Extracted date response."""
    date: str
    label: str
    confidence: float
    source_text: str
    is_deadline: bool
    days_until: Optional[int] = None


class ExtractedPartyResponse(BaseModel):
    """Extracted party response."""
    name: str
    role: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    confidence: float


class ExtractedAmountResponse(BaseModel):
    """Extracted amount response."""
    amount: float
    label: str
    currency: str
    period: Optional[str] = None
    confidence: float
    source_text: str


class DetectedIssueResponse(BaseModel):
    """Detected issue response."""
    issue_id: str
    severity: str
    title: str
    description: str
    affected_text: Optional[str] = None
    legal_basis: Optional[str] = None
    recommended_action: Optional[str] = None
    deadline: Optional[str] = None
    related_laws: list[str] = []


class ExtractionResultResponse(BaseModel):
    """Complete extraction result response."""
    doc_type: str
    doc_type_confidence: float
    language: str
    page_count: int
    word_count: int
    summary: str
    key_points: list[str]
    dates: list[ExtractedDateResponse]
    parties: list[ExtractedPartyResponse]
    amounts: list[ExtractedAmountResponse]
    issues: list[DetectedIssueResponse]
    extracted_at: str


class IntakeDocumentResponse(BaseModel):
    """Complete intake document response."""
    id: str
    user_id: str
    filename: str
    file_hash: str
    file_size: int
    mime_type: str
    status: str
    status_message: str
    progress_percent: int
    extraction: Optional[ExtractionResultResponse] = None
    uploaded_at: str
    processed_at: Optional[str] = None


class UploadResponse(BaseModel):
    """Upload response."""
    id: str
    filename: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    """Batch upload response."""
    uploaded: list[UploadResponse]
    failed: list[dict]
    total_uploaded: int
    total_failed: int


# =============================================================================
# UPLOAD ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(..., description="User ID for the document owner"),
):
    """
    Upload a document for intake processing.
    
    The document will be:
    1. Received and validated
    2. Hashed for integrity
    3. Queued for processing
    
    Use the returned ID to check processing status.
    """
    engine = get_intake_engine()
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if len(content) > 25 * 1024 * 1024:  # 25MB limit
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    
    # Intake the document
    doc = await engine.intake_document(
        user_id=user_id,
        file_content=content,
        filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
    )
    
    return UploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value,
        message="Document received. Use /process/{id} to begin processing.",
    )


class AutoProcessResponse(BaseModel):
    """Response for auto-processed upload."""
    id: str
    filename: str
    status: str
    doc_type: str
    message: str
    extracted_data: dict = {}
    timeline_events: int = 0
    issues_found: int = 0


@router.post("/upload/auto", response_model=AutoProcessResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
):
    """
    Upload and automatically process a document (complete pipeline).
    
    This is the recommended endpoint for the full document flow:
    1. Upload & validate
    2. OCR/text extraction (auto-detects if image/scan)
    3. Document type classification (summons, lease, notice, etc.)
    4. Data extraction (dates, amounts, parties)
    5. Timeline event creation
    6. FormData hub update
    7. Issue detection
    8. UI refresh via WebSocket
    
    Returns complete processing result in one call.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    engine = get_intake_engine()
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 25MB)")
    
    # Step 1: Intake the document
    doc = await engine.intake_document(
        user_id=user_id,
        file_content=content,
        filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
    )
    
    # Step 2: Process (extract text, classify, analyze)
    try:
        doc = await engine.process_document(doc.id)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return AutoProcessResponse(
            id=doc.id,
            filename=doc.filename,
            status="error",
            doc_type="unknown",
            message=f"Processing failed: {str(e)}",
        )
    
    # Step 3: Run full flow orchestration
    flow_result = {}
    if FLOW_AVAILABLE:
        try:
            orchestrator = DocumentFlowOrchestrator()
            flow_result = await orchestrator.process_document_complete(
                doc_id=doc.id,
                user_id=user_id,
            )
        except Exception as flow_err:
            logger.warning(f"Flow orchestration partial: {flow_err}")
    
    # Publish completion event
    await event_bus.publish(
        BusEventType.DOCUMENT_PROCESSED,
        {
            "doc_id": doc.id,
            "user_id": user_id,
            "doc_type": doc.doc_type.value if doc.doc_type else "unknown",
            "filename": doc.filename,
        },
        user_id=user_id,
    )
    
    # Build response
    extracted_data = {}
    if doc.extraction:
        extracted_data = {
            "dates": len(doc.extraction.dates) if doc.extraction.dates else 0,
            "parties": len(doc.extraction.parties) if doc.extraction.parties else 0,
            "amounts": len(doc.extraction.amounts) if doc.extraction.amounts else 0,
            "summary": doc.extraction.summary[:200] if doc.extraction.summary else "",
        }
    
    return AutoProcessResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status.value if doc.status else "complete",
        doc_type=doc.doc_type.value if doc.doc_type else "unknown",
        message="Document processed successfully",
        extracted_data=extracted_data,
        timeline_events=flow_result.get("stages", {}).get("events", {}).get("count", 0),
        issues_found=len(doc.extraction.issues) if doc.extraction and doc.extraction.issues else 0,
    )


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    files: list[UploadFile] = File(...),
    user_id: str = Form(...),
):
    """
    Upload multiple documents at once.
    
    Returns status for each file.
    """
    engine = get_intake_engine()
    
    uploaded = []
    failed = []
    
    for file in files:
        try:
            content = await file.read()
            
            if len(content) == 0:
                failed.append({"filename": file.filename, "error": "Empty file"})
                continue
            
            if len(content) > 25 * 1024 * 1024:
                failed.append({"filename": file.filename, "error": "File too large"})
                continue
            
            doc = await engine.intake_document(
                user_id=user_id,
                file_content=content,
                filename=file.filename or "unknown",
                mime_type=file.content_type or "application/octet-stream",
            )
            
            uploaded.append(UploadResponse(
                id=doc.id,
                filename=doc.filename,
                status=doc.status.value,
                message="Document received",
            ))
            
        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})
    
    return BatchUploadResponse(
        uploaded=uploaded,
        failed=failed,
        total_uploaded=len(uploaded),
        total_failed=len(failed),
    )


# =============================================================================
# PROCESSING ENDPOINTS
# =============================================================================

@router.post("/process/{doc_id}", response_model=IntakeDocumentResponse)
async def process_document(doc_id: str, user_id: str = Depends(get_user_id)):
    """
    Process an uploaded document.
    
    This runs the full pipeline:
    1. Validation
    2. Text extraction (OCR if needed)
    3. Content analysis & document type detection
    4. Issue detection
    5. Timeline event creation
    6. FormData hub update
    7. UI refresh via WebSocket
    
    Returns the complete extraction result.
    """
    engine = get_intake_engine()
    
    doc = engine.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status == IntakeStatus.COMPLETE:
        # Already processed, return existing result
        return _doc_to_response(doc)
    
    try:
        # Run basic processing first
        doc = await engine.process_document(doc_id)
        
        # Run full flow orchestration if available
        if FLOW_AVAILABLE:
            try:
                orchestrator = DocumentFlowOrchestrator()
                flow_result = await orchestrator.process_document_complete(
                    doc_id=doc_id,
                    user_id=user_id,
                )
                # Attach flow result to response
                if flow_result.get("status") == "complete":
                    await event_bus.publish(
                        BusEventType.DOCUMENT_PROCESSED,
                        {
                            "doc_id": doc_id,
                            "user_id": user_id,
                            "doc_type": doc.doc_type.value if doc.doc_type else "unknown",
                            "flow_stages": list(flow_result.get("stages", {}).keys()),
                        },
                        user_id=user_id,
                    )
            except Exception as flow_err:
                # Log but don't fail - basic processing succeeded
                import logging
                logging.getLogger(__name__).warning(f"Flow orchestration warning: {flow_err}")
        
        return _doc_to_response(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/status/{doc_id}", response_model=IntakeStatusResponse)
async def get_processing_status(doc_id: str):
    """
    Get the current processing status of a document.
    
    Use this to poll for completion during async processing.
    """
    engine = get_intake_engine()
    status = engine.get_processing_status(doc_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return IntakeStatusResponse(**status)


# =============================================================================
# RETRIEVAL ENDPOINTS
# =============================================================================

@router.get("/documents", response_model=list[IntakeDocumentResponse])
async def list_documents(
    user_id: str = Depends(get_user_id),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    List all documents for a user.
    
    Optionally filter by processing status.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    if status:
        try:
            status_filter = IntakeStatus(status)
            docs = [d for d in docs if d.status == status_filter]
        except ValueError:
            pass
    
    return [_doc_to_response(d) for d in docs]


@router.get("/documents/{doc_id}", response_model=IntakeDocumentResponse)
async def get_document(doc_id: str):
    """
    Get a specific document with all extraction results.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return _doc_to_response(doc)


@router.get("/documents/{doc_id}/issues", response_model=list[DetectedIssueResponse])
async def get_document_issues(doc_id: str):
    """
    Get only the detected issues for a document.
    
    Useful for displaying alerts/warnings to the user.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        DetectedIssueResponse(
            issue_id=i.issue_id,
            severity=i.severity.value,
            title=i.title,
            description=i.description,
            affected_text=i.affected_text,
            legal_basis=i.legal_basis,
            recommended_action=i.recommended_action,
            deadline=i.deadline.isoformat() if i.deadline else None,
            related_laws=i.related_laws,
        )
        for i in doc.extraction.issues
    ]


@router.get("/documents/{doc_id}/dates", response_model=list[ExtractedDateResponse])
async def get_document_dates(doc_id: str):
    """
    Get only the extracted dates for a document.
    
    Includes deadline detection and days-until calculation.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        ExtractedDateResponse(
            date=d.date.isoformat(),
            label=d.label,
            confidence=d.confidence,
            source_text=d.source_text,
            is_deadline=d.is_deadline,
            days_until=d.days_until,
        )
        for d in doc.extraction.dates
    ]


@router.get("/documents/{doc_id}/amounts", response_model=list[ExtractedAmountResponse])
async def get_document_amounts(doc_id: str):
    """
    Get only the extracted monetary amounts for a document.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        ExtractedAmountResponse(
            amount=a.amount,
            label=a.label,
            currency=a.currency,
            period=a.period,
            confidence=a.confidence,
            source_text=a.source_text,
        )
        for a in doc.extraction.amounts
    ]


@router.get("/documents/{doc_id}/parties", response_model=list[ExtractedPartyResponse])
async def get_document_parties(doc_id: str):
    """
    Get only the extracted parties for a document.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return [
        ExtractedPartyResponse(
            name=p.name,
            role=p.role,
            address=p.address,
            phone=p.phone,
            email=p.email,
            confidence=p.confidence,
        )
        for p in doc.extraction.parties
    ]


@router.get("/documents/{doc_id}/text")
async def get_document_text(doc_id: str):
    """
    Get the full extracted text for a document.
    """
    engine = get_intake_engine()
    doc = engine.get_document(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.extraction:
        raise HTTPException(status_code=400, detail="Document not yet processed")
    
    return {
        "id": doc_id,
        "filename": doc.filename,
        "text": doc.extraction.full_text,
        "word_count": doc.extraction.word_count,
        "language": doc.extraction.language.value,
    }


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@router.get("/issues/critical")
async def get_critical_issues(user_id: str = Depends(get_user_id)):
    """
    Get all CRITICAL issues across all user's documents.
    
    These require immediate attention.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    critical_issues = []
    for doc in docs:
        if doc.extraction:
            for issue in doc.extraction.issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    critical_issues.append({
                        "document_id": doc.id,
                        "document_name": doc.filename,
                        "issue": DetectedIssueResponse(
                            issue_id=issue.issue_id,
                            severity=issue.severity.value,
                            title=issue.title,
                            description=issue.description,
                            affected_text=issue.affected_text,
                            legal_basis=issue.legal_basis,
                            recommended_action=issue.recommended_action,
                            deadline=issue.deadline.isoformat() if issue.deadline else None,
                            related_laws=issue.related_laws,
                        ),
                    })
    
    return {
        "total_critical": len(critical_issues),
        "issues": critical_issues,
    }


@router.get("/deadlines/upcoming")
async def get_upcoming_deadlines(
    user_id: str = Depends(get_user_id),
    days: int = Query(14, description="Number of days to look ahead"),
):
    """
    Get all upcoming deadlines across user's documents.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    deadlines = []
    for doc in docs:
        if doc.extraction:
            for date in doc.extraction.dates:
                if date.is_deadline and date.days_until is not None:
                    if 0 <= date.days_until <= days:
                        deadlines.append({
                            "document_id": doc.id,
                            "document_name": doc.filename,
                            "date": date.date.isoformat(),
                            "label": date.label,
                            "days_until": date.days_until,
                            "source_text": date.source_text,
                        })
    
    # Sort by days until deadline
    deadlines.sort(key=lambda x: x["days_until"])
    
    return {
        "total_deadlines": len(deadlines),
        "deadlines": deadlines,
    }


@router.get("/summary")
async def get_user_intake_summary(user_id: str = Depends(get_user_id)):
    """
    Get a summary of all intake documents for a user.
    """
    engine = get_intake_engine()
    docs = engine.get_user_documents(user_id)
    
    by_status = {}
    by_type = {}
    total_issues = 0
    critical_issues = 0
    
    for doc in docs:
        # Count by status
        status = doc.status.value
        by_status[status] = by_status.get(status, 0) + 1
        
        # Count by type and issues
        if doc.extraction:
            doc_type = doc.extraction.doc_type.value
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
            
            total_issues += len(doc.extraction.issues)
            critical_issues += sum(
                1 for i in doc.extraction.issues 
                if i.severity == IssueSeverity.CRITICAL
            )
    
    return {
        "total_documents": len(docs),
        "by_status": by_status,
        "by_type": by_type,
        "total_issues_detected": total_issues,
        "critical_issues": critical_issues,
    }


# =============================================================================
# ENUM ENDPOINTS (for frontend)
# =============================================================================

@router.get("/enums/document-types")
async def get_document_types():
    """Get all document types."""
    return [{"value": t.value, "name": t.name} for t in DocumentType]


@router.get("/enums/intake-statuses")
async def get_intake_statuses():
    """Get all intake statuses."""
    return [{"value": s.value, "name": s.name} for s in IntakeStatus]


@router.get("/enums/issue-severities")
async def get_issue_severities():
    """Get all issue severity levels."""
    return [{"value": s.value, "name": s.name} for s in IssueSeverity]


@router.get("/enums/languages")
async def get_languages():
    """Get supported languages."""
    return [{"value": l.value, "name": l.name} for l in LanguageCode]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _doc_to_response(doc) -> IntakeDocumentResponse:
    """Convert IntakeDocument to response model."""
    extraction_response = None
    
    if doc.extraction:
        ext = doc.extraction
        extraction_response = ExtractionResultResponse(
            doc_type=ext.doc_type.value,
            doc_type_confidence=ext.doc_type_confidence,
            language=ext.language.value,
            page_count=ext.page_count,
            word_count=ext.word_count,
            summary=ext.summary,
            key_points=ext.key_points,
            dates=[
                ExtractedDateResponse(
                    date=d.date.isoformat(),
                    label=d.label,
                    confidence=d.confidence,
                    source_text=d.source_text,
                    is_deadline=d.is_deadline,
                    days_until=d.days_until,
                )
                for d in ext.dates
            ],
            parties=[
                ExtractedPartyResponse(
                    name=p.name,
                    role=p.role,
                    address=p.address,
                    phone=p.phone,
                    email=p.email,
                    confidence=p.confidence,
                )
                for p in ext.parties
            ],
            amounts=[
                ExtractedAmountResponse(
                    amount=a.amount,
                    label=a.label,
                    currency=a.currency,
                    period=a.period,
                    confidence=a.confidence,
                    source_text=a.source_text,
                )
                for a in ext.amounts
            ],
            issues=[
                DetectedIssueResponse(
                    issue_id=i.issue_id,
                    severity=i.severity.value,
                    title=i.title,
                    description=i.description,
                    affected_text=i.affected_text,
                    legal_basis=i.legal_basis,
                    recommended_action=i.recommended_action,
                    deadline=i.deadline.isoformat() if i.deadline else None,
                    related_laws=i.related_laws,
                )
                for i in ext.issues
            ],
            extracted_at=ext.extracted_at.isoformat(),
        )
    
    return IntakeDocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        file_hash=doc.file_hash,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status.value,
        status_message=doc.status_message,
        progress_percent=doc.progress_percent,
        extraction=extraction_response,
        uploaded_at=doc.uploaded_at.isoformat(),
        processed_at=doc.processed_at.isoformat() if doc.processed_at else None,
    )


# =============================================================================
# INTAKE ANALYSIS ENDPOINTS (for get_started.html)
# =============================================================================

class SituationAnalysisRequest(BaseModel):
    """Request for analyzing user situation."""
    situation_type: Optional[str] = None
    description: Optional[str] = None
    has_document: bool = False
    timestamp: Optional[str] = None


class SituationAnalysisResponse(BaseModel):
    """Response with situation analysis."""
    situation_summary: str
    document_type: Optional[str] = None
    key_dates: list[str] = []
    recommended_actions: list[str] = []
    urgency: str = "medium"
    urgency_reason: Optional[str] = None


@router.post("/analyze-situation", response_model=SituationAnalysisResponse)
async def analyze_situation(
    request: SituationAnalysisRequest,
    user_id: str = Depends(get_user_id),
):
    """
    Analyze user's described situation and provide guidance.
    Used by the get_started.html intake page.
    """
    situation_type = request.situation_type or "unknown"
    description = request.description or ""
    
    # Build situation-specific analysis
    summaries = {
        "notice": "You've received a notice from your landlord. This is often the first step in an eviction process, but you have rights and options.",
        "lease": "You have questions about your lease agreement. Understanding your lease terms is crucial to knowing your rights and obligations.",
        "repairs": "You're dealing with repair or habitability issues. Landlords have a legal duty to maintain safe and habitable conditions.",
        "other": "You're facing a tenant-related concern. Let's help you organize your situation and understand your options."
    }
    
    actions_map = {
        "notice": [
            "Read the notice carefully and note all dates",
            "Don't ignore it - even if you disagree with it",
            "Check if proper notice procedures were followed",
            "Document everything related to this notice",
            "Consider consulting with a tenant rights organization"
        ],
        "lease": [
            "Review your entire lease document",
            "Note any clauses you don't understand",
            "Check for any potentially illegal provisions",
            "Keep a copy of the signed lease in a safe place",
            "Document any violations by either party"
        ],
        "repairs": [
            "Document the repair issues with photos and dates",
            "Send written repair requests to your landlord",
            "Keep copies of all communications",
            "Know your rights to habitability under MN law",
            "Consider rent escrow if repairs aren't made"
        ],
        "other": [
            "Document your concerns in writing",
            "Gather any related documents or evidence",
            "Keep records of all communications with landlord",
            "Research your specific rights under MN tenant law",
            "Consider seeking legal advice if needed"
        ]
    }
    
    urgency_map = {
        "notice": ("high", "Notices often have strict deadlines. Acting quickly is important."),
        "lease": ("low", "Lease questions are important but usually not urgent unless facing immediate action."),
        "repairs": ("medium", "Repair issues should be addressed promptly, especially if affecting habitability."),
        "other": ("medium", "Priority depends on your specific situation.")
    }
    
    summary = summaries.get(situation_type, summaries["other"])
    
    # If user provided description, personalize the response
    if description:
        if len(description) > 50:
            summary += f" Based on what you've shared, we can help you organize the details and determine your best course of action."
    
    actions = actions_map.get(situation_type, actions_map["other"])
    urgency, urgency_reason = urgency_map.get(situation_type, urgency_map["other"])
    
    # Detect potential urgency from description
    urgent_keywords = ["tomorrow", "eviction", "lockout", "court date", "emergency", "today", "asap", "immediately"]
    if description and any(kw in description.lower() for kw in urgent_keywords):
        urgency = "high"
        urgency_reason = "Your situation may be time-sensitive. Please review deadlines carefully."
    
    return SituationAnalysisResponse(
        situation_summary=summary,
        document_type=f"{situation_type}_related" if situation_type != "unknown" else None,
        key_dates=[],  # Would be extracted from description with NLP
        recommended_actions=actions,
        urgency=urgency,
        urgency_reason=urgency_reason
    )


@router.post("/analyze-document", response_model=SituationAnalysisResponse)
async def analyze_document_for_intake(
    file: UploadFile = File(...),
    situation_type: str = Form(None),
    description: str = Form(None),
    user_id: str = Depends(get_user_id),
):
    """
    Analyze an uploaded document for the intake process.
    Used by the get_started.html intake page.
    """
    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"
    
    # Detect document type from filename
    doc_type = "unknown"
    if any(kw in filename.lower() for kw in ["notice", "eviction", "quit"]):
        doc_type = "notice"
    elif any(kw in filename.lower() for kw in ["lease", "rental", "agreement"]):
        doc_type = "lease"
    elif any(kw in filename.lower() for kw in ["repair", "maintenance", "fix"]):
        doc_type = "repair_request"
    elif any(kw in filename.lower() for kw in ["complaint", "violation"]):
        doc_type = "complaint"
    
    # Use situation_type if provided
    if situation_type and situation_type != "unknown":
        doc_type = situation_type
    
    # Build analysis based on document type
    type_labels = {
        "notice": "Landlord Notice / Eviction Document",
        "lease": "Lease Agreement / Rental Contract", 
        "repair_request": "Repair Request / Maintenance Issue",
        "complaint": "Complaint / Violation Notice",
        "unknown": "General Document"
    }
    
    summaries = {
        "notice": f"We received your document '{filename}'. This appears to be a notice from your landlord. It's important to review this carefully and note any deadlines mentioned.",
        "lease": f"We received your lease document '{filename}'. We can help you understand the key terms and identify any provisions to be aware of.",
        "repair_request": f"We received your repair-related document '{filename}'. Documenting repair issues is important for protecting your rights.",
        "complaint": f"We received your complaint document '{filename}'. We'll help you track this and understand your options.",
        "unknown": f"We received your document '{filename}'. We'll help you organize it and determine how it relates to your situation."
    }
    
    actions_by_type = {
        "notice": [
            "Check the notice date and any response deadlines",
            "Verify the notice was properly served",
            "Review the stated reason for the notice",
            "Determine if you have grounds to contest",
            "Add this document to your case timeline"
        ],
        "lease": [
            "Note the lease term start and end dates",
            "Review rent amount and due date",
            "Check rules about security deposits",
            "Look for any unusual or potentially illegal clauses",
            "Save this lease in your document vault"
        ],
        "repair_request": [
            "Document the date you reported the issue",
            "Keep evidence of the repair problem (photos)",
            "Track landlord's response or lack thereof",
            "Know your rights if repairs aren't made",
            "Add to timeline for tracking"
        ],
        "complaint": [
            "Review the complaint details carefully",
            "Gather evidence to support or refute claims",
            "Note any deadlines for response",
            "Document your side of the situation",
            "Consider if legal assistance is needed"
        ],
        "unknown": [
            "Review the document contents",
            "Identify how it relates to your tenancy",
            "Store it securely in your document vault",
            "Add relevant events to your timeline",
            "Consult with an advocate if unclear"
        ]
    }
    
    urgency = "medium"
    urgency_reason = "Review your document carefully and note any time-sensitive items."
    
    if doc_type == "notice":
        urgency = "high"
        urgency_reason = "Notices often have strict deadlines. Check all dates immediately."
    
    return SituationAnalysisResponse(
        situation_summary=summaries.get(doc_type, summaries["unknown"]),
        document_type=type_labels.get(doc_type, "Document"),
        key_dates=[],  # Would be extracted with document parsing
        recommended_actions=actions_by_type.get(doc_type, actions_by_type["unknown"]),
        urgency=urgency,
        urgency_reason=urgency_reason
    )
