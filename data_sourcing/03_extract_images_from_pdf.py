"""
extract_images_from_pdf.py
This script extracts image regions from PDF files based on relative coordinates specified in a JSON annotation file.
It uses PyMuPDF to open and process PDFs, and Pillow to save the extracted images. The extraction is performed at a
specified resolution (DPI), and the images are saved in the 'images' directory with descriptive filenames.
- Reads annotations from 'annotations.json', which should contain image regions with relative coordinates.
- For each annotated image region, converts relative coordinates to absolute positions on the PDF page.
- Extracts the specified region at the given DPI and saves it as a PNG file in the 'images' folder.
- Handles missing files, invalid pages, and extraction errors gracefully.
"""

import os
import json
import fitz  # PyMuPDF
from PIL import Image
from tqdm import tqdm
import argparse

def main():
    parser = argparse.ArgumentParser(description="Extract images from PDFs based on annotations")
    parser.add_argument("--pdf-dir", default=os.getenv("PDF_DIR", "pdf"), help="Directory containing PDF files")
    parser.add_argument("--img-dir", default=os.getenv("IMG_DIR", "images_new"), help="Directory to save extracted images")
    parser.add_argument("--annot-file", default=os.getenv("ANNOT_FILE", "annotations.json"), help="Annotations JSON file")
    parser.add_argument("--dpi", type=int, default=int(os.getenv("DPI", "144")), help="DPI for image extraction")
    
    args = parser.parse_args()
    
    PDF_DIR = args.pdf_dir
    IMG_DIR = args.img_dir
    ANNOT_FILE = args.annot_file
    DPI = args.dpi

    os.makedirs(IMG_DIR, exist_ok=True)

    with open(ANNOT_FILE, "r") as f:
        data = json.load(f)

    total_extracted = 0

    for key, annotations in tqdm(data.items(), desc="Processing PDFs"):
        pdf_path = os.path.join(PDF_DIR, f"{key}.pdf")
        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            continue

        try:
            doc = fitz.open(pdf_path)

            for idx, ann in enumerate(annotations):
                parts = ann.get("inconsistency_parts", [])
                for pidx, part in enumerate(parts):
                    if part.get("type") != "image":
                        continue

                    page_num = part.get("page")
                    bbox = part.get("bbox")

                    if page_num is None or bbox is None:
                        continue

                    # Convert to 0-based indexing (PyMuPDF uses 0-based)
                    page_index = page_num - 1 if page_num > 0 else page_num

                    try:
                        if page_index >= len(doc) or page_index < 0:
                            print(
                                f"Page {page_num} (index {page_index}) not found in {pdf_path} (has {len(doc)} pages)"
                            )
                            continue

                        page = doc[page_index]
                        rect = page.rect

                        # Convert relative coordinates to absolute
                        abs_bbox = fitz.Rect(
                            rect.x0 + bbox["x"] * rect.width,
                            rect.y0 + bbox["y"] * rect.height,
                            rect.x0 + (bbox["x"] + bbox["width"]) * rect.width,
                            rect.y0 + (bbox["y"] + bbox["height"]) * rect.height,
                        )

                        # Extract the image region
                        pix = page.get_pixmap(clip=abs_bbox, dpi=DPI)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                        # Use image_id for filename if available
                        image_id = part.get("image_id")
                        if image_id:
                            img_filename = f"{image_id}.png"
                        else:
                            img_filename = f"{key}_{page_num}_{idx}_{pidx}.png"
                        img_path = os.path.join(IMG_DIR, img_filename)
                        img.save(img_path)

                        total_extracted += 1

                    except Exception as e:
                        print(
                            f"Error extracting image from {key}, page {page_num}: {str(e)}"
                        )
                        continue

            doc.close()

        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            continue

    print(f"\nExtraction complete! Total images extracted: {total_extracted}")
    print(f"Images saved in: {IMG_DIR}")

if __name__ == "__main__":
    main()
