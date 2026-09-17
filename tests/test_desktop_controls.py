import unittest

from betabrite_controller.desktop_controls import (
    PRESETS,
    MessageDraft,
    can_transmit,
    display_name,
)


class DesktopControlsTests(unittest.TestCase):

    def test_default_draft_is_valid(self):
        draft = MessageDraft()
        self.assertIs(draft.validate(), draft)
        self.assertEqual(draft.normalized_message, "BRIEF IN PROGRESS")

    def test_blank_draft_requires_message_or_special(self):
        with self.assertRaises(ValueError):
            MessageDraft(message="   ").validate()

    def test_special_only_draft_is_valid(self):
        draft = MessageDraft(message="", special_name="fireworks")
        draft.validate()
        self.assertTrue(draft.has_payload)

    def test_invalid_backend_choice_is_rejected(self):
        with self.assertRaises(ValueError):
            MessageDraft(color_name="purple").validate()

    def test_invalid_speed_is_rejected(self):
        with self.assertRaises(ValueError):
            MessageDraft(speed_level=9).validate()

    def test_send_kwargs_are_backend_ready(self):
        draft = MessageDraft(
            message="  SYSTEM ONLINE  ",
            color_name="green",
            mode_name="hold",
            speed_level=4,
            flash=True,
            wide=True,
        )

        self.assertEqual(
            draft.send_kwargs(),
            {
                "message": "SYSTEM ONLINE",
                "color_name": "green",
                "mode_name": "hold",
                "special_name": None,
                "speed_level": 4,
                "flash": True,
                "wide": True,
            },
        )

    def test_transmit_requires_active_ready_state(self):
        draft = MessageDraft(message="READY")
        self.assertFalse(can_transmit(False, draft))
        self.assertTrue(can_transmit(True, draft))

    def test_presets_and_display_names(self):
        self.assertEqual(PRESETS["ONLINE"], "SYSTEM ONLINE")
        self.assertEqual(display_name("roll-left"), "Roll Left")


if __name__ == "__main__":
    unittest.main()
