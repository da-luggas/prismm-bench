import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tqdm import tqdm
import argparse

load_dotenv()


class MCQSchema(BaseModel):
    question: str = Field(..., description="The multiple choice question text")
    correct: str = Field(..., description="The correct answer option")
    incorrect: list[str] = Field(..., description="List of incorrect answer options")


def main():
    parser = argparse.ArgumentParser(description="Generate multiple choice questions for inconsistencies")
    parser.add_argument("--input-json", default=os.getenv("INPUT_JSON", "new_annotations_no_mcq.json"), help="Input JSON file with annotations")
    parser.add_argument("--images-dir", default=os.getenv("IMAGES_DIR", "images"), help="Directory containing annotation images")
    parser.add_argument("--output-json", default=os.getenv("OUTPUT_JSON", "new_annotations_with_mcq.json"), help="Output JSON file")
    parser.add_argument("--question-key", default=os.getenv("QUESTION_KEY", "default"), help="Key for the MCQ in JSON")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY"), help="Gemini API key")
    parser.add_argument("--model", default=os.getenv("MODEL", "gemini-2.5-flash"), help="Gemini model to use")
    
    args = parser.parse_args()
    
    if not args.api_key:
        raise ValueError("API key must be provided via --api-key or GEMINI_API_KEY env var")
    
    INCONSISTENCY_JSON = args.input_json
    ANNOTATION_IMAGES_DIR = args.images_dir
    OUTPUT_JSON = args.output_json
    QUESTION_KEY = args.question_key

    client = genai.Client(api_key=args.api_key)

PROMPT_TEMPLATE = """
You are a visual assistant that can analyze image and text excerpts from scientific papers. You receive either one image, two images or a pair of image and text that contain a visual inconsistency that reviewers of the paper found to be an error in the paper. Alongside the image/text information, you'll receive an explanation of what the inconsistency is. Based on these, generate a multiple-choice question testing the model's ability to detect the inconsistency. Follow these strict rules:

- The question should directly reference the provided content of the paper
- There must be exactly 4 answer choices
- Only one answer should correctly describe the inconsistency
- The 3 distractors must be plausible but incorrect. They should either be incorrect due to omission or subtle misinterpretations of the content
- Do not invent details beyond what's provided
- Clearly label the correct answer
---
"""


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def get_image_path(image_id):
    try:
        png_path = os.path.join(ANNOTATION_IMAGES_DIR, f"{image_id}.png")
        if os.path.exists(png_path):
            return png_path
        jpg_path = os.path.join(ANNOTATION_IMAGES_DIR, f"{image_id}.jpg")
        if os.path.exists(jpg_path):
            return jpg_path
        return None
    except Exception as e:
        print(f"WARNING: Error in get_image_path for image_id {image_id}: {e}")
        return None


def prepare_content(inconsistency):
    # Returns a list of Gemini API content parts: images as types.Part, text as string
    try:
        parts = inconsistency.get("inconsistency_parts", [])
        content = []
        for part in parts:
            try:
                if part.get("type") == "image":
                    img_path = get_image_path(part.get("image_id"))
                    if img_path:
                        mime_type = (
                            "image/png" if img_path.endswith(".png") else "image/jpeg"
                        )
                        with open(img_path, "rb") as f:
                            image_bytes = f.read()
                        content.append(
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                        )
                elif part.get("type") == "text":
                    text = part.get("content", "")
                    if text:
                        content.append("Text part from inconsistency: " + text)
            except Exception as part_exc:
                print(f"WARNING: Error processing part in prepare_content: {part_exc}")
                continue
        return content
    except Exception as e:
        print(f"WARNING: Error in prepare_content: {e}")
        return []


def call_genai_api(client: genai.Client, content_parts, explanation: str):
    try:
        # Compose the prompt: image(s)/text + explanation + instructions
        prompt = PROMPT_TEMPLATE + "\nExplanation:\n" + explanation
        contents = [prompt] + content_parts
        response = client.models.generate_content(
            model=args.model,
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_schema": MCQSchema,
            },
        )
        return response.parsed, (
            response.usage_metadata.prompt_token_count,
            response.usage_metadata.total_token_count,
        )
    except Exception as e:
        print(f"WARNING: Error in call_genai_api: {e}")

        # Return dummy MCQSchema-like object and zero tokens
        class Dummy:
            question = None
            correct = None
            incorrect = None

        return Dummy(), (0, 0)


def main():
    parser = argparse.ArgumentParser(description="Generate multiple choice questions for inconsistencies")
    parser.add_argument("--input-json", default=os.getenv("INPUT_JSON", "new_annotations_no_mcq.json"), help="Input JSON file with annotations")
    parser.add_argument("--images-dir", default=os.getenv("IMAGES_DIR", "images"), help="Directory containing annotation images")
    parser.add_argument("--output-json", default=os.getenv("OUTPUT_JSON", "new_annotations_with_mcq.json"), help="Output JSON file")
    parser.add_argument("--question-key", default=os.getenv("QUESTION_KEY", "default"), help="Key for the MCQ in JSON")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY"), help="Gemini API key")
    parser.add_argument("--model", default=os.getenv("MODEL", "gemini-2.5-flash"), help="Gemini model to use")
    
    args = parser.parse_args()
    
    if not args.api_key:
        raise ValueError("API key must be provided via --api-key or GEMINI_API_KEY env var")
    
    INCONSISTENCY_JSON = args.input_json
    ANNOTATION_IMAGES_DIR = args.images_dir
    OUTPUT_JSON = args.output_json
    QUESTION_KEY = args.question_key

    client = genai.Client(api_key=args.api_key)
    data = load_json(INCONSISTENCY_JSON)
    updated = {}
    input_token_count = 0
    total_token_count = 0
    with tqdm(data.items(), desc="Processing images") as pbar:
        for image_id, inconsistencies in pbar:
            updated[image_id] = []
            for inconsistency in inconsistencies:
                try:
                    content_parts = prepare_content(inconsistency)
                    explanation = inconsistency.get("description", "")
                    try:
                        mcq, (input_tokens, total_tokens) = call_genai_api(
                            client, content_parts, explanation
                        )
                        input_token_count += input_tokens
                        total_token_count += total_tokens
                        if "mcq" not in inconsistency:
                            inconsistency["mcq"] = {}
                        inconsistency["mcq"][QUESTION_KEY] = {
                            "question": mcq.question,
                            "correct": mcq.correct,
                            "incorrect": mcq.incorrect,
                        }
                    except Exception as api_exc:
                        print(
                            f"WARNING: Failed to generate MCQ for image_id {image_id}: {api_exc}"
                        )
                        if "mcq" not in inconsistency:
                            inconsistency["mcq"] = {}
                        inconsistency["mcq"][QUESTION_KEY] = {
                            "question": None,
                            "correct": None,
                            "incorrect": None,
                        }
                    updated[image_id].append(inconsistency)
                    # Correct cost calculation:
                    input_cost = input_token_count * 0.3 / 1_000_000
                    output_cost = (
                        (total_token_count - input_token_count) * 2.5 / 1_000_000
                    )
                    total_cost = input_cost + output_cost
                    pbar.set_postfix(cost=f"${total_cost:.3f}")
                except Exception as e:
                    print(
                        f"WARNING: Error processing inconsistency for image_id {image_id}: {e}"
                    )
                    continue
    save_json(updated, OUTPUT_JSON)
    print(f"Saved multiple choice questions to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
