import json
import tempfile

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from utils.prompts import system_prompt
from utils.providers.base import BaseMCQProvider
from utils.types import AnnotationEntry, ReasoningLevel

load_dotenv()


class OpenAIBatchProvider(BaseMCQProvider):
    def __init__(
        self,
        api_key: str,
        annotation_file: str,
        model: str = "gpt-5",
        reasoning: ReasoningLevel = ReasoningLevel.HIGH,
        file_id: str = None,
        batch_id: str = None,
        max_batch_size_mb: float = 190.0,  # Conservative limit below 200MB
    ):
        super().__init__(annotation_file=annotation_file, model=model)
        self.annotation_file = annotation_file
        self.model = model
        self.api_key = api_key
        self.reasoning = reasoning
        self.file_id = file_id
        self.batch_id = batch_id
        self.batch_requests = []
        self.max_batch_size_mb = max_batch_size_mb

        # Support for multiple batch jobs
        self.batch_jobs = []  # List of {"file_id": str, "batch_id": str}

        self.client = OpenAI(api_key=api_key)

    def _estimate_request_size_mb(self, request):
        """Estimate the size of a single batch request in MB."""
        return len(json.dumps(request).encode("utf-8")) / (1024 * 1024)

    def _estimate_total_size_mb(self, requests):
        """Estimate the total size of all batch requests in MB."""
        total_size = 0
        for request in requests:
            total_size += self._estimate_request_size_mb(request)
        return total_size

    def _split_batch_requests(self, requests):
        """Split batch requests into chunks that don't exceed the size limit."""
        batches = []
        current_batch = []
        current_size_mb = 0.0

        for request in requests:
            request_size_mb = self._estimate_request_size_mb(request)

            # If adding this request would exceed the limit, start a new batch
            if (
                current_batch
                and (current_size_mb + request_size_mb) > self.max_batch_size_mb
            ):
                batches.append(current_batch)
                current_batch = [request]
                current_size_mb = request_size_mb
            else:
                current_batch.append(request)
                current_size_mb += request_size_mb

        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)

        return batches

    def _create_batch_from_requests(
        self, batch_requests, question_type, batch_num=None
    ):
        """Create a single batch job from a list of requests."""
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".jsonl", delete=True
        ) as tmpfile:
            batch_file = tmpfile.name
            for req in batch_requests:
                tmpfile.write(json.dumps(req) + "\n")

            batch_name = f"batch_{batch_num}" if batch_num is not None else "batch"
            print(
                f"Uploading '{batch_name}' ({len(batch_requests)} requests) to OpenAI..."
            )

            batch_input_file = self.client.files.create(
                file=open(batch_file, "rb"), purpose="batch"
            )
            print(f"File uploaded with ID: {batch_input_file.id}")

            print(f"Creating {batch_name} job...")
            batch = self.client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/v1/responses",
                completion_window="24h",
                metadata={
                    "question_type": question_type,
                    "batch_num": str(batch_num or 0),
                },
            )
            print(f"Batch created with ID: {batch.id}. Status: {batch.status}")

            return {"file_id": batch_input_file.id, "batch_id": batch.id}

    def run_mcq_inference(
        self,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
        without_context: bool = False,
    ) -> dict[str, str]:
        self.responses = []
        if whole_page and question_type == "part_pair":
            whole_page = False
            print("Whole page forced off as it is not supported for part_pair.")
        if whole_doc and question_type == "part_pair":
            whole_doc = False
            print("Whole doc forced off as it is not supported for part_pair.")

        iterator = (
            tqdm(
                self.iter_annotations(question_type, whole_page, whole_doc),
                desc="Preparing PDF pages",
            )
            if (whole_page or whole_doc) and question_type != "part_pair"
            else self.iter_annotations(question_type, whole_page, whole_doc)
        )
        for key, idx, ann in iterator:
            if without_context:
                self._handle_one_annotation_without_context(
                    id=key,
                    idx=idx,
                    annotation=ann,
                    question_type=question_type,
                    whole_page=whole_page,
                    whole_doc=whole_doc,
                    without_context=without_context,
                )
            elif question_type == "part_pair":
                self._handle_one_part_pair_annotation(
                    id=key,
                    idx=idx,
                    annotation=ann,
                    question_type=question_type,
                    whole_page=whole_page,
                    whole_doc=whole_doc,
                    without_context=without_context,
                )
            else:
                self._handle_one_annotation(
                    id=key,
                    idx=idx,
                    annotation=ann,
                    question_type=question_type,
                    whole_page=whole_page,
                    whole_doc=whole_doc,
                    without_context=without_context,
                )

        # Split batch requests if they're too large
        total_size_mb = self._estimate_total_size_mb(self.batch_requests)
        print(
            f"Total estimated size: {total_size_mb:.2f} MB for {len(self.batch_requests)} requests"
        )

        batch_splits = self._split_batch_requests(self.batch_requests)

        if len(batch_splits) > 1:
            print(
                f"⚠️  Large batch detected! Split {len(self.batch_requests)} requests into {len(batch_splits)} batch jobs"
            )
            for i, batch in enumerate(batch_splits):
                batch_size_mb = self._estimate_total_size_mb(batch)
                print(
                    f"  Batch {i + 1}: {len(batch)} requests (~{batch_size_mb:.2f} MB)"
                )
        else:
            print(f"Batch size is within limits ({total_size_mb:.2f} MB)")

        self.batch_jobs = []

        for i, batch_requests in enumerate(batch_splits):
            batch_info = self._create_batch_from_requests(
                batch_requests, question_type, batch_num=i + 1
            )
            self.batch_jobs.append(batch_info)

        # For backwards compatibility, set the first batch as the primary one
        if self.batch_jobs:
            self.batch_id = self.batch_jobs[0]["batch_id"]
            self.file_id = self.batch_jobs[0]["file_id"]

        return {
            "batch_jobs": self.batch_jobs,
            "file_id": self.file_id,  # Primary batch for backwards compatibility
            "batch_id": self.batch_id,  # Primary batch for backwards compatibility
        }

    def get_batch_results(self):
        self.responses = []

        # Use batch_jobs if available, otherwise fall back to single batch for backwards compatibility
        if self.batch_jobs:
            batch_jobs_to_process = self.batch_jobs
        elif self.file_id and self.batch_id:
            batch_jobs_to_process = [
                {"file_id": self.file_id, "batch_id": self.batch_id}
            ]
        else:
            raise ValueError(
                "No batch jobs found. file_id and batch_id must be set to retrieve results."
            )

        print(f"Processing results from {len(batch_jobs_to_process)} batch job(s)...")

        all_results = []
        for i, batch_job in enumerate(batch_jobs_to_process):
            print(
                f"Processing batch job {i + 1}/{len(batch_jobs_to_process)} (ID: {batch_job['batch_id']})..."
            )

            # Check if ready
            batch_response = self.client.batches.retrieve(batch_job["batch_id"])
            if batch_response.status != "completed":
                raise ValueError(
                    f"Batch job {batch_job['batch_id']} not ready yet. Status: {batch_response.status}"
                )

            # Get results from this batch
            file_response = self.client.files.content(
                batch_response.output_file_id
            ).text
            batch_results = [json.loads(line) for line in file_response.splitlines()]
            all_results.extend(batch_results)
            print(f"Retrieved {len(batch_results)} results from batch {i + 1}")

        print(f"Total results retrieved: {len(all_results)}")

        # Process all results
        question_type = None
        if all_results:
            question_type = all_results[0].get("question_type")

        for result in all_results:
            parts = result["custom_id"].split("_")
            if len(parts) == 6:
                id, idx, question_type, correct_letter, whole_page, without_context = (
                    parts
                )
                whole_doc = "False"  # Default for backwards compatibility
            else:
                (
                    id,
                    idx,
                    question_type,
                    correct_letter,
                    whole_page,
                    whole_doc,
                    without_context,
                ) = parts
            output = result.get("response", {}).get("body", {}).get("output", [])
            prediction = None
            for item in output:
                if item.get("type") == "message":
                    content = item.get("content", [])
                    for c in content:
                        if c.get("type") == "output_text":
                            prediction = c.get("text", "").strip("'.\" )").upper()
                            break
                    if prediction is not None:
                        break
            is_correct = prediction == correct_letter
            self.responses.append(
                {
                    "id": id,
                    "idx": idx,
                    "question_type": question_type,
                    "correct_letter": correct_letter,
                    "prediction": prediction,
                    "is_correct": is_correct,
                }
            )

        whole_page = whole_page == "True"
        whole_doc = whole_doc == "True"
        without_context = without_context == "True"

        # Write results to a results file
        self.write_results(
            self.model, question_type, whole_page, whole_doc, without_context
        )

    def get_batch_status(self):
        """Get the status of all batch jobs."""
        if self.batch_jobs:
            batch_jobs_to_check = self.batch_jobs
        elif self.file_id and self.batch_id:
            batch_jobs_to_check = [{"file_id": self.file_id, "batch_id": self.batch_id}]
        else:
            return {"error": "No batch jobs found"}

        statuses = []
        for i, batch_job in enumerate(batch_jobs_to_check):
            try:
                batch_response = self.client.batches.retrieve(batch_job["batch_id"])
                statuses.append(
                    {
                        "batch_num": i + 1,
                        "batch_id": batch_job["batch_id"],
                        "file_id": batch_job["file_id"],
                        "status": batch_response.status,
                        "created_at": batch_response.created_at,
                        "completed_at": batch_response.completed_at,
                        "request_counts": batch_response.request_counts.__dict__
                        if batch_response.request_counts
                        else None,
                    }
                )
            except Exception as e:
                statuses.append(
                    {
                        "batch_num": i + 1,
                        "batch_id": batch_job["batch_id"],
                        "file_id": batch_job["file_id"],
                        "status": "error",
                        "error": str(e),
                    }
                )

        return {"batch_jobs": statuses, "total_batches": len(statuses)}

    def _handle_one_annotation(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
        without_context: bool = False,
    ) -> None:
        context_items, question, answers, correct_letter = self.build_default_context(
            annotation, id, question_type, whole_page, whole_doc
        )
        context_messages = []
        for item in context_items:
            if item["kind"] == "image":
                context_messages.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{item['base64']}",
                    }
                )
            else:
                context_messages.append({"type": "input_text", "text": item["text"]})

        model_input = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": context_messages,
            },
        ]

        custom_id = f"{id}_{idx}_{question_type.replace('_', '-')}_{correct_letter}_{whole_page}_{whole_doc}_{without_context}"

        # Build batch request
        body = {
            "model": self.model,
            "input": model_input,
        }
        body["reasoning"] = {"effort": self.reasoning.value}

        self.batch_requests.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            }
        )

    def _handle_one_annotation_without_context(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
        without_context: bool = False,
    ) -> None:
        context_items, question, answers, correct_letter = self.build_without_context(
            annotation, question_type
        )
        context_messages = []
        for item in context_items:
            if item["kind"] == "image":
                context_messages.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{item['base64']}",
                    }
                )
            else:
                context_messages.append({"type": "input_text", "text": item["text"]})

        model_input = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": context_messages,
            },
        ]

        custom_id = f"{id}_{idx}_{question_type.replace('_', '-')}_{correct_letter}_{whole_page}_{whole_doc}_{without_context}"

        # Build batch request
        body = {
            "model": self.model,
            "input": model_input,
        }
        body["reasoning"] = {"effort": self.reasoning.value}

        self.batch_requests.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            }
        )

    def _handle_one_part_pair_annotation(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "part_pair",
        whole_page: bool = False,
        whole_doc: bool = False,
        without_context: bool = False,
    ) -> None:
        if whole_page:
            print(
                "Whole page setting will be ignored in _handle_one_part_pair_annotation"
            )
        if whole_doc:
            print(
                "Whole doc setting will be ignored in _handle_one_part_pair_annotation"
            )
        context_items, correct_letter = self.build_part_pair_context(annotation, id)
        if not context_items:
            return
        context_messages = []
        for item in context_items:
            if item["kind"] == "image":
                context_messages.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{item['base64']}",
                    }
                )
            else:
                context_messages.append({"type": "input_text", "text": item["text"]})

        model_input = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": context_messages,
            },
        ]

        custom_id = f"{id}_{idx}_{question_type.replace('_', '-')}_{correct_letter}_{whole_page}_{whole_doc}_{without_context}"

        # Build batch request
        body = {
            "model": self.model,
            "input": model_input,
        }
        body["reasoning"] = {"effort": self.reasoning.value}

        self.batch_requests.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            }
        )
