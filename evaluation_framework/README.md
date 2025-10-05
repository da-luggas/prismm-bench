# Evaluation Framework

This is an evaluation framework for running MCQ (Multiple Choice Question) inference on annotated documents using various language models.

## Setup

1. Create and activate the conda environment:

   ```bash
   conda env create -f environment.yml
   conda activate mcq
   ```

2. Ensure you have access to the required models. The framework uses vLLM for local model inference.

## Running the Benchmark with One Model

To run the evaluation benchmark with a single model:

```bash
python inference.py --model <model_name>
```

The script will run MCQ inference across different configurations:

- Default questions with/without context
- Edit-based questions
- Part-pair questions
- Whole page and whole document evaluations

Results will be saved in the responses list within the provider.

## Requirements

- GPU with CUDA support (for vLLM inference)
- Sufficient VRAM for the chosen model (e.g., 72B models require multiple GPUs)
- Annotated documents in `annotations.json`

## Supported Models

The framework supports the following multimodal models via vLLM:

- `llava-hf/llava-onevision-qwen2-7b-ov-hf`
- `llava-hf/llava-onevision-qwen2-72b-ov-hf`
- `Qwen/Qwen2.5-VL-72B-Instruct`
- `Qwen/Qwen2.5-VL-32B-Instruct`
- `Qwen/Qwen2.5-VL-7B-Instruct`
- `OpenGVLab/InternVL3-8B-Instruct`
- `OpenGVLab/InternVL3-38B-Instruct`
- `OpenGVLab/InternVL3-78B-Instruct`
- `OpenGVLab/InternVL3_5-8B`
- `OpenGVLab/InternVL3_5-38B`
- `internlm/internlm-xcomposer2d5-7b`
- `internlm/internlm-xcomposer2-4khd-7b`
- `zai-org/GLM-4.5V-FP8`
- `AIDC-AI/Ovis2-34B`
- `AIDC-AI/Ovis2-8B`
- `google/gemma-3-4b-it`
- `google/gemma-3-27b-it`
- `google/gemma-3-12b-it`

**Note:** The `openai_batch` and `gemini_batch` implementations are experimental only and require API keys in a `.env` file.
