import os
import json
from pdf2image import convert_from_path
import re
from tqdm import tqdm
import argparse

def extract_figures_tables(
    mineru_dir="mineru_output", pdf_dir="pdf", output_dir="suppl_images", dpi=144
):
    """
    Extract figures, tables, and equations from PDFs based on mineru_output JSON metadata.
    Saves cropped images into output_dir with filenames indicating pdf_id, page, type, group, and figure/table name.
    Assumes bounding boxes are in PDF points (1/72 inch), and output images are at a specified DPI.
    """
    os.makedirs(output_dir, exist_ok=True)
    # Prepare metadata list
    extracted_metadata = []
    # Iterate over each paper folder
    for pdf_id in tqdm(os.listdir(mineru_dir)):
        auto_dir = os.path.join(mineru_dir, pdf_id, "auto")
        if not os.path.isdir(auto_dir):
            continue
        # Find the middle.json file
        json_files = [f for f in os.listdir(auto_dir) if f.endswith("middle.json")]
        if not json_files:
            continue
        json_path = os.path.join(auto_dir, json_files[0])
        try:
            with open(json_path, "r") as jf:
                data = json.load(jf)
        except Exception as e:
            print(f"Failed to load JSON {json_path}: {e}")
            continue

        # Load PDF pages as images at specified dpi
        pdf_path = os.path.join(pdf_dir, f"{pdf_id}.pdf")
        if not os.path.exists(pdf_path):
            print(f"PDF not found: {pdf_path}")
            continue
        try:
            pages = convert_from_path(pdf_path, dpi=dpi)
        except Exception as e:
            print(f"Error converting PDF {pdf_path}: {e}")
            continue

        # Process each page's blocks
        for page_info in data.get("pdf_info", []):
            page_idx = page_info.get("page_idx", 0)
            if page_idx < 0 or page_idx >= len(pages):
                continue
            img = pages[page_idx]
            scale = dpi / 72.0  # 72 dpi (PDF points) to specified dpi
            page_width, page_height = img.size

            # Extract image and table blocks
            for block in page_info.get("preproc_blocks", []):
                btype = block.get("type")
                if btype not in ("image", "table", "interline_equation"):
                    continue

                # Handle equations separately (no grouping, no captions)
                if btype == "interline_equation":
                    bbox = block.get("bbox")
                    if not bbox or len(bbox) < 4:
                        continue

                    # Scale from PDF points to specified dpi
                    x0, y0, x1, y1 = bbox
                    left = x0 * scale
                    top = y0 * scale
                    right = x1 * scale
                    bottom = y1 * scale

                    crop = img.crop((left, top, right, bottom))

                    # Use block index or create a unique identifier for equations
                    eq_id = block.get("index", "unknown")
                    # Replace underscores with hyphens and convert to string
                    btype_clean = btype.replace("_", "-")
                    out_name = f"{pdf_id}_{page_idx}_{btype_clean}_equation{eq_id}.png"
                    out_path = os.path.join(output_dir, out_name)
                    try:
                        crop.save(out_path)
                        # Save metadata
                        rel_bbox = [
                            left / page_width,
                            top / page_height,
                            right / page_width,
                            bottom / page_height,
                        ]
                        extracted_metadata.append(
                            {
                                "filename": out_name,
                                "pdf_id": pdf_id,
                                "page_idx": page_idx,
                                "type": btype_clean,
                                "bbox_scaled": [left, top, right, bottom],
                                "bbox_relative": rel_bbox,
                            }
                        )
                    except Exception as e:
                        print(f"Failed to save {out_path}: {e}")
                    continue

                # Handle images and tables (existing logic)
                # Group sub-blocks by their group_id (caption+body)
                groups = {}
                for sub in block.get("blocks", []):
                    gid = sub.get("group_id", 0)
                    groups.setdefault(gid, []).append(sub)

                # Crop each group region
                for gid, subblocks in groups.items():
                    # Try to extract the figure/table name from the caption
                    caption_text = None
                    for sub in subblocks:
                        if (
                            sub.get("type") in ("image_caption", "table_caption")
                        ) and sub.get("lines"):
                            for line in sub["lines"]:
                                for span in line.get("spans", []):
                                    if span.get("type") == "text" and ":" in span.get(
                                        "content", ""
                                    ):
                                        # Extract the part before the colon
                                        match = re.match(
                                            r"([A-Za-z]+\s*\d+)",
                                            span["content"].split(":")[0].strip(),
                                        )
                                        if match:
                                            caption_text = match.group(1).replace(
                                                " ", ""
                                            )
                                        else:
                                            # fallback: use everything before colon, no spaces
                                            caption_text = (
                                                span["content"]
                                                .split(":")[0]
                                                .replace(" ", "")[:10]
                                            )
                                        break
                                if caption_text:
                                    break
                        if caption_text:
                            break
                    if not caption_text:
                        caption_text = "noname"

                    x0 = min(sb["bbox"][0] for sb in subblocks)
                    y0 = min(sb["bbox"][1] for sb in subblocks)
                    x1 = max(sb["bbox"][2] for sb in subblocks)
                    y1 = max(sb["bbox"][3] for sb in subblocks)
                    # Scale from PDF points (72 dpi) to specified dpi
                    left = x0 * scale
                    top = y0 * scale
                    right = x1 * scale
                    bottom = y1 * scale
                    crop = img.crop((left, top, right, bottom))
                    out_name = f"{pdf_id}_{page_idx}_{btype}_{caption_text.lower()}.png"
                    out_path = os.path.join(output_dir, out_name)
                    try:
                        crop.save(out_path)
                        # Save metadata
                        rel_bbox = [
                            left / page_width,
                            top / page_height,
                            right / page_width,
                            bottom / page_height,
                        ]
                        extracted_metadata.append(
                            {
                                "filename": out_name,
                                "pdf_id": pdf_id,
                                "page_idx": page_idx,
                                "type": btype,
                                "caption": caption_text,
                                "bbox_scaled": [left, top, right, bottom],
                                "bbox_relative": rel_bbox,
                            }
                        )
                    except Exception as e:
                        print(f"Failed to save {out_path}: {e}")

    # Save metadata JSON
    meta_path = os.path.join(output_dir, "extracted_metadata.json")
    try:
        with open(meta_path, "w") as mf:
            json.dump(extracted_metadata, mf, indent=2)
        print(f"Saved metadata to {meta_path}")
    except Exception as e:
        print(f"Failed to save metadata JSON: {e}")


def main():
    parser = argparse.ArgumentParser(description="Extract figures and tables from MinerU output")
    parser.add_argument("--mineru-dir", default=os.getenv("MINERU_DIR", "mineru_output"), help="Directory containing MinerU output")
    parser.add_argument("--pdf-dir", default=os.getenv("PDF_DIR", "pdf"), help="Directory containing PDF files")
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_DIR", "suppl_images"), help="Output directory for extracted images")
    parser.add_argument("--dpi", type=int, default=int(os.getenv("DPI", "144")), help="DPI for image extraction")
    
    args = parser.parse_args()
    
    extract_figures_tables(
        mineru_dir=args.mineru_dir,
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        dpi=args.dpi
    )


if __name__ == "__main__":
    main()
