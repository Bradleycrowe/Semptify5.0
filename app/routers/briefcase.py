"""
Briefcase Router - Document & Folder Organization System
A digital briefcase for organizing legal documents, evidence, and case files
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import os
import io
import json
import shutil
import hashlib
import base64
import zipfile
import uuid

router = APIRouter(prefix="/api/briefcase", tags=["Briefcase"])

# In-memory storage (in production, use database)
briefcase_data = {
    "folders": {
        "root": {
            "id": "root",
            "name": "My Briefcase",
            "parent_id": None,
            "created_at": datetime.now().isoformat(),
            "color": "#4ade80",
            "icon": "briefcase"
        },
        "extracted": {
            "id": "extracted",
            "name": "📄 Extracted Pages",
            "parent_id": "root",
            "created_at": datetime.now().isoformat(),
            "color": "#f59e0b",
            "icon": "file-export",
            "system": True
        },
        "highlights": {
            "id": "highlights",
            "name": "🖍️ Highlights & Notes",
            "parent_id": "root",
            "created_at": datetime.now().isoformat(),
            "color": "#ec4899",
            "icon": "highlighter",
            "system": True
        },
        "evidence": {
            "id": "evidence",
            "name": "📸 Evidence",
            "parent_id": "root",
            "created_at": datetime.now().isoformat(),
            "color": "#ef4444",
            "icon": "gavel",
            "system": True
        }
    },
    "documents": {},
    "extractions": {},  # Store extracted PDF pages
    "highlights": {},   # Store highlights and notes
    "tags": ["Important", "Evidence", "Lease", "Notice", "Court", "Correspondence", "Financial", "Photos"]
}

# Pydantic models
class FolderCreate(BaseModel):
    name: str
    parent_id: str = "root"
    color: Optional[str] = "#3b82f6"
    icon: Optional[str] = "folder"

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None

class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    starred: Optional[bool] = None


@router.get("/")
async def get_briefcase():
    """Get entire briefcase structure"""
    return {
        "folders": list(briefcase_data["folders"].values()),
        "documents": list(briefcase_data["documents"].values()),
        "tags": briefcase_data["tags"],
        "stats": {
            "total_folders": len(briefcase_data["folders"]),
            "total_documents": len(briefcase_data["documents"]),
            "total_size": sum(d.get("size", 0) for d in briefcase_data["documents"].values())
        }
    }


@router.get("/folder/{folder_id}")
async def get_folder_contents(folder_id: str):
    """Get contents of a specific folder"""
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder = briefcase_data["folders"][folder_id]
    
    # Get subfolders
    subfolders = [f for f in briefcase_data["folders"].values() if f.get("parent_id") == folder_id]
    
    # Get documents in this folder
    documents = [d for d in briefcase_data["documents"].values() if d.get("folder_id") == folder_id]
    
    # Get breadcrumb path
    breadcrumb = get_breadcrumb(folder_id)
    
    return {
        "folder": folder,
        "subfolders": subfolders,
        "documents": documents,
        "breadcrumb": breadcrumb
    }


def get_breadcrumb(folder_id: str) -> List[Dict]:
    """Build breadcrumb path from root to folder"""
    breadcrumb = []
    current_id = folder_id
    
    while current_id:
        if current_id in briefcase_data["folders"]:
            folder = briefcase_data["folders"][current_id]
            breadcrumb.insert(0, {"id": folder["id"], "name": folder["name"]})
            current_id = folder.get("parent_id")
        else:
            break
    
    return breadcrumb


@router.post("/folder")
async def create_folder(folder: FolderCreate):
    """Create a new folder"""
    if folder.parent_id != "root" and folder.parent_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Parent folder not found")
    
    folder_id = f"folder_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(folder.name) & 0xFFFF:04x}"
    
    new_folder = {
        "id": folder_id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "color": folder.color,
        "icon": folder.icon,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    briefcase_data["folders"][folder_id] = new_folder
    
    return {"success": True, "folder": new_folder}


@router.put("/folder/{folder_id}")
async def update_folder(folder_id: str, update: FolderUpdate):
    """Update folder properties"""
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if folder_id == "root":
        raise HTTPException(status_code=400, detail="Cannot modify root folder")
    
    folder = briefcase_data["folders"][folder_id]
    
    if update.name is not None:
        folder["name"] = update.name
    if update.color is not None:
        folder["color"] = update.color
    if update.icon is not None:
        folder["icon"] = update.icon
    if update.parent_id is not None:
        # Prevent moving to own child
        if not is_valid_move(folder_id, update.parent_id):
            raise HTTPException(status_code=400, detail="Cannot move folder to its own subfolder")
        folder["parent_id"] = update.parent_id
    
    folder["updated_at"] = datetime.now().isoformat()
    
    return {"success": True, "folder": folder}


def is_valid_move(folder_id: str, new_parent_id: str) -> bool:
    """Check if moving folder to new parent is valid (not circular)"""
    if new_parent_id == folder_id:
        return False
    
    current_id = new_parent_id
    while current_id:
        if current_id == folder_id:
            return False
        if current_id in briefcase_data["folders"]:
            current_id = briefcase_data["folders"][current_id].get("parent_id")
        else:
            break
    
    return True


@router.delete("/folder/{folder_id}")
async def delete_folder(folder_id: str, recursive: bool = False):
    """Delete a folder"""
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if folder_id == "root":
        raise HTTPException(status_code=400, detail="Cannot delete root folder")
    
    # Check for contents
    subfolders = [f for f in briefcase_data["folders"].values() if f.get("parent_id") == folder_id]
    documents = [d for d in briefcase_data["documents"].values() if d.get("folder_id") == folder_id]
    
    if (subfolders or documents) and not recursive:
        raise HTTPException(
            status_code=400, 
            detail=f"Folder contains {len(subfolders)} folders and {len(documents)} documents. Use recursive=true to delete all."
        )
    
    # Recursive delete
    if recursive:
        delete_folder_recursive(folder_id)
    else:
        del briefcase_data["folders"][folder_id]
    
    return {"success": True, "message": "Folder deleted"}


def delete_folder_recursive(folder_id: str):
    """Recursively delete folder and contents"""
    # Delete subfolders
    subfolders = [f["id"] for f in briefcase_data["folders"].values() if f.get("parent_id") == folder_id]
    for subfolder_id in subfolders:
        delete_folder_recursive(subfolder_id)
    
    # Delete documents
    doc_ids = [d["id"] for d in briefcase_data["documents"].values() if d.get("folder_id") == folder_id]
    for doc_id in doc_ids:
        del briefcase_data["documents"][doc_id]
    
    # Delete folder
    if folder_id in briefcase_data["folders"]:
        del briefcase_data["folders"][folder_id]


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    folder_id: str = Form(default="root"),
    tags: str = Form(default=""),
    notes: str = Form(default="")
):
    """Upload a document to the briefcase"""
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    content = await file.read()
    
    # Generate document ID and hash
    doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) & 0xFFFFFF:06x}"
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    
    # Determine file type
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    file_type = get_file_type(ext)
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Store document
    document = {
        "id": doc_id,
        "name": filename,
        "folder_id": folder_id,
        "size": len(content),
        "type": file_type,
        "extension": ext,
        "mime_type": file.content_type,
        "hash": file_hash,
        "tags": tag_list,
        "notes": notes,
        "starred": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "content": base64.b64encode(content).decode('utf-8')
    }
    
    briefcase_data["documents"][doc_id] = document
    
    # Return without content
    doc_response = {k: v for k, v in document.items() if k != "content"}
    
    return {"success": True, "document": doc_response}


def get_file_type(ext: str) -> str:
    """Determine file type category from extension"""
    types = {
        ".pdf": "pdf",
        ".doc": "word", ".docx": "word",
        ".xls": "excel", ".xlsx": "excel",
        ".ppt": "powerpoint", ".pptx": "powerpoint",
        ".txt": "text", ".md": "text", ".rtf": "text",
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image", ".webp": "image",
        ".mp3": "audio", ".wav": "audio", ".m4a": "audio",
        ".mp4": "video", ".mov": "video", ".avi": "video",
        ".zip": "archive", ".rar": "archive", ".7z": "archive",
        ".html": "web", ".htm": "web",
        ".json": "data", ".xml": "data", ".csv": "data"
    }
    return types.get(ext, "other")


@router.get("/document/{doc_id}")
async def get_document(doc_id: str):
    """Get document metadata"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = briefcase_data["documents"][doc_id]
    # Return without content
    return {k: v for k, v in doc.items() if k != "content"}


@router.get("/document/{doc_id}/download")
async def download_document(doc_id: str):
    """Download a document"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = briefcase_data["documents"][doc_id]
    content = base64.b64decode(doc["content"])
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=doc.get("mime_type", "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename={doc['name']}"}
    )


@router.get("/document/{doc_id}/preview")
async def preview_document(doc_id: str):
    """Get document content for preview (base64)"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = briefcase_data["documents"][doc_id]
    
    return {
        "id": doc_id,
        "name": doc["name"],
        "type": doc["type"],
        "mime_type": doc.get("mime_type"),
        "content": f"data:{doc.get('mime_type', 'application/octet-stream')};base64,{doc['content']}"
    }


@router.put("/document/{doc_id}")
async def update_document(doc_id: str, update: DocumentUpdate):
    """Update document properties"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = briefcase_data["documents"][doc_id]
    
    if update.name is not None:
        doc["name"] = update.name
    if update.folder_id is not None:
        if update.folder_id not in briefcase_data["folders"]:
            raise HTTPException(status_code=404, detail="Target folder not found")
        doc["folder_id"] = update.folder_id
    if update.tags is not None:
        doc["tags"] = update.tags
    if update.notes is not None:
        doc["notes"] = update.notes
    if update.starred is not None:
        doc["starred"] = update.starred
    
    doc["updated_at"] = datetime.now().isoformat()
    
    return {"success": True, "document": {k: v for k, v in doc.items() if k != "content"}}


@router.delete("/document/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del briefcase_data["documents"][doc_id]
    
    return {"success": True, "message": "Document deleted"}


@router.post("/document/{doc_id}/move")
async def move_document(doc_id: str, folder_id: str = Form(...)):
    """Move document to another folder"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Target folder not found")
    
    briefcase_data["documents"][doc_id]["folder_id"] = folder_id
    briefcase_data["documents"][doc_id]["updated_at"] = datetime.now().isoformat()
    
    return {"success": True, "message": "Document moved"}


@router.post("/document/{doc_id}/copy")
async def copy_document(doc_id: str, folder_id: str = Form(...)):
    """Copy document to another folder"""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Target folder not found")
    
    original = briefcase_data["documents"][doc_id]
    new_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(original['name']) & 0xFFFF:04x}"
    
    copy = original.copy()
    copy["id"] = new_id
    copy["folder_id"] = folder_id
    copy["name"] = f"Copy of {original['name']}"
    copy["created_at"] = datetime.now().isoformat()
    copy["updated_at"] = datetime.now().isoformat()
    
    briefcase_data["documents"][new_id] = copy
    
    return {"success": True, "document": {k: v for k, v in copy.items() if k != "content"}}


@router.get("/search")
async def search_documents(
    q: str,
    folder_id: Optional[str] = None,
    tags: Optional[str] = None,
    file_type: Optional[str] = None,
    starred: Optional[bool] = None
):
    """Search documents"""
    results = []
    query = q.lower()
    tag_filter = [t.strip() for t in tags.split(",")] if tags else []
    
    for doc in briefcase_data["documents"].values():
        # Text search
        if query:
            name_match = query in doc["name"].lower()
            notes_match = query in doc.get("notes", "").lower()
            tag_match = any(query in t.lower() for t in doc.get("tags", []))
            if not (name_match or notes_match or tag_match):
                continue
        
        # Folder filter
        if folder_id and doc["folder_id"] != folder_id:
            continue
        
        # Tag filter
        if tag_filter:
            if not any(t in doc.get("tags", []) for t in tag_filter):
                continue
        
        # File type filter
        if file_type and doc["type"] != file_type:
            continue
        
        # Starred filter
        if starred is not None and doc.get("starred") != starred:
            continue
        
        results.append({k: v for k, v in doc.items() if k != "content"})
    
    return {"results": results, "count": len(results)}


@router.get("/starred")
async def get_starred_documents():
    """Get all starred documents"""
    starred = [
        {k: v for k, v in doc.items() if k != "content"}
        for doc in briefcase_data["documents"].values()
        if doc.get("starred")
    ]
    return {"documents": starred, "count": len(starred)}


@router.get("/recent")
async def get_recent_documents(limit: int = 10):
    """Get recently added/updated documents"""
    docs = list(briefcase_data["documents"].values())
    docs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    recent = [
        {k: v for k, v in doc.items() if k != "content"}
        for doc in docs[:limit]
    ]
    return {"documents": recent, "count": len(recent)}


@router.get("/tags")
async def get_all_tags():
    """Get all available tags"""
    # Get predefined tags plus any custom tags used
    all_tags = set(briefcase_data["tags"])
    for doc in briefcase_data["documents"].values():
        all_tags.update(doc.get("tags", []))
    
    return {"tags": sorted(list(all_tags))}


@router.post("/tags")
async def add_tag(tag: str = Form(...)):
    """Add a new tag"""
    if tag not in briefcase_data["tags"]:
        briefcase_data["tags"].append(tag)
    return {"success": True, "tags": briefcase_data["tags"]}


@router.post("/export")
async def export_folder(folder_id: str = Form(default="root")):
    """Export folder as ZIP file"""
    if folder_id not in briefcase_data["folders"]:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        export_folder_to_zip(zip_file, folder_id, "")
    
    zip_buffer.seek(0)
    folder_name = briefcase_data["folders"][folder_id]["name"]
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={folder_name}.zip"}
    )


def export_folder_to_zip(zip_file: zipfile.ZipFile, folder_id: str, path: str):
    """Recursively add folder contents to ZIP"""
    folder = briefcase_data["folders"][folder_id]
    folder_path = os.path.join(path, folder["name"]) if path else folder["name"]
    
    # Add documents
    for doc in briefcase_data["documents"].values():
        if doc["folder_id"] == folder_id:
            content = base64.b64decode(doc["content"])
            zip_file.writestr(os.path.join(folder_path, doc["name"]), content)
    
    # Add subfolders
    for subfolder in briefcase_data["folders"].values():
        if subfolder.get("parent_id") == folder_id:
            export_folder_to_zip(zip_file, subfolder["id"], folder_path)


@router.get("/stats")
async def get_briefcase_stats():
    """Get detailed briefcase statistics"""
    docs = list(briefcase_data["documents"].values())

    # Type distribution
    type_counts = {}
    for doc in docs:
        t = doc["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    # Tag distribution
    tag_counts = {}
    for doc in docs:
        for tag in doc.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Folder sizes
    folder_sizes = {}
    for doc in docs:
        fid = doc["folder_id"]
        folder_sizes[fid] = folder_sizes.get(fid, 0) + doc.get("size", 0)

    return {
        "total_folders": len(briefcase_data["folders"]),
        "total_documents": len(docs),
        "total_size": sum(d.get("size", 0) for d in docs),
        "starred_count": sum(1 for d in docs if d.get("starred")),
        "type_distribution": type_counts,
        "tag_distribution": tag_counts,
        "folder_sizes": folder_sizes,
        "extractions_count": len(briefcase_data.get("extractions", {})),
        "highlights_count": len(briefcase_data.get("highlights", {}))
    }


# ============ Extracted Pages Storage ============

@router.post("/extraction")
async def save_extraction(
    pdf_name: str = Form(...),
    pages: str = Form(...),  # JSON array of page numbers
    extracted_data: UploadFile = File(None),  # Optional: the actual extracted PDF
    notes: str = Form("")
):
    """Save extracted pages from PDF tools."""
    import json
    
    extraction_id = str(uuid.uuid4())
    page_list = json.loads(pages)
    
    extraction = {
        "id": extraction_id,
        "pdf_name": pdf_name,
        "pages": page_list,
        "page_count": len(page_list),
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "folder_id": "extracted"
    }
    
    # Save extracted PDF file if provided
    if extracted_data:
        upload_dir = Path("uploads/briefcase/extractions")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{extraction_id}.pdf"
        content = await extracted_data.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        extraction["file_path"] = str(file_path)
        extraction["file_size"] = len(content)
    
    briefcase_data["extractions"][extraction_id] = extraction
    
    return {"success": True, "extraction_id": extraction_id, "extraction": extraction}


@router.get("/extractions")
async def list_extractions():
    """List all saved extractions."""
    extractions = list(briefcase_data.get("extractions", {}).values())
    extractions.sort(key=lambda x: x["created_at"], reverse=True)
    return {"extractions": extractions}


@router.get("/extraction/{extraction_id}")
async def get_extraction(extraction_id: str):
    """Get a specific extraction."""
    if extraction_id not in briefcase_data.get("extractions", {}):
        raise HTTPException(status_code=404, detail="Extraction not found")
    return briefcase_data["extractions"][extraction_id]


@router.delete("/extraction/{extraction_id}")
async def delete_extraction(extraction_id: str):
    """Delete an extraction."""
    if extraction_id not in briefcase_data.get("extractions", {}):
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    extraction = briefcase_data["extractions"][extraction_id]
    
    # Delete file if exists
    if "file_path" in extraction:
        file_path = Path(extraction["file_path"])
        if file_path.exists():
            file_path.unlink()
    
    del briefcase_data["extractions"][extraction_id]
    return {"success": True}


@router.get("/extraction/{extraction_id}/download")
async def download_extraction(extraction_id: str):
    """Download extracted PDF file."""
    if extraction_id not in briefcase_data.get("extractions", {}):
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    extraction = briefcase_data["extractions"][extraction_id]
    if "file_path" not in extraction:
        raise HTTPException(status_code=404, detail="No file associated with this extraction")
    
    file_path = Path(extraction["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"extracted_{extraction['pdf_name']}_pages.pdf"
    )


# ============ Highlights & Notes Storage ============

@router.post("/highlight")
async def save_highlight(
    pdf_name: str = Form(...),
    page_number: int = Form(...),
    color: str = Form(...),
    color_name: str = Form(""),
    text: str = Form(""),
    note: str = Form(""),
    coords: str = Form(None)  # JSON with x, y, width, height
):
    """Save a highlight/annotation from PDF tools."""
    import json
    
    highlight_id = str(uuid.uuid4())
    
    highlight = {
        "id": highlight_id,
        "pdf_name": pdf_name,
        "page_number": page_number,
        "color": color,
        "color_name": color_name,
        "text": text,
        "note": note,
        "coords": json.loads(coords) if coords else None,
        "created_at": datetime.now().isoformat(),
        "folder_id": "highlights"
    }
    
    briefcase_data["highlights"][highlight_id] = highlight
    
    return {"success": True, "highlight_id": highlight_id, "highlight": highlight}


@router.post("/highlights/batch")
async def save_highlights_batch(request: Request):
    """Save multiple highlights at once."""
    data = await request.json()
    highlights = data.get("highlights", [])
    pdf_name = data.get("pdf_name", "Unknown PDF")
    
    saved = []
    for h in highlights:
        highlight_id = str(uuid.uuid4())
        highlight = {
            "id": highlight_id,
            "pdf_name": pdf_name,
            "page_number": h.get("page", 1),
            "color": h.get("color", "#ffff00"),
            "color_name": h.get("colorName", ""),
            "text": h.get("text", ""),
            "note": h.get("note", ""),
            "coords": h.get("coords"),
            "created_at": datetime.now().isoformat(),
            "folder_id": "highlights"
        }
        briefcase_data["highlights"][highlight_id] = highlight
        saved.append(highlight)
    
    return {"success": True, "count": len(saved), "highlights": saved}


@router.get("/highlights")
async def list_highlights(pdf_name: Optional[str] = None, color: Optional[str] = None):
    """List all saved highlights, optionally filtered."""
    highlights = list(briefcase_data.get("highlights", {}).values())
    
    if pdf_name:
        highlights = [h for h in highlights if h["pdf_name"] == pdf_name]
    if color:
        highlights = [h for h in highlights if h["color"] == color]
    
    highlights.sort(key=lambda x: x["created_at"], reverse=True)
    return {"highlights": highlights}


@router.get("/highlight/{highlight_id}")
async def get_highlight(highlight_id: str):
    """Get a specific highlight."""
    if highlight_id not in briefcase_data.get("highlights", {}):
        raise HTTPException(status_code=404, detail="Highlight not found")
    return briefcase_data["highlights"][highlight_id]


@router.delete("/highlight/{highlight_id}")
async def delete_highlight(highlight_id: str):
    """Delete a highlight."""
    if highlight_id not in briefcase_data.get("highlights", {}):
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    del briefcase_data["highlights"][highlight_id]
    return {"success": True}


@router.get("/highlights/by-color")
async def get_highlights_grouped_by_color():
    """Get highlights grouped by color category."""
    color_groups = {}
    
    for highlight in briefcase_data.get("highlights", {}).values():
        color = highlight.get("color_name") or highlight.get("color", "Unknown")
        if color not in color_groups:
            color_groups[color] = []
        color_groups[color].append(highlight)
    
    return {"groups": color_groups}


# =============================================================================
# ANNOTATION & FOOTNOTE SYSTEM
# Index highlights with footnote numbers, link to timeline events
# =============================================================================

# In-memory annotation storage (in production, use DocumentAnnotation model)
annotations_data = {
    "annotations": {},
    "footnote_counters": {},  # Per-document counters: {doc_id: {global: N, DT: N, PT: N, ...}}
}


class AnnotationCreate(BaseModel):
    """Create a new annotation with footnote numbering."""
    document_id: str
    extraction_code: str  # DT, PT, $, AD, LG, NT, FM, EV, DL, WS, VL, ED, QT, TL
    highlight_text: str
    page_number: int = 1
    position_x: float = 0.0
    position_y: float = 0.0
    position_width: float = 0.0
    position_height: float = 0.0
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    annotation_note: Optional[str] = None
    detection_method: str = "manual"  # pattern, ai, context, keyword, manual
    confidence: float = 1.0
    linked_event_id: Optional[str] = None  # Link to timeline event


class AnnotationUpdate(BaseModel):
    """Update an existing annotation."""
    annotation_note: Optional[str] = None
    linked_event_id: Optional[str] = None
    is_verified: Optional[bool] = None


class TimelineEventLink(BaseModel):
    """Link annotation to a timeline event."""
    annotation_id: str
    event_id: str
    event_status: Optional[str] = "pending"  # start, continued, finish, reported, etc.


def get_footnote_counters(document_id: str) -> dict:
    """Get or create footnote counters for a document."""
    if document_id not in annotations_data["footnote_counters"]:
        annotations_data["footnote_counters"][document_id] = {
            "global": 0,
            "DT": 0, "PT": 0, "$": 0, "AD": 0, "LG": 0, "NT": 0, "FM": 0, "EV": 0,
            "DL": 0, "WS": 0, "VL": 0, "ED": 0, "QT": 0, "TL": 0
        }
    return annotations_data["footnote_counters"][document_id]


@router.post("/annotations")
async def create_annotation(annotation: AnnotationCreate):
    """
    Create a new annotation with automatic footnote numbering.
    Returns both global (1, 2, 3...) and category (DT-1, PT-1...) numbers.
    """
    counters = get_footnote_counters(annotation.document_id)
    
    # Increment counters
    counters["global"] += 1
    code = annotation.extraction_code
    if code in counters:
        counters[code] += 1
    else:
        counters[code] = 1
    
    annotation_id = f"ann_{uuid.uuid4().hex[:12]}"
    
    new_annotation = {
        "id": annotation_id,
        "document_id": annotation.document_id,
        "footnote_number": counters["global"],
        "category_number": counters[code],
        "extraction_code": code,
        "extraction_id": f"{code}-{counters[code]}",  # e.g., "DT-3"
        "highlight_text": annotation.highlight_text,
        "context_before": annotation.context_before,
        "context_after": annotation.context_after,
        "annotation_note": annotation.annotation_note,
        "page_number": annotation.page_number,
        "position_x": annotation.position_x,
        "position_y": annotation.position_y,
        "position_width": annotation.position_width,
        "position_height": annotation.position_height,
        "detection_method": annotation.detection_method,
        "confidence": annotation.confidence,
        "linked_event_id": annotation.linked_event_id,
        "is_verified": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    annotations_data["annotations"][annotation_id] = new_annotation
    
    return {
        "success": True,
        "annotation": new_annotation,
        "footnote": counters["global"],
        "category_footnote": f"{code}-{counters[code]}"
    }


@router.get("/annotations/{document_id}")
async def get_document_annotations(document_id: str, page: Optional[int] = None):
    """
    Get all annotations for a document.
    Returns indexed footnotes with category markers.
    """
    annotations = [
        a for a in annotations_data["annotations"].values()
        if a["document_id"] == document_id
    ]
    
    if page is not None:
        annotations = [a for a in annotations if a["page_number"] == page]
    
    # Sort by footnote number
    annotations.sort(key=lambda x: x["footnote_number"])
    
    # Group by category
    by_category = {}
    for ann in annotations:
        code = ann["extraction_code"]
        if code not in by_category:
            by_category[code] = []
        by_category[code].append(ann)
    
    return {
        "document_id": document_id,
        "total_annotations": len(annotations),
        "annotations": annotations,
        "by_category": by_category,
        "counters": get_footnote_counters(document_id)
    }


@router.put("/annotations/{annotation_id}")
async def update_annotation(annotation_id: str, update: AnnotationUpdate):
    """Update an annotation's note, link, or verification status."""
    if annotation_id not in annotations_data["annotations"]:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    ann = annotations_data["annotations"][annotation_id]
    
    if update.annotation_note is not None:
        ann["annotation_note"] = update.annotation_note
    if update.linked_event_id is not None:
        ann["linked_event_id"] = update.linked_event_id
    if update.is_verified is not None:
        ann["is_verified"] = update.is_verified
    
    ann["updated_at"] = datetime.now().isoformat()
    
    return {"success": True, "annotation": ann}


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: str):
    """Delete an annotation (footnote numbers are preserved for audit trail)."""
    if annotation_id not in annotations_data["annotations"]:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    del annotations_data["annotations"][annotation_id]
    return {"success": True}


@router.post("/annotations/link-event")
async def link_annotation_to_event(link: TimelineEventLink):
    """
    Link an annotation to a timeline event.
    This creates a bidirectional connection for date/event coordination.
    """
    if link.annotation_id not in annotations_data["annotations"]:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    ann = annotations_data["annotations"][link.annotation_id]
    ann["linked_event_id"] = link.event_id
    ann["event_status"] = link.event_status
    ann["updated_at"] = datetime.now().isoformat()
    
    return {
        "success": True,
        "annotation_id": link.annotation_id,
        "event_id": link.event_id,
        "event_status": link.event_status
    }


@router.get("/annotations/footnote-index/{document_id}")
async def get_footnote_index(document_id: str):
    """
    Get the complete footnote index for a document.
    Returns all annotations organized for citation reference.
    """
    annotations = [
        a for a in annotations_data["annotations"].values()
        if a["document_id"] == document_id
    ]
    
    annotations.sort(key=lambda x: x["footnote_number"])
    
    index = []
    for ann in annotations:
        index.append({
            "number": ann["footnote_number"],
            "code": ann["extraction_code"],
            "category_id": ann["extraction_id"],
            "text": ann["highlight_text"][:100] + ("..." if len(ann["highlight_text"]) > 100 else ""),
            "page": ann["page_number"],
            "note": ann.get("annotation_note"),
            "linked_event": ann.get("linked_event_id"),
            "verified": ann.get("is_verified", False)
        })
    
    return {
        "document_id": document_id,
        "total": len(index),
        "index": index
    }


@router.get("/annotations/date-events/{document_id}")
async def get_date_event_coordination(document_id: str):
    """
    Get all date-related annotations with suggested timeline events.
    Used for coordinating dates across documents.
    """
    # Get date-related annotations
    date_codes = ["DT", "DL", "TL", "EV"]
    annotations = [
        a for a in annotations_data["annotations"].values()
        if a["document_id"] == document_id and a["extraction_code"] in date_codes
    ]
    
    # Sort by page/position
    annotations.sort(key=lambda x: (x["page_number"], x["position_y"]))
    
    date_events = []
    for ann in annotations:
        date_events.append({
            "annotation_id": ann["id"],
            "extraction_id": ann["extraction_id"],
            "text": ann["highlight_text"],
            "page": ann["page_number"],
            "code": ann["extraction_code"],
            "linked_event_id": ann.get("linked_event_id"),
            "event_status": ann.get("event_status", "pending"),
            "context_before": ann.get("context_before", "")[:50],
            "context_after": ann.get("context_after", "")[:50],
            # Suggested event statuses based on context
            "suggested_statuses": suggest_event_statuses(ann)
        })
    
    return {
        "document_id": document_id,
        "total_dates": len(date_events),
        "date_events": date_events
    }


def suggest_event_statuses(annotation: dict) -> List[str]:
    """Suggest event statuses based on annotation context."""
    text = (annotation.get("highlight_text", "") + " " + 
            annotation.get("context_before", "") + " " + 
            annotation.get("context_after", "")).lower()
    
    suggestions = []
    
    # Pattern matching for status suggestions
    status_patterns = {
        "served": ["served", "delivered", "sent", "mailed", "posted"],
        "received": ["received", "got", "acknowledged"],
        "filed": ["filed", "submitted", "recorded", "entered"],
        "start": ["begin", "start", "commence", "effective", "from"],
        "finish": ["end", "expire", "terminate", "conclude", "until", "through"],
        "deadline": ["due", "deadline", "by", "must", "required"],
        "invited": ["hearing", "scheduled", "appearance", "meeting", "appointment"],
        "reported": ["reported", "complained", "notified", "informed"],
        "pending": ["pending", "awaiting", "waiting"],
    }
    
    for status, keywords in status_patterns.items():
        if any(kw in text for kw in keywords):
            suggestions.append(status)
    
    return suggestions if suggestions else ["pending"]


# =============================================================================
# COMPREHENSIVE DOCUMENT OPERATIONS
# Consolidates all document functions from across the app
# =============================================================================

class DocumentDeleteRequest(BaseModel):
    """Request to delete a document with options."""
    delete_extractions: bool = True
    delete_annotations: bool = True
    delete_highlights: bool = True
    delete_timeline_events: bool = False  # Careful - affects case history


class DocumentAnalyzeRequest(BaseModel):
    """Request to analyze a document."""
    extract_text: bool = True
    classify_type: bool = True
    extract_entities: bool = True
    create_timeline_events: bool = False
    min_confidence: float = 0.7


class ExtractionRequest(BaseModel):
    """Request to extract specific data from a document."""
    extract_dates: bool = True
    extract_parties: bool = True
    extract_amounts: bool = True
    extract_addresses: bool = True
    extract_legal_refs: bool = True
    extract_case_numbers: bool = True


@router.delete("/document/{doc_id}/full")
async def delete_document_full(doc_id: str, options: DocumentDeleteRequest = None):
    """
    Delete a document and optionally all related data.
    
    This comprehensive delete removes:
    - The document file itself
    - All page extractions from this document
    - All annotations/footnotes from this document
    - All highlights from this document
    - Optionally: timeline events linked to this document
    
    Returns a summary of what was deleted.
    """
    if options is None:
        options = DocumentDeleteRequest()
    
    deleted_summary = {
        "document_deleted": False,
        "extractions_deleted": 0,
        "annotations_deleted": 0,
        "highlights_deleted": 0,
        "timeline_events_deleted": 0,
    }
    
    # Delete the main document
    if doc_id in briefcase_data["documents"]:
        doc = briefcase_data["documents"][doc_id]
        doc_name = doc.get("name", "")
        del briefcase_data["documents"][doc_id]
        deleted_summary["document_deleted"] = True
        deleted_summary["document_name"] = doc_name
    else:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete related extractions
    if options.delete_extractions:
        extraction_ids_to_delete = []
        for ext_id, ext in briefcase_data.get("extractions", {}).items():
            if ext.get("pdf_name") == doc_name or ext.get("document_id") == doc_id:
                extraction_ids_to_delete.append(ext_id)
                # Delete file if exists
                if "file_path" in ext:
                    file_path = Path(ext["file_path"])
                    if file_path.exists():
                        file_path.unlink()
        
        for ext_id in extraction_ids_to_delete:
            del briefcase_data["extractions"][ext_id]
        deleted_summary["extractions_deleted"] = len(extraction_ids_to_delete)
    
    # Delete related annotations
    if options.delete_annotations:
        ann_ids_to_delete = []
        for ann_id, ann in annotations_data.get("annotations", {}).items():
            if ann.get("document_id") == doc_id:
                ann_ids_to_delete.append(ann_id)
        
        for ann_id in ann_ids_to_delete:
            del annotations_data["annotations"][ann_id]
        deleted_summary["annotations_deleted"] = len(ann_ids_to_delete)
        
        # Clear footnote counters for this document
        if doc_id in annotations_data.get("footnote_counters", {}):
            del annotations_data["footnote_counters"][doc_id]
    
    # Delete related highlights
    if options.delete_highlights:
        hl_ids_to_delete = []
        for hl_id, hl in briefcase_data.get("highlights", {}).items():
            if hl.get("pdf_name") == doc_name or hl.get("document_id") == doc_id:
                hl_ids_to_delete.append(hl_id)
        
        for hl_id in hl_ids_to_delete:
            del briefcase_data["highlights"][hl_id]
        deleted_summary["highlights_deleted"] = len(hl_ids_to_delete)
    
    # Delete timeline events (optional, careful with this)
    if options.delete_timeline_events:
        try:
            from app.core.database import get_db_session
            from app.models.models import TimelineEvent
            from sqlalchemy import delete
            
            # This is async, but we're in sync context - would need adjustment
            # For now, just note that timeline events should be deleted separately
            deleted_summary["timeline_note"] = "Timeline events should be deleted via timeline API"
        except ImportError:
            pass
    
    return {
        "success": True,
        "message": f"Document '{doc_name}' and related data deleted",
        "deleted": deleted_summary
    }


@router.get("/document/{doc_id}/extractions")
async def get_document_extractions(doc_id: str):
    """
    Get all extractions from a specific document.
    
    Includes:
    - Page extractions (split PDFs)
    - Highlights and notes
    - Annotations with footnotes
    - Linked timeline events
    """
    # Get document info
    doc = briefcase_data["documents"].get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_name = doc.get("name", "")
    
    # Get page extractions
    extractions = [
        ext for ext in briefcase_data.get("extractions", {}).values()
        if ext.get("pdf_name") == doc_name or ext.get("document_id") == doc_id
    ]
    
    # Get highlights
    highlights = [
        hl for hl in briefcase_data.get("highlights", {}).values()
        if hl.get("pdf_name") == doc_name or hl.get("document_id") == doc_id
    ]
    
    # Get annotations
    annotations = [
        ann for ann in annotations_data.get("annotations", {}).values()
        if ann.get("document_id") == doc_id
    ]
    
    # Sort annotations by footnote number
    annotations.sort(key=lambda x: x.get("footnote_number", 0))
    
    # Group annotations by extraction code
    annotations_by_code = {}
    for ann in annotations:
        code = ann.get("extraction_code", "NT")
        if code not in annotations_by_code:
            annotations_by_code[code] = []
        annotations_by_code[code].append(ann)
    
    return {
        "document_id": doc_id,
        "document_name": doc_name,
        "page_extractions": {
            "total": len(extractions),
            "items": extractions
        },
        "highlights": {
            "total": len(highlights),
            "items": highlights,
            "by_color": group_by_key(highlights, "color_name")
        },
        "annotations": {
            "total": len(annotations),
            "items": annotations,
            "by_code": annotations_by_code,
            "footnote_count": get_footnote_counters(doc_id)
        }
    }


def group_by_key(items: List[dict], key: str) -> Dict[str, List[dict]]:
    """Group items by a key value."""
    groups = {}
    for item in items:
        val = item.get(key, "unknown")
        if val not in groups:
            groups[val] = []
        groups[val].append(item)
    return groups


@router.post("/document/{doc_id}/analyze")
async def analyze_briefcase_document(doc_id: str, options: DocumentAnalyzeRequest = None):
    """
    Analyze a briefcase document to extract intelligence.
    
    This proxies to the main document pipeline for:
    - OCR text extraction
    - Document type classification
    - Entity extraction (dates, parties, amounts)
    - Optional: Auto-create timeline events
    
    Results are stored with the briefcase document.
    """
    if options is None:
        options = DocumentAnalyzeRequest()
    
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found in briefcase")
    
    doc = briefcase_data["documents"][doc_id]
    
    # Get document content
    if "content" not in doc:
        raise HTTPException(status_code=400, detail="Document has no content")
    
    content = base64.b64decode(doc["content"])
    
    results = {
        "document_id": doc_id,
        "document_name": doc.get("name"),
        "analysis": {}
    }
    
    # Try to extract text
    if options.extract_text:
        try:
            from app.services.ocr_service import extract_text_from_file
            ocr_result = await extract_text_from_file(
                file_bytes=content,
                filename=doc.get("name", "document")
            )
            results["analysis"]["text"] = {
                "extracted": True,
                "text_preview": ocr_result.text[:500] if ocr_result.text else "",
                "full_text": ocr_result.text,
                "confidence": ocr_result.confidence,
                "method": ocr_result.method
            }
            doc["extracted_text"] = ocr_result.text
            doc["text_confidence"] = ocr_result.confidence
        except Exception as e:
            results["analysis"]["text"] = {"extracted": False, "error": str(e)}
    
    # Try to classify document type
    if options.classify_type and doc.get("extracted_text"):
        try:
            from app.services.recognition.engine import get_recognition_engine
            engine = get_recognition_engine()
            recognition = await engine.recognize(
                text=doc["extracted_text"],
                filename=doc.get("name")
            )
            results["analysis"]["classification"] = {
                "doc_type": recognition.document_type.value if recognition.document_type else None,
                "confidence": recognition.confidence,
                "category": recognition.category.value if recognition.category else None
            }
            doc["doc_type"] = recognition.document_type.value if recognition.document_type else None
            doc["doc_confidence"] = recognition.confidence
        except Exception as e:
            results["analysis"]["classification"] = {"error": str(e)}
    
    # Try to extract entities
    if options.extract_entities and doc.get("extracted_text"):
        try:
            from app.services.event_extractor import get_event_extractor
            extractor = get_event_extractor()
            events = extractor.extract_events(
                text=doc["extracted_text"],
                doc_type=doc.get("doc_type", "unknown")
            )
            
            # Filter by confidence
            events = [e for e in events if e.confidence >= options.min_confidence]
            
            results["analysis"]["entities"] = {
                "events_found": len(events),
                "events": [
                    {
                        "date": e.date.isoformat() if e.date else None,
                        "type": e.event_type,
                        "title": e.title,
                        "description": e.description,
                        "confidence": e.confidence,
                        "is_deadline": e.is_deadline
                    }
                    for e in events
                ]
            }
            doc["extracted_events"] = results["analysis"]["entities"]["events"]
        except Exception as e:
            results["analysis"]["entities"] = {"error": str(e)}
    
    doc["analyzed_at"] = datetime.now().isoformat()
    doc["updated_at"] = datetime.now().isoformat()
    
    return results


@router.post("/document/{doc_id}/extract")
async def extract_document_data(doc_id: str, options: ExtractionRequest = None):
    """
    Extract specific data types from a briefcase document.
    
    Uses pattern matching and AI to find:
    - Dates (DT) - court dates, deadlines, lease dates
    - Parties (PT) - landlord, tenant, attorney names
    - Amounts ($) - rent, fees, damages, deposits
    - Addresses (AD) - property addresses, mailing addresses
    - Legal refs (LG) - statute citations, case numbers
    - Case numbers - court case identifiers
    
    Returns extracted data organized by category with confidence scores.
    """
    if options is None:
        options = ExtractionRequest()
    
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = briefcase_data["documents"][doc_id]
    
    # Need extracted text
    if not doc.get("extracted_text"):
        return {
            "error": "Document has no extracted text. Run /analyze first.",
            "document_id": doc_id
        }
    
    text = doc["extracted_text"]
    extractions = {
        "document_id": doc_id,
        "document_name": doc.get("name"),
        "extracted_at": datetime.now().isoformat()
    }
    
    import re
    
    # Extract dates
    if options.extract_dates:
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b',
        ]
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        extractions["dates"] = {
            "code": "DT",
            "count": len(dates),
            "items": list(set(dates))[:50]  # Dedupe and limit
        }
    
    # Extract amounts
    if options.extract_amounts:
        amount_pattern = r'\$[\d,]+(?:\.\d{2})?|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b'
        amounts = re.findall(amount_pattern, text, re.IGNORECASE)
        extractions["amounts"] = {
            "code": "$",
            "count": len(amounts),
            "items": list(set(amounts))[:30]
        }
    
    # Extract addresses
    if options.extract_addresses:
        address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Place|Pl)\.?(?:\s+(?:Apt|Unit|Suite|Ste|#)\s*\d+)?'
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        extractions["addresses"] = {
            "code": "AD",
            "count": len(addresses),
            "items": list(set(addresses))[:20]
        }
    
    # Extract case numbers
    if options.extract_case_numbers:
        case_patterns = [
            r'\b(?:Case|Cause|File)\s*(?:No\.?|Number|#)?\s*:?\s*([A-Z0-9-]+)\b',
            r'\b(\d{2}-\d+-[A-Z]+)\b',  # Common format: 24-123-CV
            r'\b([A-Z]{2,3}\d{2}-\d{4,})\b',  # Format: CV24-1234
        ]
        cases = []
        for pattern in case_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            cases.extend(matches)
        extractions["case_numbers"] = {
            "code": "LG",
            "count": len(cases),
            "items": list(set(cases))[:10]
        }
    
    # Extract party names (harder - use simple patterns)
    if options.extract_parties:
        party_patterns = [
            r'(?:Plaintiff|Petitioner|Complainant|Landlord|Lessor):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?:Defendant|Respondent|Tenant|Lessee):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'v\.\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        parties = []
        for pattern in party_patterns:
            matches = re.findall(pattern, text)
            parties.extend(matches)
        extractions["parties"] = {
            "code": "PT",
            "count": len(parties),
            "items": list(set(parties))[:20]
        }
    
    # Extract legal references
    if options.extract_legal_refs:
        legal_patterns = [
            r'\b(Minn\.?\s*Stat\.?\s*(?:§|Section)?\s*[\d.]+)\b',
            r'\b((?:M\.S\.|MN|Minn)\s*[\d.]+)\b',
            r'\b(Chapter\s+\d+[A-Z]?)\b',
        ]
        legal_refs = []
        for pattern in legal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            legal_refs.extend(matches)
        extractions["legal_refs"] = {
            "code": "LG",
            "count": len(legal_refs),
            "items": list(set(legal_refs))[:30]
        }
    
    # Store extractions with document
    doc["extractions"] = extractions
    doc["updated_at"] = datetime.now().isoformat()
    
    return extractions


@router.get("/document/{doc_id}/text")
async def get_document_text(doc_id: str):
    """Get the extracted text content of a briefcase document."""
    if doc_id not in briefcase_data["documents"]:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = briefcase_data["documents"][doc_id]
    
    if not doc.get("extracted_text"):
        return {
            "document_id": doc_id,
            "has_text": False,
            "message": "No text extracted. Run /analyze first."
        }
    
    return {
        "document_id": doc_id,
        "document_name": doc.get("name"),
        "has_text": True,
        "text": doc["extracted_text"],
        "text_length": len(doc["extracted_text"]),
        "text_confidence": doc.get("text_confidence"),
        "analyzed_at": doc.get("analyzed_at")
    }


@router.post("/import-from-vault/{vault_doc_id}")
async def import_from_vault(vault_doc_id: str, folder_id: str = "root"):
    """
    Import a document from the main vault/documents system into the briefcase.
    
    Copies the document and any existing analysis to the briefcase
    for organization and annotation.
    """
    try:
        from app.services.document_pipeline import get_document_pipeline
        pipeline = get_document_pipeline()
        doc = pipeline.get_document(vault_doc_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="Vault document not found")
        
        # Create briefcase document from vault document
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # Try to get file content
        content_b64 = ""
        if hasattr(doc, 'file_path') and doc.file_path and os.path.exists(doc.file_path):
            with open(doc.file_path, 'rb') as f:
                content_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        briefcase_doc = {
            "id": doc_id,
            "name": doc.filename,
            "folder_id": folder_id,
            "size": doc.file_size if hasattr(doc, 'file_size') else 0,
            "type": get_file_type(os.path.splitext(doc.filename)[1]),
            "extension": os.path.splitext(doc.filename)[1],
            "mime_type": doc.mime_type if hasattr(doc, 'mime_type') else "application/octet-stream",
            "tags": [],
            "notes": "",
            "starred": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "content": content_b64,
            # Import existing analysis
            "vault_doc_id": vault_doc_id,
            "doc_type": doc.doc_type.value if doc.doc_type else None,
            "doc_confidence": doc.confidence,
            "title": doc.title,
            "summary": doc.summary,
            "extracted_text": doc.full_text if hasattr(doc, 'full_text') else None,
            "key_dates": doc.key_dates if hasattr(doc, 'key_dates') else None,
            "key_parties": doc.key_parties if hasattr(doc, 'key_parties') else None,
            "key_amounts": doc.key_amounts if hasattr(doc, 'key_amounts') else None,
        }
        
        briefcase_data["documents"][doc_id] = briefcase_doc
        
        return {
            "success": True,
            "briefcase_doc_id": doc_id,
            "vault_doc_id": vault_doc_id,
            "imported": {
                "name": briefcase_doc["name"],
                "type": briefcase_doc["doc_type"],
                "has_text": bool(briefcase_doc.get("extracted_text")),
                "has_dates": bool(briefcase_doc.get("key_dates")),
            }
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Document pipeline not available")


@router.get("/consolidated-functions")
async def get_consolidated_functions():
    """
    Get a list of all document functions available in the briefcase.
    This consolidates functionality from across the app.
    """
    return {
        "briefcase_functions": {
            "folder_management": [
                {"endpoint": "POST /folder", "description": "Create folder"},
                {"endpoint": "PUT /folder/{id}", "description": "Update folder"},
                {"endpoint": "DELETE /folder/{id}", "description": "Delete folder"},
                {"endpoint": "GET /folder/{id}", "description": "Get folder contents"},
            ],
            "document_management": [
                {"endpoint": "POST /document", "description": "Upload document"},
                {"endpoint": "GET /document/{id}", "description": "Get document metadata"},
                {"endpoint": "PUT /document/{id}", "description": "Update document"},
                {"endpoint": "DELETE /document/{id}", "description": "Delete document (basic)"},
                {"endpoint": "DELETE /document/{id}/full", "description": "Delete document + all related data"},
                {"endpoint": "GET /document/{id}/download", "description": "Download document"},
                {"endpoint": "GET /document/{id}/preview", "description": "Preview document"},
                {"endpoint": "POST /document/{id}/move", "description": "Move to folder"},
                {"endpoint": "POST /document/{id}/copy", "description": "Copy to folder"},
            ],
            "analysis_functions": [
                {"endpoint": "POST /document/{id}/analyze", "description": "OCR + classify + extract entities"},
                {"endpoint": "POST /document/{id}/extract", "description": "Extract dates/amounts/parties/etc"},
                {"endpoint": "GET /document/{id}/text", "description": "Get extracted text"},
                {"endpoint": "GET /document/{id}/extractions", "description": "Get all extractions from document"},
            ],
            "annotation_functions": [
                {"endpoint": "POST /annotations", "description": "Create annotation with footnote"},
                {"endpoint": "GET /annotations/{doc_id}", "description": "Get all annotations"},
                {"endpoint": "PUT /annotations/{id}", "description": "Update annotation"},
                {"endpoint": "DELETE /annotations/{id}", "description": "Delete annotation"},
                {"endpoint": "POST /annotations/link-event", "description": "Link to timeline event"},
                {"endpoint": "GET /annotations/footnote-index/{doc_id}", "description": "Get footnote index"},
                {"endpoint": "GET /annotations/date-events/{doc_id}", "description": "Get date/event coordination"},
            ],
            "highlight_functions": [
                {"endpoint": "POST /highlight", "description": "Save highlight"},
                {"endpoint": "POST /highlights/batch", "description": "Save multiple highlights"},
                {"endpoint": "GET /highlights", "description": "List highlights"},
                {"endpoint": "GET /highlights/by-color", "description": "Group by color"},
                {"endpoint": "DELETE /highlight/{id}", "description": "Delete highlight"},
            ],
            "extraction_functions": [
                {"endpoint": "POST /extraction", "description": "Save extracted pages"},
                {"endpoint": "GET /extractions", "description": "List extractions"},
                {"endpoint": "GET /extraction/{id}", "description": "Get extraction"},
                {"endpoint": "GET /extraction/{id}/download", "description": "Download extraction"},
                {"endpoint": "DELETE /extraction/{id}", "description": "Delete extraction"},
            ],
            "import_export": [
                {"endpoint": "POST /import-from-vault/{id}", "description": "Import from main vault"},
                {"endpoint": "POST /export", "description": "Export folder as ZIP"},
            ],
            "search_and_filter": [
                {"endpoint": "GET /search", "description": "Search documents"},
                {"endpoint": "GET /starred", "description": "Get starred documents"},
                {"endpoint": "GET /recent", "description": "Get recent documents"},
                {"endpoint": "GET /tags", "description": "List all tags"},
            ],
        },
        "extraction_codes": {
            "DT": "Dates & Deadlines",
            "PT": "Parties & Names",
            "$": "Money & Amounts",
            "AD": "Addresses & Locations",
            "LG": "Legal Terms & Citations",
            "NT": "Notes & Footnotes",
            "FM": "Form Field Data",
            "EV": "Events & Actions",
            "DL": "Critical Deadlines",
            "WS": "Witness/Testimony",
            "VL": "Violations/Issues",
            "ED": "Evidence Markers",
            "QT": "Quoted Text",
            "TL": "Timeline Key Dates",
        },
        "event_statuses": [
            "start", "continued", "finish", "reported", "invited",
            "attended", "missed", "served", "received", "filed",
            "responded", "pending", "resolved", "escalated", "used", "unknown"
        ]
    }