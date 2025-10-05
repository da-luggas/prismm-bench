import json
import tempfile
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from tqdm import tqdm

from utils.prompts import system_prompt
from utils.providers.base import BaseMCQProvider
from utils.types import AnnotationEntry, ReasoningLevel

load_dotenv()


class GeminiBatchProvider(BaseMCQProvider):
    def __init__(
        self,
        api_key: str,
        annotation_file: str,
        model: str = "gemini-2.0-flash",
        reasoning: ReasoningLevel = ReasoningLevel.HIGH,
        file_name: str = None,
        batch_name: str = None,
        max_batch_size_mb: float = 1900.0,  # Conservative limit below 2GB
    ):
        super().__init__(annotation_file=annotation_file, model=model)
        self.annotation_file = annotation_file
        self.model = model
        self.api_key = api_key
        self.reasoning = reasoning
        self.file_name = file_name
        self.batch_name = batch_name
        self.batch_requests = []
        self.max_batch_size_mb = max_batch_size_mb

        # Support for multiple batch jobs
        self.batch_jobs = []  # List of {"file_name": str, "batch_name": str}

        self.client = genai.Client(api_key=api_key)

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
            mode="w+", suffix=".jsonl", delete=False
        ) as tmpfile:
            batch_file = tmpfile.name
            for req in batch_requests:
                tmpfile.write(json.dumps(req) + "\n")

        batch_display_name = f"batch_{batch_num}" if batch_num is not None else "batch"
        print(
            f"Uploading '{batch_display_name}' ({len(batch_requests)} requests) to Gemini..."
        )

        # Upload the file to the File API
        uploaded_file = self.client.files.upload(
            file=batch_file,
            config=types.UploadFileConfig(
                display_name=f"{batch_display_name}_requests",
                mime_type="application/jsonl",
            ),
        )
        print(f"File uploaded with name: {uploaded_file.name}")

        print(f"Creating {batch_display_name} job...")
        batch = self.client.batches.create(
            model=self.model,
            src=uploaded_file.name,
            config={
                "display_name": f"{batch_display_name}_job",
            },
        )
        print(f"Batch created with name: {batch.name}. Status: {batch.state.name}")

        return {"file_name": uploaded_file.name, "batch_name": batch.name}

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
            self.batch_name = self.batch_jobs[0]["batch_name"]
            self.file_name = self.batch_jobs[0]["file_name"]

        return {
            "batch_jobs": self.batch_jobs,
            "file_name": self.file_name,  # Primary batch for backwards compatibility
            "batch_name": self.batch_name,  # Primary batch for backwards compatibility
        }

    def get_batch_results(self):
        self.responses = []

        # Use batch_jobs if available, otherwise fall back to single batch for backwards compatibility
        if self.batch_jobs:
            batch_jobs_to_process = self.batch_jobs
        elif self.file_name and self.batch_name:
            batch_jobs_to_process = [
                {"file_name": self.file_name, "batch_name": self.batch_name}
            ]
        else:
            raise ValueError(
                "No batch jobs found. file_name and batch_name must be set to retrieve results."
            )

        print(f"Processing results from {len(batch_jobs_to_process)} batch job(s)...")

        all_results = []
        for i, batch_job in enumerate(batch_jobs_to_process):
            print(
                f"Processing batch job {i + 1}/{len(batch_jobs_to_process)} (Name: {batch_job['batch_name']})..."
            )

            # Check if ready
            batch_response = self.client.batches.get(name=batch_job["batch_name"])
            if batch_response.state.name != "JOB_STATE_SUCCEEDED":
                raise ValueError(
                    f"Batch job {batch_job['batch_name']} not ready yet. Status: {batch_response.state.name}"
                )

            # Get results from this batch
            if batch_response.dest and batch_response.dest.file_name:
                result_file_name = batch_response.dest.file_name
                file_content = self.client.files.download(file=result_file_name)
                file_content_str = file_content.decode("utf-8")
                batch_results = [
                    json.loads(line) for line in file_content_str.splitlines()
                ]
            else:
                raise ValueError(
                    f"No output file found for batch {batch_job['batch_name']}"
                )

            all_results.extend(batch_results)
            print(f"Retrieved {len(batch_results)} results from batch {i + 1}")

        print(f"Total results retrieved: {len(all_results)}")

        # Process all results
        question_type = None
        if all_results:
            # Extract question_type from the first result's key
            first_key = all_results[0]["key"]
            parts = first_key.split("_")
            if len(parts) >= 3:
                question_type = parts[2].replace("-", "_")

        for result in all_results:
            parts = result["key"].split("_")
            if len(parts) == 6:
                (
                    id,
                    idx,
                    question_type_part,
                    correct_letter,
                    whole_page,
                    without_context,
                ) = parts
                whole_doc = "False"  # Default for backwards compatibility
            else:
                (
                    id,
                    idx,
                    question_type_part,
                    correct_letter,
                    whole_page,
                    whole_doc,
                    without_context,
                ) = parts

            question_type = question_type_part.replace("-", "_")

            # Extract prediction from response
            prediction = None
            if "response" in result and result["response"]:
                response_obj = result["response"]
                if "candidates" in response_obj and response_obj["candidates"]:
                    candidate = response_obj["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts_list = candidate["content"]["parts"]
                        if parts_list and "text" in parts_list[0]:
                            prediction = parts_list[0]["text"].strip("'.\" )").upper()

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
        elif self.file_name and self.batch_name:
            batch_jobs_to_check = [
                {"file_name": self.file_name, "batch_name": self.batch_name}
            ]
        else:
            return {"error": "No batch jobs found"}

        statuses = []
        for i, batch_job in enumerate(batch_jobs_to_check):
            try:
                batch_response = self.client.batches.get(name=batch_job["batch_name"])
                statuses.append(
                    {
                        "batch_num": i + 1,
                        "batch_name": batch_job["batch_name"],
                        "file_name": batch_job["file_name"],
                        "status": batch_response.state.name,
                        "create_time": batch_response.create_time.isoformat()
                        if batch_response.create_time
                        else None,
                        "update_time": batch_response.update_time.isoformat()
                        if batch_response.update_time
                        else None,
                        "total_request_count": batch_response.total_request_count
                        if hasattr(batch_response, "total_request_count")
                        else None,
                    }
                )
            except Exception as e:
                statuses.append(
                    {
                        "batch_num": i + 1,
                        "batch_name": batch_job["batch_name"],
                        "file_name": batch_job["file_name"],
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

        # Build Gemini content format
        contents = []

        # Add system instruction first, then user content
        parts = []
        for item in context_items:
            if item["kind"] == "image":
                parts.append(
                    {"inline_data": {"mime_type": "image/jpeg", "data": item["base64"]}}
                )
            else:
                parts.append({"text": item["text"]})

        contents.append({"parts": parts, "role": "user"})

        custom_id = f"{id}_{idx}_{question_type.replace('_', '-')}_{correct_letter}_{whole_page}_{whole_doc}_{without_context}"

        # Build batch request in Gemini JSONL format
        request = {
            "key": custom_id,
            "request": {
                "contents": contents,
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "generation_config": {
                    "temperature": 0.0,
                },
            },
        }

        self.batch_requests.append(request)

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

        # Build Gemini content format
        contents = []

        parts = []
        for item in context_items:
            if item["kind"] == "image":
                parts.append(
                    {"inline_data": {"mime_type": "image/jpeg", "data": item["base64"]}}
                )
            else:
                parts.append({"text": item["text"]})

        contents.append({"parts": parts, "role": "user"})

        custom_id = f"{id}_{idx}_{question_type.replace('_', '-')}_{correct_letter}_{whole_page}_{whole_doc}_{without_context}"

        # Build batch request in Gemini JSONL format
        request = {
            "key": custom_id,
            "request": {
                "contents": contents,
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "generation_config": {
                    "temperature": 0.0,
                },
            },
        }

        self.batch_requests.append(request)

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

        # Build Gemini content format
        contents = []

        parts = []
        for item in context_items:
            if item["kind"] == "image":
                parts.append(
                    {"inline_data": {"mime_type": "image/jpeg", "data": item["base64"]}}
                )
            else:
                parts.append({"text": item["text"]})

        contents.append({"parts": parts, "role": "user"})

        custom_id = f"{id}_{idx}_{question_type.replace('_', '-')}_{correct_letter}_{whole_page}_{whole_doc}_{without_context}"

        # Build batch request in Gemini JSONL format
        request = {
            "key": custom_id,
            "request": {
                "contents": contents,
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "generation_config": {
                    "temperature": 0.0,
                },
            },
        }

        self.batch_requests.append(request)

    def wait_for_completion(
        self, timeout_hours: int = 48, poll_interval_seconds: int = 30
    ):
        """Wait for all batch jobs to complete."""
        if not self.batch_jobs:
            raise ValueError("No batch jobs to wait for")

        completed_states = {
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
        }

        start_time = time.time()
        timeout_seconds = timeout_hours * 3600

        print(f"Waiting for {len(self.batch_jobs)} batch job(s) to complete...")

        while True:
            all_completed = True
            status_info = self.get_batch_status()

            for batch_status in status_info["batch_jobs"]:
                if batch_status["status"] not in completed_states:
                    all_completed = False
                    break

            if all_completed:
                print("All batch jobs completed!")
                # Print final status
                for batch_status in status_info["batch_jobs"]:
                    print(
                        f"Batch {batch_status['batch_num']}: {batch_status['status']}"
                    )
                break

            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                print(f"Timeout reached after {timeout_hours} hours")
                break

            # Print current status
            print(f"Status check ({elapsed_time / 60:.1f} min elapsed):")
            for batch_status in status_info["batch_jobs"]:
                print(f"  Batch {batch_status['batch_num']}: {batch_status['status']}")

            print(f"Waiting {poll_interval_seconds} seconds before next check...")
            time.sleep(poll_interval_seconds)

    def cancel_batch_jobs(self):
        """Cancel all batch jobs."""
        if not self.batch_jobs:
            print("No batch jobs to cancel")
            return

        for i, batch_job in enumerate(self.batch_jobs):
            try:
                self.client.batches.cancel(name=batch_job["batch_name"])
                print(f"Cancelled batch job {i + 1}: {batch_job['batch_name']}")
            except Exception as e:
                print(f"Failed to cancel batch job {i + 1}: {e}")

    def delete_batch_jobs(self):
        """Delete all batch jobs."""
        if not self.batch_jobs:
            print("No batch jobs to delete")
            return

        for i, batch_job in enumerate(self.batch_jobs):
            try:
                self.client.batches.delete(name=batch_job["batch_name"])
                print(f"Deleted batch job {i + 1}: {batch_job['batch_name']}")
            except Exception as e:
                print(f"Failed to delete batch job {i + 1}: {e}")
