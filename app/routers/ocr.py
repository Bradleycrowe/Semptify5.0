"""
🔥 OCR API Router
==================
REST API endpoints for the world-class OCR engine.
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import base64
import logging

from app.services.ocr_engine import (
    get_ocr_engine,
    ocr_image,
    ProcessingQuality,
    DocumentLayout,
    OCRResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ocr", tags=["OCR Engine"])


# =============================================================================
# Request/Response Models
# =============================================================================

class OCRTextRequest(BaseModel):
    """Request to OCR a base64 encoded image."""
    image_base64: str = Field(..., description="Base64 encoded image data")
    quality: str = Field("balanced", description="Processing quality: fast, balanced, best, legal")
    layout_hint: Optional[str] = Field(None, description="Document layout hint")
    filename: Optional[str] = Field(None, description="Original filename for context")
    extract_entities: bool = Field(True, description="Extract structured entities")


class OCRURLRequest(BaseModel):
    """Request to OCR an image from URL."""
    url: str = Field(..., description="URL of image to process")
    quality: str = Field("balanced", description="Processing quality")
    layout_hint: Optional[str] = Field(None, description="Document layout hint")


class EntityResponse(BaseModel):
    """Extracted entity."""
    type: str
    value: str
    confidence: float


class BlockResponse(BaseModel):
    """Text block."""
    text: str
    confidence: float
    type: str


class OCRResponse(BaseModel):
    """OCR result response."""
    success: bool
    text: str
    blocks: List[BlockResponse] = []
    entities: List[EntityResponse] = []
    confidence: float
    engine: str
    processing_time_ms: float
    pages: int
    language: str
    layout: str
    has_handwriting: bool
    warnings: List[str] = []


class QuickOCRResponse(BaseModel):
    """Simplified OCR response."""
    text: str
    confidence: float
    entities: Dict[str, List[str]]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/analyze", response_model=OCRResponse)
async def analyze_image(
    file: UploadFile = File(...),
    quality: str = Form("balanced"),
    layout_hint: Optional[str] = Form(None),
    extract_entities: bool = Form(True)
):
    """
    🔥 World-Class OCR Analysis
    
    Upload an image for OCR processing with our advanced multi-engine system.
    
    **Quality Levels:**
    - `fast`: Single engine, minimal preprocessing (~1-2s)
    - `balanced`: Primary engine with validation (~2-4s)  
    - `best`: Full ensemble with all preprocessing (~5-10s)
    - `legal`: Optimized for legal documents (~5-10s)
    
    **Layout Hints:**
    - `printed`: Standard printed text
    - `handwritten`: Handwritten content
    - `form`: Forms with fields
    - `table`: Tabular data
    - `legal`: Legal documents
    - `receipt`: Receipts/invoices
    """
    try:
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")
        
        # Map quality string
        quality_map = {
            "fast": ProcessingQuality.FAST,
            "balanced": ProcessingQuality.BALANCED,
            "best": ProcessingQuality.BEST,
            "legal": ProcessingQuality.LEGAL
        }
        proc_quality = quality_map.get(quality.lower(), ProcessingQuality.BALANCED)
        
        # Map layout hint
        layout_map = {
            "printed": DocumentLayout.PRINTED_TEXT,
            "handwritten": DocumentLayout.HANDWRITTEN,
            "mixed": DocumentLayout.MIXED,
            "form": DocumentLayout.FORM,
            "table": DocumentLayout.TABLE,
            "legal": DocumentLayout.LEGAL,
            "receipt": DocumentLayout.RECEIPT,
            "id": DocumentLayout.ID_DOCUMENT
        }
        doc_layout = layout_map.get(layout_hint.lower() if layout_hint else "", None)
        
        # Process
        engine = get_ocr_engine()
        result = await engine.recognize(
            image_data=content,
            quality=proc_quality,
            layout_hint=doc_layout,
            extract_entities=extract_entities,
            filename=file.filename
        )
        
        return OCRResponse(
            success=True,
            text=result.text,
            blocks=[BlockResponse(text=b.text, confidence=b.confidence, type=b.block_type) for b in result.blocks],
            entities=[EntityResponse(type=e.entity_type, value=e.value, confidence=e.confidence) for e in result.entities],
            confidence=result.confidence,
            engine=result.engine_used,
            processing_time_ms=result.processing_time_ms,
            pages=result.page_count,
            language=result.language,
            layout=result.layout_type.value,
            has_handwriting=result.has_handwriting,
            warnings=result.warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.post("/analyze-base64", response_model=OCRResponse)
async def analyze_base64(request: OCRTextRequest):
    """
    OCR analysis from base64 encoded image.
    Useful for browser-based uploads.
    """
    try:
        # Decode base64
        try:
            # Handle data URL format
            if ',' in request.image_base64:
                image_data = base64.b64decode(request.image_base64.split(',')[1])
            else:
                image_data = base64.b64decode(request.image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Map quality
        quality_map = {
            "fast": ProcessingQuality.FAST,
            "balanced": ProcessingQuality.BALANCED,
            "best": ProcessingQuality.BEST,
            "legal": ProcessingQuality.LEGAL
        }
        proc_quality = quality_map.get(request.quality.lower(), ProcessingQuality.BALANCED)
        
        # Map layout hint
        layout_map = {
            "printed": DocumentLayout.PRINTED_TEXT,
            "handwritten": DocumentLayout.HANDWRITTEN,
            "form": DocumentLayout.FORM,
            "table": DocumentLayout.TABLE,
            "legal": DocumentLayout.LEGAL,
            "receipt": DocumentLayout.RECEIPT
        }
        doc_layout = layout_map.get(request.layout_hint.lower() if request.layout_hint else "", None)
        
        # Process
        engine = get_ocr_engine()
        result = await engine.recognize(
            image_data=image_data,
            quality=proc_quality,
            layout_hint=doc_layout,
            extract_entities=request.extract_entities,
            filename=request.filename
        )
        
        return OCRResponse(
            success=True,
            text=result.text,
            blocks=[BlockResponse(text=b.text, confidence=b.confidence, type=b.block_type) for b in result.blocks],
            entities=[EntityResponse(type=e.entity_type, value=e.value, confidence=e.confidence) for e in result.entities],
            confidence=result.confidence,
            engine=result.engine_used,
            processing_time_ms=result.processing_time_ms,
            pages=result.page_count,
            language=result.language,
            layout=result.layout_type.value,
            has_handwriting=result.has_handwriting,
            warnings=result.warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR base64 analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.post("/quick", response_model=QuickOCRResponse)
async def quick_ocr(
    file: UploadFile = File(...)
):
    """
    Quick OCR - Fast text extraction with minimal processing.
    Returns text and grouped entities only.
    """
    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        engine = get_ocr_engine()
        result = await engine.recognize(
            image_data=content,
            quality=ProcessingQuality.FAST,
            extract_entities=True,
            filename=file.filename
        )
        
        # Group entities by type
        entities_grouped: Dict[str, List[str]] = {}
        for entity in result.entities:
            if entity.entity_type not in entities_grouped:
                entities_grouped[entity.entity_type] = []
            entities_grouped[entity.entity_type].append(entity.value)
        
        return QuickOCRResponse(
            text=result.text,
            confidence=result.confidence,
            entities=entities_grouped
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick OCR failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@router.post("/extract-text")
async def extract_text_only(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Extract text only - simplest endpoint.
    Returns just the extracted text string.
    """
    try:
        content = await file.read()
        
        engine = get_ocr_engine()
        result = await engine.recognize(
            image_data=content,
            quality=ProcessingQuality.BALANCED,
            extract_entities=False,
            filename=file.filename
        )
        
        return {
            "text": result.text,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")


@router.get("/health")
async def ocr_health():
    """Check OCR engine health and available backends."""
    engine = get_ocr_engine()
    
    backends = {
        "tesseract": engine.tesseract_ocr._available,
        "azure_document": bool(engine.azure_ocr.endpoint and engine.azure_ocr.key),
        "preprocessing": engine.preprocessor._pil_available
    }
    
    return {
        "status": "healthy" if any(backends.values()) else "degraded",
        "backends": backends,
        "recommended_quality": "best" if backends.get("azure_document") else "balanced"
    }
