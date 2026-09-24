# Changelog

## 1.1.0 - 2026-09-24

- Route unspecified X5 ONNX/Caffe quantization requests to PTQ by default, following the official OE guidance.
- Require explicit QAT intent or PTQ evaluation evidence before entering the Plugin QAT workflow.
- Prefer verified X5 OE Docker images for Mapper workflows and record Docker/host execution mode in environment snapshots.
- Align all Skill release metadata and user documentation with source release v1.1.0.

## 1.0.0 - 2026-08-31

- Normalize all X5 Skill metadata for the first standalone OE X5 Skills release.
- Record `1.0.0` source installs and support `v1.0.0` as the release reference anchor.
