import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from tqdm import tqdm
import argparse


class EvidenceClaim(BaseModel):
    source: str
    statement: str


class TargetActionOption(BaseModel):
    letter: str
    attribute: str
    target: str
    other_involved: str | None = None
    action: str
    edit_statement: str
    reason: str


class TargetActionAnswers(BaseModel):
    answers: list[TargetActionOption]


analysis_system_prompt_default = """You are a system that converts multiple choice question answers into Evidence-Claim JSON format.

Evidence-Claim JSON format:
```json
{
  "letter": "A" | "B" | "C" | "D",
  "attribute": str,
  "claim": {
    "source": "expectation" | str,
    "statement": str
  },
  "evidence": {
    "source": str,
    "statement": str
  },
}
```

There are two patterns of answer options:

Pattern 1: One part of the answer makes a claim that is contradicted by evidence in another part

Example:
```json
{
  "letter": "C", // The letter of the answer option
  "attribute": "optimal trade-off", // The attribute in the center of the answer option (e.g. rank parameter, complexity, name, etc.)
  "claim": {
    "source": "caption", // The source the claim about the attribute is based on (e.g., caption, text, figure_1 etc.)
    "statement": "at 128 tokens" // A brief 2-3 words description
  },
  "evidence": {
    "source": "plot", // The source the evidence about the attribute contradicting the claim is based on (e.g., plot, table, equation_2 etc.)
    "statement": "not visible at 128 tokens" // A brief 2-3 words description
  },
}

Pattern 2: One part of the answer makes a claim that contradicts common expectations to scientific correctness

Example:
```json
{
  "letter": "A",
  "attribute": "legend",
  "claim": {
    "source": "expectation", // In that case, the source for claim is always "expectation"
    "statement": "shouldn't occlude plot" 
  },
  "evidence": {
    "source": "figure_8",
    "statement": "occludes plot"
  },
}
```

Given:
- The question
- The answer options with letters (A, B, C, D)
- The correct answer letter
- The visual elements relevant to the inconsistency

Convert each multiple choice question answer (A, B, C, D) into the Target-Action JSON format. Ensure that the answer letters remain consistent with the input. Keep the JSON output concise. Do not use adjectives or any other descriptive language. The goal is to remove linguistic cues and focus on the core content of each answer option."""

analysis_system_prompt_edit = """You are a system that converts multiple choice question answers about inconsistencies in scientific papers into Target-Action JSON format. The goal is to identify what needs to be changed in the paper to resolve the inconsistency.

Target-Action JSON format:
```json
{
  "letter": "A" | "B" | "C" | "D",
  "attribute": str, // the core element at issue (e.g., legend, methods evaluated, F1 scores)
  "target": str, // where the edit is applied (e.g., caption, figure_4b, table_5, equation_2)
  "other_involved": str // (optional) other elements involved in the inconsistency, comma-separated
  "action": "modify" | "remove" | "add" | "reposition" | "replace",
  "edit_statement": str, // short 2-3 words description of the needed change (exclude word from action)
  "reason": str // why the change is needed in 2-3 words
}
```

Example:
```json
{
  "letter": "C",
  "attribute": "windows",
  "target": "figure_1b",
  "other_involved": "figure_1a",
  "action": "modify",
  "edit_statement": "align door position",
  "reason": "different"
}
```

Given:
- The question
- The answer options with letters (A, B, C, D)
- The correct answer letter
- The visual elements relevant to the inconsistency

Convert each multiple choice question answer (A, B, C, D) into the Target-Action JSON format. Ensure that the answer letters remain consistent with the input. Keep the JSON output concise. Do not use adjectives or any other descriptive language. Most important is to remove linguistic cues and focus on the core content of each answer option.
"""

analysis_user_prompt = """{question}

A) {A}
B) {B}
C) {C}
D) {D}

Correct answer: {correct_letter})

Visual elements: {visual_elements}"""
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Perform multiturn debiasing on MCQs")
    parser.add_argument("--input-json", default=os.getenv("INPUT_JSON", "annotations.json"), help="Input JSON file with annotations")
    parser.add_argument("--output-json", default=os.getenv("OUTPUT_JSON", "json_expectation_edit_llama.json"), help="Output JSON file")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY"), help="API key")
    parser.add_argument("--model", default=os.getenv("MODEL", "google/gemini-2.5-flash"), help="Model to use")
    
    args = parser.parse_args()
    
    if not args.api_key:
        raise ValueError("API key must be provided via --api-key or GEMINI_API_KEY env var")

    client = OpenAI(
        api_key=args.api_key,
        base_url="https://openrouter.ai/api/v1",  # We used OpenRouter as a proxy to access Gemini via the OpenAI API
    )

    with open(args.input_json, "r") as f:
        annotations = json.load(f)

    for key, entries in tqdm(annotations.items()):
        for idx, entry in enumerate(entries):
            try:
                mcq = entry["mcq"]["default_generic"]
                visual_elements = ", ".join(entry["visual_elements"])
                question = mcq["question"]
                answers = [mcq["correct"]] + mcq["incorrect"]
                letters = mcq["letters"]
                letter_answer_map = {
                    letter: answer for letter, answer in zip(letters, answers)
                }

                # Format the analysis prompt
                analysis_text = analysis_user_prompt.format(
                    question=question,
                    correct_letter=letters[0],
                    visual_elements=visual_elements,
                    **letter_answer_map,
                )

                messages = [
                    {"role": "system", "content": analysis_system_prompt_edit},
                    {"role": "user", "content": analysis_text},
                ]

                response = client.chat.completions.parse(
                    model=args.model,
                    messages=messages,
                    response_format=TargetActionAnswers,
                )
                final_response = response.choices[0].message.parsed

                # Update the entry with the refined answers

                new_letter_answer_map = {ans.letter: ans for ans in final_response.answers}

                annotations[key][idx]["mcq"]["edit_generic"] = {
                    "question": "What action needs to be taken to resolve the inconsistency in these parts of a scientific paper?",
                    "correct": new_letter_answer_map[letters[0]].model_dump_json(),
                    "incorrect": [
                        new_letter_answer_map[letter].model_dump_json()
                        for letter in letters[1:]
                    ],
                    "letters": letters,
                }
            except Exception as e:
                print(f"Failed for key {key}, idx {idx}: {e}")
                continue

        with open(args.output_json, "w") as f:
            json.dump(annotations, f, indent=2)

if __name__ == "__main__":
    main()
