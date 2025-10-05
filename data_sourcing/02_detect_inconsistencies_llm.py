import json
import os
import pickle
from typing import Any, Dict, List
from dotenv import load_dotenv
from openreview.api import Note
import openai
from tqdm.auto import tqdm
from pydantic import BaseModel, Field
import re
import argparse

load_dotenv()

model = "mistralai/mistral-nemo"  # default


def sort_forum_for_paper(post: Note) -> List[Dict[str, Any]]:
    replies = post.details.get("replies", [])

    # Dictionary to store the hierarchical structure (parent_id -> list of child reply dictionaries)
    # Initialize with the main post's forum ID
    children_map: Dict[str, List[Dict[str, Any]]] = {post.forum: []}

    # Populate the children_map by iterating through all replies
    for reply in replies:
        parent_id = reply.get("replyto")
        if parent_id:
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(reply)

    # Recursive function to build the sorted hierarchical tree
    def build_tree(parent_id: str) -> List[Dict[str, Any]]:
        direct_replies = children_map.get(parent_id, [])

        # Sort direct replies chronologically using 'cdate'
        sorted_replies = sorted(direct_replies, key=lambda reply: reply.get("cdate", 0))

        # For each sorted reply, recursively build its subtree
        for reply in sorted_replies:
            reply["children"] = build_tree(reply["id"])

        return sorted_replies

    # Build the tree starting from the main post's forum ID
    sorted_hierarchical_replies = build_tree(post.forum)

    return sorted_hierarchical_replies


client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), base_url="https://openrouter.ai/api/v1"
)


class Inconsistency(BaseModel):
    has_inconsistency: bool = Field(
        default=False, description="Whether the review contains an inconsistency."
    )
    inconsistencies: list[str] = Field(
        default=[],
        description="The part of the review that mentions the inconsistency.",
    )


def call_openai(prompt: str) -> Dict[str, Any]:
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "user",
                "content": """
                    You are an AI assistant specialized in analyzing academic paper reviews. Your task is to identify inconsistencies between visual elements (such as figures and tables) and their corresponding text descriptions in the original paper being reviewed. These inconsistencies should be explicitly mentioned or highlighted by the reviewer in their review.

                    Here is the paper review you need to analyze:

                    <review>
                    {prompt}
                    </review>

                    Instructions:
                    1. Carefully read through the entire review.
                    2. Focus exclusively on identifying instances where the reviewer mentions inconsistencies in the original paper between visual elements (figures, tables, graphs, etc.) and their corresponding text descriptions or inconsistencies between visual elements themselves (e.g. captions, legends, etc.).
                    3. For each identified inconsistency:
                        a. Determine the type of mismatch (e.g., figure legend vs. content, text results vs. figure data, table values vs. text mentions)
                        b. Note the specific location or reference in the original paper (e.g., figure number, table number, page number if available)
                        c. Briefly describe the nature of the inconsistency as mentioned by the reviewer
                    4. Disregard any general inconsistencies that are not strictly related to vision-text or vision-vision mismatches in the original paper.

                    Before providing your final response, analyze the review in <review_analysis> tags:
                    1. List all mentions of visual elements in the review.
                    2. For each visual element, note whether the reviewer mentions any inconsistencies with the text or another visual element.
                    3. For identified inconsistencies, write down the specific quote from the review that mentions it.

                    This analysis will help ensure a thorough examination of the review and prevent misinterpretation of inconsistencies within the review itself versus those in the original paper.

                    After your analysis, present your findings in JSON format. Each identified inconsistency should be an object in an array, with the following structure:

                    {{
                    "has_inconsistency": boolean,
                    "inconsistencies": [
                        "string (brief explanation of the inconsistency, always including the place in the original paper where it is located and as close to the reviewer's text as possible)",
                        // Additional inconsistencies...
                    ]
                    }}

                    If no inconsistencies in the original paper are mentioned by the reviewer, return:

                    {{
                    "has_inconsistency": false,
                    "inconsistencies": []
                    }}

                    Example of desired output structure (purely for format, not content):

                    {{
                    "has_inconsistency": true,
                    "inconsistencies": [
                        "Table 1: The performance for model A is 69.74 percent but the text mentions 65.47 percent.",
                        "Figure 1: The text refers to Group 1 and Group 0, but Figure 1 labels the groups as Group 1 and Group 2."
                    ]
                    }}

                    Remember to focus solely on vision-text and vision-vision mismatches in the original paper as mentioned by the reviewer. Provide clear, concise descriptions that make it easy for researchers to locate and verify the inconsistencies in the original paper based on the review's comments.
                                    """.format(prompt=prompt),
            }
        ],
        response_format=Inconsistency,
    )

    try:
        return response.parsed.model_dump()
    except Exception:
        # Fallback: extract JSON code block if present
        match = re.search(
            r"```json\s*(\{.*?\})\s*```", response.choices[0].message.content, re.DOTALL
        )
        if match:
            try:
                return json.loads(match.group(1))
            except Exception as e:
                print("Failed to parse extracted JSON code block.")
                print(match.group(1))
                raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect inconsistencies in reviews using LLM")
    parser.add_argument("--input-file", default=os.getenv("INPUT_FILE", "iclr_2025_raw.pkl"), help="Input pickle file with submissions")
    parser.add_argument("--annotations-file", default=os.getenv("ANNOTATIONS_FILE", "../annotations.json"), help="Annotations JSON file")
    parser.add_argument("--output-file", default=os.getenv("OUTPUT_FILE", "inconsistencies.json"), help="Output JSON file for inconsistencies")
    parser.add_argument("--model", default=os.getenv("MODEL", "mistralai/mistral-nemo"), help="LLM model to use")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--save-every", type=int, default=int(os.getenv("SAVE_EVERY", "10")), help="Save every N processed reviews")
    
    args = parser.parse_args()
    
    if not args.api_key:
        raise ValueError("API key must be provided via --api-key or OPENAI_API_KEY env var")
    
    # Update client with provided api_key
    global client, model
    client = openai.OpenAI(api_key=args.api_key, base_url="https://openrouter.ai/api/v1")
    model = args.model
    
    # Open one of the conference data
    with open(args.input_file, "rb") as file:
        posts = pickle.load(file)

    all_replies = []
    for post in posts:
        all_replies.append(sort_forum_for_paper(post))

    # Check all reviews that have no rebuttal
    no_rebuttal = []
    for post in all_replies:
        for reply in post:
            if any(
                "Official_Review" in invitation or "Official_Comment" in invitation
                for invitation in reply["invitations"]
            ):
                if reply["forum"] == reply["replyto"]:
                    if not reply["children"]:
                        no_rebuttal.append(reply)

    no_rebuttal_only_reviews = [
        r for r in no_rebuttal if any("Reviewer" in f for f in r["signatures"])
    ]

    with open(args.annotations_file, "rb") as f:
        existing_annotations = json.load(f)

        annotation_keys = list(existing_annotations.keys())

    no_rebuttal_only_reviews = [
        r for r in no_rebuttal_only_reviews if r["forum"] not in annotation_keys
    ]

    # Load existing inconsistencies if available
    inconsistencies_path = args.output_file
    if os.path.exists(inconsistencies_path):
        with open(inconsistencies_path, "r") as f:
            inconsistencies = json.load(f)
    else:
        inconsistencies = {}

    reviews_to_process = [
        i for i in no_rebuttal_only_reviews if i["forum"] not in inconsistencies
    ]

    save_every = args.save_every
    processed = 0

    for idx, review in tqdm(
        enumerate(reviews_to_process),
        desc="LLM-based inconsistency search",
        total=len(reviews_to_process),
    ):
        try:
            prompt_parts = []
            for key in ["weaknesses", "questions"]:
                value = review["content"].get(key, {}).get("value")
                if value:
                    prompt_parts.append(value)
            prompt = "\n\n".join(prompt_parts)
            result = call_openai(prompt)
            forum = review["forum"]

            if forum not in inconsistencies:
                inconsistencies[forum] = {
                    "has_inconsistency": False,
                    "inconsistencies": [],
                }

            if result.get("has_inconsistency", False):
                inconsistencies[forum]["has_inconsistency"] = True

            inconsistencies[forum]["inconsistencies"].extend(
                result.get("inconsistencies", [])
            )

            processed += 1
            # Save after every save_every processed reviews
            if processed % save_every == 0:
                with open(inconsistencies_path, "w") as f:
                    json.dump(inconsistencies, f, indent=2)
        except Exception as e:
            print(f"Error processing review {idx}: {e}")

    # Final save
    with open(inconsistencies_path, "w") as f:
        json.dump(inconsistencies, f, indent=2)
