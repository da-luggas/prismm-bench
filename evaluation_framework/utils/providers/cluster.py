from dataclasses import asdict
from typing import Any, NamedTuple, Optional

from PIL.Image import Image
from tqdm import tqdm
from transformers import AutoProcessor, AutoTokenizer
from vllm import LLM, EngineArgs, SamplingParams
from vllm.multimodal.utils import fetch_image

from utils.prompts import system_prompt
from utils.providers.base import BaseMCQProvider
from utils.types import AnnotationEntry


class ModelRequestData(NamedTuple):
    engine_args: EngineArgs
    prompt: str
    image_data: list[Image]
    stop_token_ids: Optional[list[int]] = None
    chat_template: Optional[str] = None
    lora_requests: Optional[list[Any]] = None


class vLLMProvider(BaseMCQProvider):
    def __init__(self, model: str, annotation_file: str, reasoning: bool = False):
        super().__init__(annotation_file=annotation_file, model=model)
        self.llm = None
        self.reasoning = False

    def load_llava_ov(self, context_messages, image_urls) -> ModelRequestData:
        engine_args = EngineArgs(
            model=self.model,
            max_model_len=32768,
            tensor_parallel_size=4 if "72b" in self.model.lower() else 1,
            max_num_batched_tokens=32768,
            max_num_seqs=5,
            limit_mm_per_prompt={"image": 5},
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_messages},
        ]

        processor = AutoProcessor.from_pretrained(self.model)

        prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            image_data=[fetch_image(url) for url in image_urls],
        )

    def load_qwen_2_5_vl(self, context_messages, image_urls) -> ModelRequestData:
        try:
            from qwen_vl_utils import smart_resize
        except ModuleNotFoundError:
            print(
                "WARNING: `qwen-vl-utils` not installed, input images will not "
                "be automatically resized. You can enable this functionality by "
                "`pip install qwen-vl-utils`."
            )
            smart_resize = None

        engine_args = EngineArgs(
            model=self.model,
            tensor_parallel_size=4 if "7b" not in self.model.lower() else 1,
            max_model_len=32768,  # if smart_resize is None else 4096,
            max_num_batched_tokens=32768,  # if smart_resize is None else 4096,
            max_num_seqs=5,
            limit_mm_per_prompt={"image": 5},
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_messages},
        ]

        processor = AutoProcessor.from_pretrained(self.model)

        prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        if smart_resize is None:
            image_data = [fetch_image(url) for url in image_urls]
        else:

            def post_process_image(image: Image) -> Image:
                width, height = image.size
                resized_height, resized_width = smart_resize(
                    height, width, max_pixels=1024 * 28 * 28
                )
                return image.resize((resized_width, resized_height))

            image_data = [post_process_image(fetch_image(url)) for url in image_urls]

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            image_data=image_data,
        )

    def load_qwen_vl(self, context_messages, image_urls) -> ModelRequestData:
        engine_args = EngineArgs(
            model=self.model,
            trust_remote_code=True,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            max_num_seqs=5,
            hf_overrides={"architectures": ["QwenVLForConditionalGeneration"]},
            limit_mm_per_prompt={"image": 5},
        )

        prompt_string = ""

        for i in context_messages:
            if i["type"] == "text":
                prompt_string += i["text"] + "\n"
            elif i["type"] == "image":
                prompt_string += (
                    f"Image-{image_urls.index(i['image']) + 1}: <img></img>\n\n"
                )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_string},
        ]

        tokenizer = AutoTokenizer.from_pretrained(self.model, trust_remote_code=True)
        chat_template = "{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"  # noqa: E501

        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            chat_template=chat_template,
        )

        stop_tokens = ["<|endoftext|>", "<|im_start|>", "<|im_end|>"]
        stop_token_ids = [tokenizer.convert_tokens_to_ids(i) for i in stop_tokens]

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            stop_token_ids=stop_token_ids,
            image_data=[fetch_image(url) for url in image_urls],
            chat_template=chat_template,
        )

    def load_internlm(self, context_messages, image_urls) -> ModelRequestData:
        engine_args = EngineArgs(
            model=self.model,
            trust_remote_code=True,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            max_num_seqs=5,
            tensor_parallel_size=1,
            limit_mm_per_prompt={"image": 5},
        )

        prompt_string = ""

        for i in context_messages:
            if i["type"] == "text":
                prompt_string += i["text"] + "\n"
            elif i["type"] == "image":
                prompt_string += (
                    f"Image-{image_urls.index(i['image']) + 1}: <ImageHere>\n"
                )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_string},
        ]

        tokenizer = AutoTokenizer.from_pretrained(self.model, trust_remote_code=True)
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            image_data=[fetch_image(url) for url in image_urls],
        )

    def load_internvl(self, context_messages, image_urls) -> ModelRequestData:
        engine_args = EngineArgs(
            model=self.model,
            tensor_parallel_size=4 if "-8b" not in self.model.lower() else 1,
            trust_remote_code=True,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            max_num_seqs=5,
            limit_mm_per_prompt={"image": 5},
            mm_processor_kwargs={"max_dynamic_patch": 4},
        )

        prompt_string = ""

        for i in context_messages:
            if i["type"] == "text":
                prompt_string += i["text"] + "\n"
            elif i["type"] == "image":
                prompt_string += f"Image-{image_urls.index(i['image']) + 1}: <image>\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_string},
        ]

        tokenizer = AutoTokenizer.from_pretrained(self.model, use_remote_code=True)
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        stop_tokens = ["<|endoftext|>", "<|im_start|>", "<|im_end|>", "<|end|>"]
        stop_token_ids = [tokenizer.convert_tokens_to_ids(i) for i in stop_tokens]

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            stop_token_ids=stop_token_ids,
            image_data=[fetch_image(url) for url in image_urls],
        )

    def load_internvl3_5(self, context_messages, image_urls) -> ModelRequestData:
        self.reasoning = True
        engine_args = EngineArgs(
            model=self.model,
            tensor_parallel_size=4 if "-8b" not in self.model.lower() else 1,
            trust_remote_code=True,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            max_num_seqs=5,
            limit_mm_per_prompt={"image": 5},
            mm_processor_kwargs={"max_dynamic_patch": 4},
        )

        R1_SYSTEM_PROMPT = """
        You are an AI assistant that rigorously follows this response protocol:

        1. First, conduct a detailed analysis of the question. Consider different angles, potential solutions, and reason through the problem step-by-step. Enclose this entire thinking process within <think> and </think> tags.

        2. After the thinking section, provide a clear, concise, and direct answer to the user's question. Separate the answer from the think section with a newline.

        Ensure that the thinking process is thorough but remains focused on the query. The final answer should be standalone and not reference the thinking section.

        The final answer should only include the letter of the correct answer (A, B, C, or D), and nothing else.
        """.strip()

        messages = [
            {"role": "system", "content": R1_SYSTEM_PROMPT},
            {"role": "user", "content": context_messages},
        ]

        processor = AutoProcessor.from_pretrained(self.model, use_remote_code=True)
        prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=True
        )

        stop_token_ids = [151643, 151644, 151645]

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            stop_token_ids=stop_token_ids,
            image_data=[fetch_image(url) for url in image_urls],
        )

    def load_glm(self, context_messages, image_urls) -> ModelRequestData:
        self.reasoning = True
        engine_args = EngineArgs(
            model=self.model,
            tensor_parallel_size=4,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            max_num_seqs=5,
            limit_mm_per_prompt={"image": 5},
            enforce_eager=True,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_messages},
        ]

        processor = AutoProcessor.from_pretrained(self.model)
        prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=True
        )

        image_data = [fetch_image(url) for url in image_urls]

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            image_data=image_data,
        )

    def load_ovis(self, context_messages, image_urls) -> ModelRequestData:
        engine_args = EngineArgs(
            model=self.model,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            tensor_parallel_size=4 if "-34b" in self.model.lower() else 1,
            max_num_seqs=5,
            trust_remote_code=True,
            dtype="half",
            limit_mm_per_prompt={"image": 5},
        )

        prompt_string = ""
        for i in context_messages:
            if i["type"] == "text":
                prompt_string += i["text"] + "\n"
            elif i["type"] == "image":
                prompt_string += f"Image-{image_urls.index(i['image']) + 1}: <image>\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_string},
        ]

        tokenizer = AutoTokenizer.from_pretrained(self.model, trust_remote_code=True)
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            image_data=[fetch_image(url) for url in image_urls],
        )

    def load_gemma(self, context_messages, image_urls) -> ModelRequestData:
        engine_args = EngineArgs(
            model=self.model,
            max_model_len=32768,
            max_num_batched_tokens=32768,
            tensor_parallel_size=4 if "27b" in self.model.lower() else 1,
            max_num_seqs=5,
            limit_mm_per_prompt={"image": 5},
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_messages},
        ]

        processor = AutoProcessor.from_pretrained(self.model, trust_remote_code=True)
        prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        return ModelRequestData(
            engine_args=engine_args,
            prompt=prompt,
            image_data=[fetch_image(url) for url in image_urls],
        )

    model_map = {
        "llava-hf/llava-onevision-qwen2-7b-ov-hf": load_llava_ov,
        "llava-hf/llava-onevision-qwen2-72b-ov-hf": load_llava_ov,
        "Qwen/Qwen2.5-VL-72B-Instruct": load_qwen_2_5_vl,
        "Qwen/Qwen2.5-VL-32B-Instruct": load_qwen_2_5_vl,
        "Qwen/Qwen2.5-VL-7B-Instruct": load_qwen_2_5_vl,
        "OpenGVLab/InternVL3-8B-Instruct": load_internvl,
        "OpenGVLab/InternVL3-38B-Instruct": load_internvl,
        "OpenGVLab/InternVL3-78B-Instruct": load_internvl,
        "OpenGVLab/InternVL3_5-8B": load_internvl3_5,
        "OpenGVLab/InternVL3_5-38B": load_internvl3_5,
        "internlm/internlm-xcomposer2d5-7b": load_internvl,
        "internlm/internlm-xcomposer2-4khd-7b": load_internvl,
        "zai-org/GLM-4.5V-FP8": load_glm,
        "AIDC-AI/Ovis2-34B": load_ovis,
        "AIDC-AI/Ovis2-8B": load_ovis,
        "google/gemma-3-4b-it": load_gemma,
        "google/gemma-3-27b-it": load_gemma,
        "google/gemma-3-12b-it": load_gemma,
    }

    def run_mcq_inference(
        self,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
        without_context: bool = False,
    ):
        self.responses = []
        for key, idx, ann in tqdm(
            self.iter_annotations(question_type, whole_page, whole_doc)
        ):
            if without_context:
                if question_type == "part_pair":
                    raise ValueError(
                        "without_context=True is not supported for question_type='part_pair'"
                    )
                self._handle_one_annotation_without_context(
                    id=key,
                    idx=idx,
                    annotation=ann,
                    question_type=question_type,
                    whole_page=whole_page,
                    whole_doc=whole_doc,
                )
            elif question_type == "part_pair":
                self._handle_one_part_pair_annotation(
                    id=key,
                    idx=idx,
                    annotation=ann,
                    question_type=question_type,
                    whole_page=whole_page,
                    whole_doc=whole_doc,
                )
            else:
                self._handle_one_annotation(
                    id=key,
                    idx=idx,
                    annotation=ann,
                    question_type=question_type,
                    whole_page=whole_page,
                    whole_doc=whole_doc,
                )
        self.write_results(
            self.model, question_type, whole_page, whole_doc, without_context
        )

    def _run_inference(
        self,
        id: str,
        idx: int,
        context_items,
        correct_letter: str,
        include_images: bool = True,
    ) -> None:
        context_messages = []
        image_urls = []
        for item in context_items:
            if item["kind"] == "image":
                image_url = f"data:image/jpeg;base64,{item['base64']}"
                context_messages.append({"type": "image", "image": image_url})
                image_urls.append(image_url)
            else:
                context_messages.append({"type": "text", "text": item["text"]})
        req_data = self.model_map[self.model](
            self, context_messages=context_messages, image_urls=image_urls
        )
        default_limits = {"image": 0, "video": 0, "audio": 0}
        req_data.engine_args.limit_mm_per_prompt = default_limits | dict(
            req_data.engine_args.limit_mm_per_prompt or {}
        )
        engine_args = asdict(req_data.engine_args)
        if not self.llm:
            self.llm = LLM(**engine_args)
        max_tokens = 16384 if self.reasoning else 10
        sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=max_tokens,
            stop_token_ids=req_data.stop_token_ids,
        )
        # Build batch request
        generate_dict = {
            "prompt": req_data.prompt,
        }
        if include_images:
            generate_dict["multi_modal_data"] = {"image": req_data.image_data}
        response = self.llm.generate(
            generate_dict,
            sampling_params=sampling_params,
            lora_request=req_data.lora_requests,
        )
        full_text = response[0].outputs[0].text
        prediction = full_text.strip("'.\" )").upper()
        response_dict = {
            "id": id,
            "idx": idx,
            "prediction": prediction,
            "correct_letter": correct_letter,
            "is_correct": prediction == correct_letter,
        }
        if self.reasoning:
            if "</think>" in full_text:
                thinking_part, final_part = full_text.split("</think>", 1)
                response_dict["reasoning"] = thinking_part.replace(
                    "<think>", ""
                ).strip()
                response_dict["prediction"] = final_part.strip("'.\" )").upper()
                response_dict["is_correct"] = (
                    response_dict["prediction"] == correct_letter
                )
            if "</think>" in full_text:
                thinking_part, final_part = full_text.split("</think>", 1)
                response_dict["reasoning"] = thinking_part.replace(
                    "<think>", ""
                ).strip()
                response_dict["prediction"] = final_part.strip("'.\" )").upper()
                response_dict["is_correct"] = (
                    response_dict["prediction"] == correct_letter
                )
        self.responses.append(response_dict)

    def _handle_one_annotation(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
    ) -> None:
        context_items, question, answers, correct_letter = self.build_default_context(
            annotation, id, question_type, whole_page, whole_doc
        )
        self._run_inference(id, idx, context_items, correct_letter, include_images=True)

    def _handle_one_annotation_without_context(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "default",
        whole_page: bool = False,
        whole_doc: bool = False,
    ) -> None:
        if whole_page:
            print(
                "WARNING: Whole page setting will be ignored in _handle_one_annotation_without_context"
            )
        if whole_doc:
            print(
                "WARNING: Whole doc setting will be ignored in _handle_one_annotation_without_context"
            )
        context_items, question, answers, correct_letter = self.build_without_context(
            annotation, question_type
        )
        self._run_inference(
            id, idx, context_items, correct_letter, include_images=False
        )

    def _handle_one_part_pair_annotation(
        self,
        id: str,
        idx: int,
        annotation: AnnotationEntry,
        question_type: str = "part_pair",
        whole_page: bool = False,
        whole_doc: bool = False,
    ) -> None:
        if whole_page:
            print(
                "WARNING: Whole page setting will be ignored in _handle_one_part_pair_annotation"
            )
        if whole_doc:
            print(
                "WARNING: Whole doc setting will be ignored in _handle_one_part_pair_annotation"
            )
        context_items, correct_letter = self.build_part_pair_context(annotation, id)
        if not context_items:
            return
        self._run_inference(id, idx, context_items, correct_letter, include_images=True)
