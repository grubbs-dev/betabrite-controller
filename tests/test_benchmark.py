import json
import tempfile
import unittest
from pathlib import Path

from betabrite_controller.benchmark import (
    BENCHMARK_PATTERNS,
    BenchmarkResult,
    pattern_frame,
    percentile,
    physical_live_benchmark_blocked_report,
    recommend_fps,
    run_virtual_benchmark_suite,
    run_virtual_pattern_benchmark,
)


class BenchmarkTests(unittest.TestCase):
    def test_percentile_calculation(self):
        self.assertEqual(percentile([], 95), 0.0)
        self.assertEqual(percentile([10], 95), 10)
        self.assertEqual(percentile([1, 2, 3, 4], 50), 2.5)

    def test_patterns_generate_valid_frames(self):
        for pattern in BENCHMARK_PATTERNS:
            frame = pattern_frame(pattern, 3, width=12, height=7)
            self.assertEqual((frame.width, frame.height), (12, 7))
            self.assertEqual(len(frame.to_rows()), 7)

    def test_virtual_pattern_benchmark_records_metrics(self):
        result = run_virtual_pattern_benchmark("moving-marker", 4, duration_seconds=0.5, width=12, height=7)
        self.assertEqual(result.pattern, "moving-marker")
        self.assertEqual(result.frames_attempted, 2)
        self.assertEqual(result.frames_sent, 2)
        self.assertGreater(result.bytes_per_frame, 0)
        self.assertEqual(result.failures, 0)

    def test_stable_rate_recommendation_has_margin(self):
        results = [
            BenchmarkResult(
                pattern="static-repeat",
                target_fps=rate,
                achieved_fps=rate,
                bytes_per_frame=1,
                protocol_overhead_bytes=0,
                average_latency_ms=1,
                p50_latency_ms=1,
                p95_latency_ms=1,
                max_latency_ms=1,
                dropped_frames=0,
                failures=0,
                duration_seconds=1,
                frames_attempted=rate,
                frames_sent=rate,
            )
            for rate in (1, 2, 4, 8)
        ]
        self.assertEqual(recommend_fps(results), 6)

    def test_report_serialization_and_blocked_physical_report(self):
        report = run_virtual_benchmark_suite(rates=[1], patterns=["static-repeat"], duration_seconds=0.1)
        data = json.loads(report.to_json())
        self.assertEqual(data["serial_device"], "virtual")
        self.assertEqual(len(data["results"]), 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report.save(path)
            self.assertTrue(path.exists())

        blocked = physical_live_benchmark_blocked_report("COM7")
        self.assertEqual(blocked.results[0].status, "blocked")
        self.assertIn("volatile", blocked.safety_note)


if __name__ == "__main__":
    unittest.main()
