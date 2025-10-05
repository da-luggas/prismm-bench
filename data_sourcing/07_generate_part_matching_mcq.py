import json
import os
import random
import re
from pathlib import Path
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate part matching MCQs")
    parser.add_argument("--annot-dir", default=os.getenv("ANNOT_DIR", "/Users/name/Desktop/Annotation Results"), help="Annotation directory")
    parser.add_argument("--annot-file", default=os.getenv("ANNOT_FILE", "annotations.json"), help="Annotations JSON file (relative to annot-dir)")
    parser.add_argument("--img-dir", default=os.getenv("IMG_DIR", "suppl_images"), help="Images directory (relative to annot-dir)")
    parser.add_argument("--out-file", default=os.getenv("OUT_FILE", "annotations_enriched.json"), help="Output JSON file (relative to annot-dir)")
    
    args = parser.parse_args()
    
    ANNOT_DIR = Path(args.annot_dir)
    ANNOT_FILE = ANNOT_DIR / args.annot_file
    IMG_DIR = ANNOT_DIR / args.img_dir
    OUT_FILE = ANNOT_DIR / args.out_file

    with open(ANNOT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_added = 0
    for paper_id, inconsistencies in list(data.items()):
        for obj in inconsistencies:
            # 1. Filter out all inconsistencies with caption or only
            if obj["category"] in ["caption", "only"]:
                mcq = obj.setdefault("mcq", {})
                # only set empty dict if part_pair missing
                mcq.setdefault("part_pair", {})
                continue

            parts = obj["inconsistency_parts"]

            # 2. Pick one inconsistency as question part, prefer text

            if len(parts) < 2:
                continue

            question_part = None
            for idx, part in enumerate(parts):
                if part["type"] == "text":
                    question_part = part
                    correct_part = parts[1] if idx == 0 else parts[0]
                    break

            if not question_part:
                question_part = parts[0]
                correct_part = parts[1]

            all_img_files = [
                f.name for f in IMG_DIR.iterdir() if f.is_file() and paper_id in f.name
            ]

            # Filter out noname
            all_img_files = [f for f in all_img_files if "noname" not in f]

            # Filter out correct
            correct_fig_name = (
                (
                    obj["visual_elements"][0]
                    if question_part["type"] == "text"
                    else obj["visual_elements"][1]
                )
                .lower()
                .replace(" ", "")
            )
            correct_modality = re.sub(r"\d+", "", correct_fig_name)
            correct_modality = "equation" if correct_modality == "()" else correct_modality
            correct_page = int(correct_part["page"])

            img_files = [
                f
                for f in all_img_files
                if correct_fig_name not in f.lower() and correct_modality in f.lower()
            ]

            # Sort by page proximity
            def extract_page(filename):
                return int(filename.split("_")[1])

            # Exclude same page results for equation to make sure they are not the same as correct (can't check automatically)
            if correct_modality == "equation":
                img_files = [f for f in img_files if extract_page(f) != correct_page]

            img_files.sort(key=lambda x: abs(extract_page(x) - correct_page))

            if len(img_files) < 3:
                # Use images from same paper but different modalities
                # Exclude correct modality and correct figure
                other_modality_imgs = [
                    f
                    for f in all_img_files
                    if correct_modality not in f.lower()
                    and correct_fig_name not in f.lower()
                ]
                # Sort by page proximity
                other_modality_imgs.sort(key=lambda x: abs(extract_page(x) - correct_page))
                # Add to img_files until we have at least 3
                img_files += other_modality_imgs[: max(0, 3 - len(img_files))]
                print(correct_part, img_files[:3])
                # If still not enough, raise error
                if len(img_files) < 3:
                    raise ValueError(
                        "Not enough candidate images found, even after searching other modalities in the same paper"
                    )

            distractors = img_files[:3]
            # Remove file ending in distractors
            distractors = [f[:-4] for f in distractors]

            mcq_block = obj.setdefault("mcq", {})
            mcq_block["part_pair"] = {
                "question": question_part["content"]
                if question_part["type"] == "text"
                else question_part["image_id"],
                "correct": correct_part["content"]
                if correct_part["type"] == "text"
                else correct_part["image_id"],
                "incorrect": distractors,
            }
            total_added += 1

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Done. Enriched {total_added} inconsistencies with MCQ data.")

if __name__ == "__main__":
    main()
