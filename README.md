<div align="center">
  <h1>PRISMM-Bench: A Benchmark of Peer-Review Grounded Multimodal Inconsistencies</h1>
  <p>
    <a href="https://github.com/da-luggas"><strong>Lukas Selch</strong></a><sup>1</sup> &nbsp; · &nbsp;
    <a href="https://github.com/yufanghou"><strong>Yufang Hou</strong></a><sup>2</sup> &nbsp; · &nbsp;
    <a href="https://github.com/jmiemirza"><strong>M. Jehanzeb Mirza</strong></a><sup>3</sup> &nbsp; · &nbsp;
    <a href="https://github.com/sivandoveh"><strong>Sivan Doveh</strong></a><sup>4</sup> &nbsp; · &nbsp;
    <strong>James Glass</strong><sup>3</sup> &nbsp; · &nbsp;
    <strong>Rogerio Feris</strong><sup>5</sup> &nbsp; · &nbsp;
    <a href="https://github.com/wlin-at"><strong>Wei Lin</strong></a><sup>1</sup>
  </p>
  <p style="font-style:italic; font-size:small; margin-top:0.25rem;">
    <sup>1</sup> Johannes Kepler University Linz &nbsp;&nbsp;
    <sup>2</sup> Interdisciplinary Transformation University Austria &nbsp;&nbsp;
    <sup>3</sup> MIT CSAIL &nbsp;&nbsp;
    <sup>4</sup> Stanford University &nbsp;&nbsp;
    <sup>5</sup> MIT-IBM Watson AI Lab
  </p>
</div>
  <p align="center">
    <a href="https://arxiv.org/abs/2510.16505"><img src="https://img.shields.io/badge/arXiv-2510.16505-red?logo=arxiv" alt="arXiv"></a>
    <a href="https://huggingface.co/datasets/daluggas/PRISMM-Bench"><img src="https://img.shields.io/badge/HuggingFace-PRISMM--Bench-orange?logo=huggingface" alt="Hugging Face"></a>
    <a href="https://github.com/EvolvingLMMs-Lab/lmms-eval/tree/main/lmms_eval/tasks/prismm_bench"><img src="https://img.shields.io/badge/lmms--eval-PRISMM--Bench-blue?logo=github" alt="lmms-eval"></a>
  </p>
<div align="center"></div>
<h3>Abstract</h3>
<p align="center">
  <p>
Large Multimodal Models (LMMs) are increasingly applied to scientific research, yet it remains unclear whether they can reliably understand and reason over the multimodal complexity of papers. A central challenge lies in detecting and resolving inconsistencies across text, figures, tables, and equations, issues that are often subtle, domain-specific, and ultimately undermine clarity, reproducibility, and trust. Existing benchmarks overlook this issue, either isolating single modalities or relying on synthetic errors that fail to capture real-world complexity.

We introduce PRISMM-Bench (Peer-Review-sourced Inconsistency Set for Multimodal Models), the first benchmark grounded in real reviewer-flagged inconsistencies in scientific papers. Through a multi-stage pipeline of review mining, LLM-assisted filtering and human verification, we curate 384 inconsistencies from 353 papers. Based on this set, we design three tasks, namely inconsistency identification, remedy and pair matching, which assess a model's capacity to detect, correct, and reason over inconsistencies across different modalities.

Furthermore, to address the notorious problem of choice-only shortcuts in multiple-choice evaluation, where models exploit answer patterns without truly understanding the question, we further introduce structured JSON-based answer representations that minimize linguistic biases by reducing reliance on superficial stylistic cues. We benchmark 21 leading LMMs, including large open-weight models (GLM-4.5V 106B, InternVL3 78B) and proprietary models (Gemini 2.5 Pro, GPT-5 with high reasoning). Results reveal strikingly low performance (27.8-53.9%), underscoring the challenge of multimodal scientific reasoning and motivating progress towards trustworthy scientific assistants. We provide the source code and dataset viewer in the appendix, and will release the full source code, dataset, and annotation tool publicly upon acceptance.
  </p>
  <img src="docs/static/images/pipeline_wei.svg" alt="Teaser" width="100%" style="background-color: white; padding: 10px;">
<br>

## Using the Benchmark ✅

> 🔔 **PRISMM-Bench is available via `lmms-eval`** — evaluate your model on PRISMM-Bench using the lmms-eval evaluation toolkit.
>
> 🔗 **Task page & instructions:** [lmms-eval — PRISMM-Bench task](https://github.com/EvolvingLMMs-Lab/lmms-eval/tree/main/lmms_eval/tasks/prismm_bench)
>
> **Quick start:**
> - Clone the `lmms-eval` repository and follow the task README linked above.

## Supplementary Material 📚

> ✨ **Reproducibility resources and tools** — annotation app, data sourcing scripts, and the survey UI are provided below to help you reproduce our experiments and run the annotation/survey pipelines.
>
> 🔗 **Annotation app:** [annotation_app/README.md](annotation_app/README.md) — web-based annotation interface used in our study.
>
> 🔗 **Data sourcing:** [data_sourcing/README.md](data_sourcing/README.md) — scripts and tools for data collection and preprocessing.
>
> 🔗 **Survey app:** [survey_app/README.md](survey_app/README.md) — human evaluation survey interface.