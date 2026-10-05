import unittest

from betabrite_controller.live import (
    LiveFramePacket,
    LiveRenderer,
    LiveScheduler,
    SimulatedLiveRenderer,
    SimulatedLiveTransport,
    StaticFrameSource,
)
from betabrite_controller.dino import DinoRunnerSource
from betabrite_controller.pixel_model import PixelFrame


class ManualClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class LiveSchedulerTests(unittest.TestCase):
    def test_frame_source_lifecycle_and_render(self):
        frame = PixelFrame(width=3, height=1)
        source = StaticFrameSource(frame)
        source.start()
        rendered = source.next_frame(100)
        self.assertEqual(rendered.to_rows(), ["000"])
        self.assertIsNot(rendered, frame)

    def test_start_pause_resume_stop(self):
        clock = ManualClock()
        scheduler = LiveScheduler(StaticFrameSource(PixelFrame(width=2, height=1)), clock=clock, perf_clock=clock)

        scheduler.start()
        self.assertTrue(scheduler.running)
        scheduler.pause()
        clock.advance(1)
        scheduler.tick()
        self.assertTrue(scheduler.paused)
        scheduler.resume()
        self.assertFalse(scheduler.paused)
        scheduler.stop()
        self.assertFalse(scheduler.running)

    def test_pacing_and_late_frame_accounting(self):
        clock = ManualClock()
        scheduler = LiveScheduler(
            StaticFrameSource(PixelFrame(width=2, height=1)),
            preview_fps=10,
            target_fps=2,
            clock=clock,
            perf_clock=clock,
        )
        scheduler.start()
        clock.advance(0.5)
        scheduler.tick()
        clock.advance(0.5)
        scheduler.tick()
        self.assertGreaterEqual(scheduler.statistics.frames_rendered, 2)

        clock.advance(1.0)
        scheduler.tick()
        self.assertGreater(scheduler.statistics.frames_dropped, 0)

    def test_simulated_transport_transmits_and_coalesces_latest_frame(self):
        clock = ManualClock()
        transport = SimulatedLiveTransport()
        scheduler = LiveScheduler(
            StaticFrameSource(PixelFrame(width=2, height=1)),
            renderer=SimulatedLiveRenderer(clock=clock),
            transport=transport,
            preview_fps=30,
            target_fps=2,
            clock=clock,
            perf_clock=clock,
        )
        scheduler.start()
        scheduler.tick()
        clock.advance(1.2)
        scheduler.tick()

        self.assertEqual(len(transport.payloads), 2)
        self.assertGreaterEqual(scheduler.statistics.frames_coalesced, 1)
        self.assertEqual(scheduler.statistics.frames_transmitted, 2)

    def test_unproven_physical_renderer_does_not_transmit(self):
        clock = ManualClock()
        transport = SimulatedLiveTransport()
        scheduler = LiveScheduler(
            StaticFrameSource(PixelFrame(width=2, height=1)),
            renderer=LiveRenderer(clock=clock),
            transport=transport,
            clock=clock,
            perf_clock=clock,
        )
        scheduler.start()
        scheduler.tick()
        self.assertEqual(transport.payloads, [])
        self.assertIn("No proven volatile", scheduler.last_error)

    def test_error_stop_after_repeated_transport_failures(self):
        class FailingTransport:
            def send_packet(self, packet: LiveFramePacket) -> None:
                raise RuntimeError("gone")

        clock = ManualClock()
        scheduler = LiveScheduler(
            StaticFrameSource(PixelFrame(width=2, height=1)),
            renderer=SimulatedLiveRenderer(clock=clock),
            transport=FailingTransport(),
            target_fps=10,
            clock=clock,
            perf_clock=clock,
            max_failures=2,
        )
        scheduler.start()
        scheduler.tick()
        clock.advance(0.1)
        scheduler.tick()

        self.assertFalse(scheduler.running)
        self.assertEqual(scheduler.statistics.errors, 2)

    def test_dino_to_scheduler_encoder_and_simulated_transport(self):
        clock = ManualClock()
        transport = SimulatedLiveTransport()
        scheduler = LiveScheduler(
            DinoRunnerSource(seed=4),
            renderer=SimulatedLiveRenderer(clock=clock),
            transport=transport,
            preview_fps=20,
            target_fps=4,
            clock=clock,
            perf_clock=clock,
        )
        scheduler.start()
        scheduler.handle_input("jump")
        for _ in range(4):
            clock.advance(0.25)
            scheduler.tick()

        self.assertGreaterEqual(scheduler.statistics.frames_rendered, 2)
        self.assertGreaterEqual(scheduler.statistics.frames_transmitted, 4)
        self.assertEqual(scheduler.statistics.errors, 0)
        self.assertTrue(all(payload.startswith(b"\x00\x00\x00") for payload in transport.payloads))


if __name__ == "__main__":
    unittest.main()
