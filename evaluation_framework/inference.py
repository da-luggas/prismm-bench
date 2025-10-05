import argparse
from utils.providers.cluster import vLLMProvider
from dotenv import load_dotenv


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run MCQ inference with specified model."
    )
    parser.add_argument(
        "--model",
        default="llava-hf/llava-onevision-qwen2-72b-ov-hf",
        help="Model to use for inference",
    )
    args = parser.parse_args()

    provider = vLLMProvider(
        annotation_file="annotations.json",
        model=args.model,
    )
    provider.run_mcq_inference("default", whole_page=False, without_context=False)
    provider.run_mcq_inference("default", whole_page=False, without_context=True)
    provider.run_mcq_inference("edit", whole_page=False, without_context=True)
    provider.run_mcq_inference("edit", whole_page=False, without_context=False)
    provider.run_mcq_inference("part_pair", whole_page=False, without_context=False)
    provider.run_mcq_inference("default", whole_page=True)
    provider.run_mcq_inference("edit", whole_page=True)
    provider.run_mcq_inference("default", whole_doc=True)
    provider.run_mcq_inference("edit", whole_doc=True)


if __name__ == "__main__":
    main()
