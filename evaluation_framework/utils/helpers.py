import base64
import io
import os
import math

from PIL import Image
from pdf2image import convert_from_path
import json

from utils.types import (
    MCQItem,
    TextInconsistencyPart,
    ImageInconsistencyPart,
    AnnotationEntry,
)


def prepare_answers(mcq: MCQItem, question_type: str) -> tuple[list[str], str]:
    answers = [mcq.correct] + mcq.incorrect
    letters = mcq.letters
    letter_to_answer = dict(zip(letters, answers))
    # Sort by letter order (A, B, C, D)
    sorted_letters = sorted(letter_to_answer.keys())
    if "binary" in question_type:
        answer_options = [
            f"{letter}) {letter_to_answer[letter]}" for letter in sorted_letters
        ]
    else:
        answer_options = [f"{letter_to_answer[letter]}" for letter in sorted_letters]
    # Find correct letter
    correct_letter = letters[0]
    return answer_options, correct_letter


def convert_image_to_base64(image_path: str) -> str:
    """Reads an image, encodes it to base64, and returns the string."""
    try:
        with Image.open(image_path) as image:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except FileNotFoundError:
        print(f"Image not found: {image_path}")
        return None
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None


def extract_pdf_pages(
    pdf_path: str, max_pages: int = 1000, resolution: int = 144
) -> list[Image.Image]:
    """Extract all pages from a PDF as PIL Images."""
    try:
        images = convert_from_path(pdf_path, dpi=resolution, last_page=max_pages)
        return images
    except Exception as e:
        print(f"Error extracting pages from {pdf_path}: {e}")
        return []


def concat_images(images: list[Image.Image], column_num: int = 3) -> Image.Image:
    """Concatenate a list of PIL Images into a single image in a grid layout."""
    if not images:
        return None

    # Calculate dimensions
    if column_num == 1:
        total_height = images[0].height * len(images)
        total_width = images[0].width
    else:
        rows = math.ceil(len(images) / column_num)
        total_height = images[0].height * rows
        total_width = images[0].width * column_num

    # Create the concatenated image
    concatenated_image = Image.new("RGB", (total_width, total_height), "white")

    x_offset, y_offset = 0, 0
    for cnt, image in enumerate(images):
        concatenated_image.paste(image, (x_offset, y_offset))
        x_offset += image.width
        if (cnt + 1) % column_num == 0:
            y_offset += image.height
            x_offset = 0

    return concatenated_image


def convert_whole_doc_to_base64_list(
    pdf_path: str,
    max_images: int = 5,
    column_num: int = 3,
    max_pages: int = 1000,
    resolution: int = 144,
) -> list[str]:
    """Convert entire PDF document to up to max_images concatenated base64 images."""
    try:
        all_pages = extract_pdf_pages(pdf_path, max_pages, resolution)
        if not all_pages:
            return []

        # Calculate how many pages per image
        pages_per_image = math.ceil(len(all_pages) / max_images)

        base64_images = []
        for i in range(0, len(all_pages), pages_per_image):
            # Get the pages for this batch
            batch_pages = all_pages[i : i + pages_per_image]

            # Concatenate this batch into a single image
            concatenated_image = concat_images(batch_pages, column_num)
            if concatenated_image is None:
                continue

            # Convert to base64
            buffered = io.BytesIO()
            concatenated_image.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            base64_images.append(img_base64)

            # Stop if we've reached max_images
            if len(base64_images) >= max_images:
                break

        return base64_images
    except Exception as e:
        print(f"Error converting whole document {pdf_path} to base64 list: {e}")
        return []


def convert_whole_doc_to_base64(
    pdf_path: str, column_num: int = 3, max_pages: int = 1000, resolution: int = 144
) -> str:
    """Convert entire PDF document to a single concatenated base64 image."""
    try:
        images = extract_pdf_pages(pdf_path, max_pages, resolution)
        if not images:
            return None

        concatenated_image = concat_images(images, column_num)
        if concatenated_image is None:
            return None

        buffered = io.BytesIO()
        concatenated_image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Error converting whole document {pdf_path} to base64: {e}")
        return None


def get_list_of_context(
    annotation: AnnotationEntry,
    id: int,
    whole_page: bool = False,
    whole_doc: bool = False,
) -> list[dict[str, str]]:
    context_parts = []

    # If whole_doc is True, return the entire document as up to 5 concatenated images
    if whole_doc:
        pdf_path = os.path.join(os.getenv("PDF_DIR", "pdf"), id + ".pdf")
        img_base64_list = convert_whole_doc_to_base64_list(pdf_path)
        for img_base64 in img_base64_list:
            if img_base64:
                context_parts.append({"type": "image", "content": img_base64})
        return context_parts

    for part in annotation.inconsistency_parts:
        if isinstance(part, ImageInconsistencyPart):
            if whole_page:
                pdf_path = os.path.join(os.getenv("PDF_DIR", "pdf"), id + ".pdf")
                images = convert_from_path(
                    pdf_path, dpi=144, first_page=part.page, last_page=part.page
                )
                if images:
                    buffered = io.BytesIO()
                    images[0].save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    context_parts.append({"type": "image", "content": img_base64})
            else:
                image_path = os.path.join(
                    os.getenv("IMAGE_DIR", "images"), part.image_id + ".png"
                )
                context_parts.append(
                    {"type": "image", "content": convert_image_to_base64(image_path)}
                )
        elif isinstance(part, TextInconsistencyPart):
            if whole_page:
                pdf_path = os.path.join(os.getenv("PDF_DIR", "pdf"), id + ".pdf")
                try:
                    images = convert_from_path(
                        pdf_path, dpi=144, first_page=part.page, last_page=part.page
                    )
                    if images:
                        buffered = io.BytesIO()
                        images[0].save(buffered, format="JPEG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode(
                            "utf-8"
                        )
                        context_parts.append({"type": "image", "content": img_base64})
                except Exception as e:
                    print(f"Error extracting page {part.page} from {pdf_path}: {e}")
            else:
                context_parts.append({"type": "text", "content": part.content})
    return context_parts


def merge_binary_results(binary_file_1: str, binary_file_2: str) -> str:
    if os.path.dirname(os.path.abspath(binary_file_1)) != os.path.dirname(
        os.path.abspath(binary_file_2)
    ):
        raise ValueError("Binary files must be in the same directory")
    with open(binary_file_1, "r") as f1, open(binary_file_2, "r") as f2:
        results1 = json.load(f1)
        results2 = json.load(f2)

    # Build a lookup for results2 by (id, idx)
    results2_lookup = {(item["id"], item["idx"]): item for item in results2}

    merged_results = []
    for item1 in results1:
        key = (item1["id"], item1["idx"])
        item2 = results2_lookup.get(key)
        if not item2:
            raise ValueError(f"Missing item in results2 for key: {key}")

        merged_prediction = item1["prediction"] + item2["prediction"]
        correct_letter = item1["correct_letter"] + item2["correct_letter"]
        is_correct = merged_prediction == correct_letter

        merged_results.append(
            {
                "id": item1["id"],
                "idx": item1["idx"],
                "prediction": merged_prediction,
                "correct_letter": correct_letter,
                "is_correct": is_correct,
            }
        )

    output_path = os.path.join(os.path.dirname(binary_file_1), "merged_results.json")
    with open(output_path, "w") as fout:
        json.dump(merged_results, fout, indent=2)

    return output_path
