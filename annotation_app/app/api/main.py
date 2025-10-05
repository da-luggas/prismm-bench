from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import Response, JSONResponse, StreamingResponse
import httpx
import os
import tempfile
import fitz  # PyMuPDF
import io
import json
import base64
import uuid
import zipfile
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000", "http://127.0.0.1", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(tempfile.gettempdir(), "openreview_pdfs")
IMAGES_DIR = os.path.join("annotation_images")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

class ImageSaveRequest(BaseModel):
    image_data: str
    paper_id: str
    page: int
    bbox: Dict[str, float]

class ExportRequest(BaseModel):
    annotations: Dict[str, Any]

@app.get("/api/pdf-proxy")
def get_paper(request: Request):
    paper_id = request.query_params.get("paper_id")
    if not paper_id:
        return JSONResponse({"error": "Paper ID is required"}, status_code=400)

    temp_pdf_path = os.path.join(TEMP_DIR, f"{paper_id}.pdf")

    # Check if PDF already exists in temp
    if os.path.exists(temp_pdf_path):
        with open(temp_pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{paper_id}.pdf"'
            }
        )

    pdf_url = f"https://openreview.net/pdf?id={paper_id}"
    try:
        resp = httpx.get(pdf_url, timeout=60.0)
        if resp.status_code != 200:
            return JSONResponse({"error": "PDF not found"}, status_code=404)
        pdf_bytes = resp.content

        # Save PDF to temp file
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_bytes)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{paper_id}.pdf"'
            }
        )
    except Exception as e:
        print("Error fetching PDF:", e)
        return JSONResponse({"error": "Failed to fetch PDF"}, status_code=500)

@app.get("/api/remove-paper")
def remove_paper(paper_id: str = Query(..., description="The paper_id to remove")):
    temp_pdf_path = os.path.join(TEMP_DIR, f"{paper_id}.pdf")
    if os.path.exists(temp_pdf_path):
        try:
            os.remove(temp_pdf_path)
            return {"message": f"Temporary file for paper_id '{paper_id}' removed."}
        except Exception as e:
            print("Error removing PDF:", e)
            return JSONResponse({"error": "Failed to remove PDF"}, status_code=500)
    else:
        return JSONResponse({"error": "Temporary file not found"}, status_code=404)

@app.get("/api/pdf-to-image")
def pdf_to_image(paper_id: str = Query(..., description="The paper_id to use"),
                 page: int = Query(..., description="The page number (1-based)")):
    temp_pdf_path = os.path.join(TEMP_DIR, f"{paper_id}.pdf")

    # Ensure PDF exists (download if needed)
    if not os.path.exists(temp_pdf_path):
        pdf_url = f"https://openreview.net/pdf?id={paper_id}"
        try:
            resp = httpx.get(pdf_url, timeout=60.0)
            if resp.status_code != 200:
                return JSONResponse({"error": "PDF not found"}, status_code=404)
            pdf_bytes = resp.content
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as e:
            print("Error fetching PDF:", e)
            return JSONResponse({"error": "Failed to fetch PDF"}, status_code=500)

    # Extract page as image
    try:
        doc = fitz.open(temp_pdf_path)
        if page < 1 or page > doc.page_count:
            doc.close()
            return JSONResponse({"error": "Page number out of range"}, status_code=400)
        pdf_page = doc.load_page(page - 1)  # 0-based indexing
        pix = pdf_page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
        img_data = pix.tobytes("png")
        doc.close()
        return StreamingResponse(io.BytesIO(img_data), media_type="image/png")
    except Exception as e:
        print("Error processing PDF:", e)
        return JSONResponse({"error": "Failed to process PDF"}, status_code=500)

@app.post("/api/save-image")
async def save_image(request: ImageSaveRequest):
    """Save cropped image to disk and return reference ID"""
    try:
        # Generate unique image ID
        image_id = f"{request.paper_id}_{request.page}_{uuid.uuid4().hex[:8]}"
        
        # Decode base64 image
        if request.image_data.startswith('data:image'):
            # Remove data URL prefix
            image_data = request.image_data.split(',')[1]
        else:
            image_data = request.image_data
            
        image_bytes = base64.b64decode(image_data)
        
        # Save image to disk
        image_path = os.path.join(IMAGES_DIR, f"{image_id}.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)
            
        # Save metadata
        metadata = {
            "image_id": image_id,
            "paper_id": request.paper_id,
            "page": request.page,
            "bbox": request.bbox,
            "timestamp": datetime.now().isoformat(),
            "file_path": image_path
        }
        
        metadata_path = os.path.join(IMAGES_DIR, f"{image_id}.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
            
        return {"image_id": image_id, "status": "saved"}
        
    except Exception as e:
        print("Error saving image:", e)
        return JSONResponse({"error": "Failed to save image"}, status_code=500)

@app.post("/api/export-annotations")
async def export_annotations(annotations: Dict[str, Any]):
    """Export annotations as a ZIP file containing JSON and images"""
    try:
        # Create a temporary ZIP file
        zip_path = os.path.join(tempfile.gettempdir(), f"annotations_{uuid.uuid4().hex[:8]}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add annotations JSON
            annotations_json = json.dumps(annotations, indent=2)
            zipf.writestr("annotations.json", annotations_json)
            
            # Collect all image IDs from annotations
            image_ids = set()
            for paper_annotations in annotations.values():
                for annotation in paper_annotations:
                    for part in annotation.get("inconsistency_parts", []):
                        if part.get("image_id"):
                            image_ids.add(part["image_id"])
            
            # Add images to ZIP
            images_added = 0
            for image_id in image_ids:
                image_path = os.path.join(IMAGES_DIR, f"{image_id}.png")
                metadata_path = os.path.join(IMAGES_DIR, f"{image_id}.json")
                
                if os.path.exists(image_path):
                    zipf.write(image_path, f"images/{image_id}.png")
                    images_added += 1
                    
                if os.path.exists(metadata_path):
                    zipf.write(metadata_path, f"metadata/{image_id}.json")
            
            # Add summary
            summary = {
                "export_timestamp": datetime.now().isoformat(),
                "total_papers": len(annotations),
                "total_annotations": sum(len(paper_annotations) for paper_annotations in annotations.values()),
                "total_images": images_added,
                "image_ids": list(image_ids)
            }
            zipf.writestr("export_summary.json", json.dumps(summary, indent=2))
        
        # Return ZIP file
        with open(zip_path, "rb") as f:
            zip_content = f.read()
            
        # Clean up temporary ZIP file
        os.remove(zip_path)
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            }
        )
        
    except Exception as e:
        print("Error exporting annotations:", e)
        return JSONResponse({"error": "Failed to export annotations"}, status_code=500)

@app.get("/api/cleanup-images")
def cleanup_old_images(days_old: int = Query(7, description="Remove images older than N days")):
    """Clean up old image files to save disk space"""
    try:
        import time
        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 60 * 60)
        
        removed_count = 0
        for filename in os.listdir(IMAGES_DIR):
            file_path = os.path.join(IMAGES_DIR, filename)
            if os.path.isfile(file_path):
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
                    
        return {"message": f"Removed {removed_count} old files"}
        
    except Exception as e:
        print("Error cleaning up images:", e)
        return JSONResponse({"error": "Failed to cleanup images"}, status_code=500)
