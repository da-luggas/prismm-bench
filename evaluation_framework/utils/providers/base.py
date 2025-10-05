import json
import os
from abc import ABC, abstractmethod
from typing import Generator, Tuple, List, Dict, Any

from utils.helpers import (
    get_list_of_context,
    prepare_answers,
    convert_image_to_base64,
)
from utils.prompts import after_question_prompt
from utils.types import AnnotationEntry, MCQItem


GenericItem = Dict[str, Any]


class BaseMCQProvider(ABC):
    """Base class encapsulating shared MCQ inference preparation logic.

    This class does NOT implement the actual model invocation. Subclasses
    should consume the generic context items produced here and transform
    them into provider specific message formats / requests.
    """

    def __init__(self, annotation_file: str, model: str):
        self.annotation_file = annotation_file
        self.model = model
        self.responses: List[dict] = []

    @abstractmethod
    def run_mcq_inference(
        self,
        model_id: str,
        question_type: str,
        whole_page: bool = False,
        whole_doc: bool = False,
        without_context: bool = False,
    ) -> None:
        """Run MCQ inference for the given parameters."""
        pass

    @abstractmethod
    def _handle_one_annotation(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
    ) -> None:
        """Handle a single annotation for inference."""
        pass

    @abstractmethod
    def _handle_one_annotation_without_context(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
    ) -> None:
        """Handle a single annotation for inference without context."""
        pass

    @abstractmethod
    def _handle_one_part_pair_annotation(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
    ) -> None:
        """Handle a single part pair annotation for inference."""
        pass

    # ------------------------------------------------------------------
    # Annotation iteration helpers
    # ------------------------------------------------------------------
    def _load_annotations(self) -> dict:
        with open(self.annotation_file, "r") as f:
            return json.load(f)

    def iter_annotations(
        self, question_type: str, whole_page: bool, whole_doc: bool = False
    ) -> Generator[Tuple[str, int, AnnotationEntry], None, None]:
        data = self._load_annotations()
        # Only show progress bar outside base (subclasses decide) to avoid dependency.
        for key, entries in data.items():
            for idx, entry in enumerate(entries):
                ann = AnnotationEntry(**entry)
                if question_type == "part_pair" and not ann.mcq.part_pair:
                    continue
                yield key, idx, ann

    # ------------------------------------------------------------------
    # Context builders (provider-agnostic) -> list of generic items
    # Generic item schema:
    #   Text: {"kind": "text", "text": str}
    #   Image: {"kind": "image", "base64": str}
    # ------------------------------------------------------------------
    def build_default_context(
        self,
        annotation: AnnotationEntry,
        id: str,
        question_type: str,
        whole_page: bool,
        whole_doc: bool = False,
    ) -> Tuple[List[GenericItem], str, List[str], str]:
        mcq_item: MCQItem = getattr(annotation.mcq, question_type)
        question = mcq_item.question
        answers, correct_letter = prepare_answers(mcq_item, question_type)
        parts = get_list_of_context(
            annotation, id=id, whole_page=whole_page, whole_doc=whole_doc
        )

        context_items: List[GenericItem] = []
        for p in parts:
            if p["type"] == "image":
                context_items.append({"kind": "image", "base64": p["content"]})
            else:
                context_items.append({"kind": "text", "text": p["content"]})

        # Append question + answers + final instruction
        context_items.append({"kind": "text", "text": question})
        for a in answers:
            context_items.append({"kind": "text", "text": a})
        context_items.append({"kind": "text", "text": after_question_prompt})
        return context_items, question, answers, correct_letter

    def build_without_context(
        self, annotation: AnnotationEntry, question_type: str
    ) -> Tuple[List[GenericItem], str, List[str], str]:
        mcq_item: MCQItem = getattr(annotation.mcq, question_type)
        question = mcq_item.question
        answers, correct_letter = prepare_answers(mcq_item, question_type)
        context_items: List[GenericItem] = []
        context_items.append({"kind": "text", "text": question})
        for a in answers:
            context_items.append({"kind": "text", "text": a})
        context_items.append({"kind": "text", "text": after_question_prompt})
        return context_items, question, answers, correct_letter

    def build_part_pair_context(
        self, annotation: AnnotationEntry, id: str
    ) -> Tuple[List[GenericItem], str]:
        mcq_item: MCQItem = getattr(annotation.mcq, "part_pair")
        # Guard
        if not mcq_item or not mcq_item.question or not mcq_item.correct:
            return [], ""

        question = mcq_item.question
        answer_options = [mcq_item.correct] + mcq_item.incorrect
        letters = mcq_item.letters
        letter_to_answer = dict(zip(letters, answer_options))
        sorted_letters = sorted(letter_to_answer.keys())
        answer_options = [letter_to_answer[letter_key] for letter_key in sorted_letters]
        correct_letter = sorted_letters[answer_options.index(mcq_item.correct)]

        items: List[GenericItem] = [
            {
                "kind": "text",
                "text": "You are provided with a part of a scientific paper:",
            }
        ]

        # Question may be image id or text
        if id in question:
            image_path = os.path.join(
                os.getenv("IMAGE_DIR", "images"), f"{question}.png"
            )
            img_b64 = convert_image_to_base64(image_path)
            items.append({"kind": "image", "base64": img_b64})
        else:
            items.append({"kind": "text", "text": question})

        items.append(
            {
                "kind": "text",
                "text": "The combination with one of the other parts within the same paper results in an inconsistency. Pick the letter of the correct answer option.",
            }
        )

        for i, image_id in enumerate(answer_options):
            letter = sorted_letters[i]
            items.append({"kind": "text", "text": f"{letter})"})
            if len(image_id.split("_")) < 4:
                image_path = os.path.join(
                    os.getenv("IMAGE_DIR", "images"), f"{image_id}.png"
                )
            else:
                image_path = os.path.join(
                    os.getenv("SUPPL_IMAGE_DIR", "suppl_images"), image_id + ".png"
                )
            img_b64 = convert_image_to_base64(image_path)
            items.append({"kind": "image", "base64": img_b64})

        items.append({"kind": "text", "text": after_question_prompt})
        # Store correct_letter as terminal text? We return separately.
        return items, correct_letter

    # ------------------------------------------------------------------
    # Utility to write results
    # ------------------------------------------------------------------
    def write_results(
        self,
        model_id: str,
        question_type: str,
        whole_page: bool,
        whole_doc: bool = False,
        without_context: bool = False,
    ) -> str:
        results_file = os.path.join(
            os.getenv("RESULTS_DIR", "results"),
            f"{model_id.replace('/', '-').replace('_','-')}_{question_type.replace('_', '-')}{'_fullpage' if whole_page else ''}{'_wholedoc' if whole_doc else ''}{'_without_context' if without_context else ''}.json",
        )
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, "w") as f:
            json.dump(self.responses, f, indent=4)
        return results_file
