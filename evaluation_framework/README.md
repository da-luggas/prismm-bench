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

### Example

Using the default LLaVA model:

```bash
python inference.py
```

Or specify a different model:

```bash
python inference.py --model "your-model-name"
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

The framework is designed for multimodal models like LLaVA. Other providers (OpenAI, Gemini) are available but require API keys in a `.env` file.
