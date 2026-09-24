"""Contracts for X5 quantization routing and container-first OE setup."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "x5" / "platforms" / "x5" / "scripts" / "probe_environment.py"
SPEC = importlib.util.spec_from_file_location("x5_probe_environment", PROBE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class X5RoutingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = json.loads((ROOT / "x5/platforms/x5/skill-index.json").read_text())
        cls.evals = yaml.safe_load((ROOT / "x5/platforms/x5/evals/cases.yaml").read_text())
        cls.policy = cls.index["routing_policy"]
        cls.cases = {case["id"]: case for case in cls.evals["routing_cases"]}

    def test_official_x5_policy_defaults_unspecified_quantization_to_ptq(self) -> None:
        quantization = self.policy["quantization"]
        self.assertEqual(quantization["default_method"], "PTQ")
        self.assertIn("oe_x5_doc/cn/oe_mapper/source/faststart/ptq_qat_overview.html", quantization["official_reference"])
        self.assertEqual(quantization["ptq_skill"], "x5-ptq-deploy")
        self.assertEqual(quantization["qat_skill"], "x5-qat-deploy")
        self.assertEqual(self.cases["unspecified-onnx-quantization"]["expected_skill"], "x5-ptq-deploy")

    def test_qat_requires_explicit_intent_or_ptq_gap_evidence(self) -> None:
        quantization = self.policy["quantization"]
        self.assertEqual(
            set(quantization["qat_entry_conditions"]),
            {"explicit_user_request", "ptq_requirement_not_met_after_evaluation"},
        )
        self.assertEqual(self.cases["explicit-qat"]["expected_skill"], "x5-qat-deploy")
        self.assertEqual(self.cases["ptq-accuracy-gap"]["expected_skill"], "x5-accuracy-diagnostics")
        self.assertEqual(self.cases["pytorch-source-alone"]["expected_action"], "ask_export_or_qat_intent")

    def test_environment_policy_prefers_docker_and_records_host_fallback(self) -> None:
        policy = self.policy["environment"]
        self.assertEqual(policy["preferred_execution"], "docker")
        self.assertEqual(policy["container_probe"], "read_only_tool_help")
        self.assertIn("explicitly_configured_host_toolchain", policy["fallbacks"])
        self.assertEqual(policy["host_opt_in"], "--execution-mode host")
        self.assertEqual(policy["host_opt_in_environment_variable"], "OE_DROBOTICS_EXECUTION_MODE=host")
        self.assertEqual(policy["qat_gpu_probe"]["docker_flag"], "--gpus all")
        self.assertEqual(policy["qat_gpu_probe"]["check"], "torch.cuda.is_available")
        self.assertEqual(policy["qat_gpu_probe"]["claim_scope"], "device_visibility_only")

    def test_host_toolchain_is_used_only_when_host_mode_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            docs = Path(temporary)
            (docs / "index.html").write_text("manual")
            (docs / "_sources").mkdir()
            args = Namespace(
                workflow="ptq",
                docs_root=str(docs),
                board_chip=None,
                board_version=None,
                board_architecture=None,
                board_reachable=False,
                require_board=False,
                docker_image=None,
                execution_mode=None,
            )
            available = {"available": True, "path": "/usr/local/bin/hb_mapper", "version": "1.2.8"}
            with (
                patch.dict("os.environ", {"OE_DROBOTICS_DOCKER_IMAGE": "", "OE_DROBOTICS_EXECUTION_MODE": ""}),
                patch.object(PROBE, "command_info", return_value=available),
                patch.object(PROBE, "package_info", return_value={"available": True, "version": "2.0"}),
                patch.object(PROBE, "probe_docker_toolchain", return_value={
                    "image": None,
                    "image_available": False,
                    "verified": False,
                    "tools": [],
                    "error": "no Docker image configured",
                }),
            ):
                default_snapshot = PROBE.build_snapshot(args)
                args.execution_mode = "host"
                host_snapshot = PROBE.build_snapshot(args)
                PROBE.validate_snapshot(default_snapshot)
                PROBE.validate_snapshot(host_snapshot)

        self.assertIsNone(default_snapshot["execution"]["selected_mode"])
        self.assertIn("configured X5 PTQ Docker image", " ".join(default_snapshot["missing"]))
        self.assertEqual(host_snapshot["execution"]["selected_mode"], "host")
        self.assertNotIn("hb_mapper", host_snapshot["missing"])

    def test_ptq_probe_uses_verified_docker_tools_when_host_cli_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            docs = Path(temporary)
            (docs / "index.html").write_text("manual")
            (docs / "_sources").mkdir()
            args = Namespace(
                workflow="ptq",
                docs_root=str(docs),
                board_chip=None,
                board_version=None,
                board_architecture=None,
                board_reachable=False,
                require_board=False,
                docker_image="openexplorer/x5-cpu:test",
            )
            unavailable = {"available": False, "path": None, "version": None}
            with (
                patch.object(PROBE, "command_info", return_value=unavailable),
                patch.object(PROBE, "package_info", return_value={"available": False, "version": None}),
                patch.object(PROBE, "probe_docker_toolchain", return_value={
                    "image": args.docker_image,
                    "image_available": True,
                    "verified": True,
                    "tools": ["hb_mapper", "hb_model_info"],
                    "error": None,
                }),
            ):
                snapshot = PROBE.build_snapshot(args)
                PROBE.validate_snapshot(snapshot)

        self.assertNotEqual(snapshot["status"], "blocked")
        self.assertEqual(snapshot["execution"]["selected_mode"], "docker")
        self.assertEqual(snapshot["execution"]["docker_image"]["verified"], True)
        self.assertNotIn("hb_mapper", snapshot["missing"])
        self.assertNotIn("hb_model_info", snapshot["missing"])

    def test_environment_schema_still_accepts_legacy_snapshot_without_execution(self) -> None:
        legacy_snapshot = {
            "schema_version": "1.0",
            "platform": "X5",
            "status": "ready",
            "captured_at": "2026-09-24T00:00:00Z",
            "workflow": "environment",
            "host": {"os": "Linux", "architecture": "x86_64", "python": "3.10"},
            "toolchain": {},
            "documentation": {"root": None, "available": False, "hat_in_scope": False},
            "missing": [],
        }
        PROBE.validate_snapshot(legacy_snapshot)

    def test_qat_docker_probe_passes_gpu_and_requires_cuda_visibility(self) -> None:
        results = [
            Namespace(returncode=0, stdout="sha256:gpu\n", stderr=""),
            Namespace(returncode=0, stdout="CUDA_VISIBLE=True\n", stderr=""),
        ]
        with (
            patch.object(PROBE.shutil, "which", return_value="/usr/bin/docker"),
            patch.object(PROBE.subprocess, "run", side_effect=results) as run,
        ):
            result = PROBE.probe_docker_toolchain(
                "registry.d-robotics.cc/deliver/ai_toolchain_ubuntu_20_x5_gpu:v1.2.8",
                "qat",
            )

        command = run.call_args_list[1].args[0]
        self.assertIn("--gpus", command)
        self.assertEqual(command[command.index("--gpus") + 1], "all")
        self.assertIn("torch.cuda.is_available()", command[-1])
        self.assertTrue(result["verified"])
        self.assertIn("cuda", result["tools"])

    def test_host_qat_requires_cuda_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            docs = Path(temporary)
            (docs / "index.html").write_text("manual")
            (docs / "_sources").mkdir()
            args = Namespace(
                workflow="qat",
                docs_root=str(docs),
                board_chip=None,
                board_version=None,
                board_architecture=None,
                board_reachable=False,
                require_board=False,
                docker_image=None,
                execution_mode="host",
            )
            available = {"available": True, "path": "/usr/bin/tool", "version": "1.0"}
            with (
                patch.object(PROBE, "command_info", return_value=available),
                patch.object(PROBE, "package_info", return_value={"available": True, "version": "2.0"}),
                patch.object(PROBE, "torch_cuda_info", return_value={"available": False, "path": None, "version": None}),
            ):
                snapshot = PROBE.build_snapshot(args)
                PROBE.validate_snapshot(snapshot)

        self.assertIsNone(snapshot["execution"]["selected_mode"])
        self.assertIn("host torch, CUDA, and horizon_plugin_pytorch", " ".join(snapshot["missing"]))

    def test_docker_probe_runs_networkless_help_without_host_mounts(self) -> None:
        results = [
            Namespace(returncode=0, stdout="sha256:abc\n", stderr=""),
            Namespace(returncode=0, stdout="/usr/bin/hb_mapper\nchecker makertbin\n/usr/bin/hb_model_info\n", stderr=""),
        ]
        with (
            patch.object(PROBE.shutil, "which", return_value="/usr/bin/docker"),
            patch.object(PROBE.subprocess, "run", side_effect=results) as run,
        ):
            result = PROBE.probe_docker_toolchain("openexplorer/x5-cpu:test", "ptq")

        self.assertTrue(result["verified"])
        self.assertEqual(result["tools"], ["hb_mapper", "hb_model_info"])
        command = run.call_args_list[1].args[0]
        self.assertIn("--entrypoint", command)
        self.assertEqual(command[command.index("--entrypoint") + 1], "/bin/bash")
        self.assertIn("--rm", command)
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("--read-only", command)
        self.assertIn("--tmpfs", command)
        self.assertIn("/tmp:rw,exec,nosuid,size=64m", command)
        self.assertNotIn("-v", command)
        self.assertNotIn("--mount", command)


if __name__ == "__main__":
    unittest.main()
