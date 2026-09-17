import unittest
from types import SimpleNamespace

from betabrite_controller.presentation import connection_view


class PresentationTests(unittest.TestCase):

    def test_ready_is_online_and_sendable(self):
        view = connection_view(
            SimpleNamespace(
                state="ready",
                message="Port opened.",
                port="COM4",
            )
        )
        self.assertEqual(view.headline, "● READY")
        self.assertEqual(view.tone, "online")
        self.assertTrue(view.can_send)
        self.assertEqual(view.port, "COM4")

    def test_selected_requires_active_probe_before_send(self):
        view = connection_view(
            SimpleNamespace(
                state="selected",
                message="Adapter selected.",
                port="/dev/ttyUSB0",
            )
        )
        self.assertEqual(view.headline, "● ADAPTER DETECTED")
        self.assertEqual(view.tone, "selected")
        self.assertFalse(view.can_send)

    def test_error_states_are_not_sendable(self):
        for state in (
            "no-adapter",
            "not-found",
            "selection-required",
            "permission-denied",
            "port-busy",
            "port-not-found",
            "open-failed",
        ):
            with self.subTest(state=state):
                view = connection_view(
                    SimpleNamespace(
                        state=state,
                        message="Problem.",
                        port=None,
                    )
                )
                self.assertFalse(view.can_send)

    def test_unknown_state_has_safe_fallback(self):
        view = connection_view(
            SimpleNamespace(
                state="unexpected",
                message="Unknown.",
                port=None,
            )
        )
        self.assertEqual(view.headline, "● CHECK CONNECTION")
        self.assertEqual(view.tone, "offline")
        self.assertFalse(view.can_send)


if __name__ == "__main__":
    unittest.main()
