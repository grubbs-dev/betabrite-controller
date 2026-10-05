import tempfile
import unittest
from pathlib import Path

from betabrite_controller.pixel_model import (
    AnimationFrame,
    PixelAnimation,
    PixelColor,
    PixelDocument,
    PixelDocumentError,
    PixelFrame,
)


class PixelFrameTests(unittest.TestCase):
    def test_create_set_unset_and_color(self):
        frame = PixelFrame(width=5, height=7)
        frame.set_pixel(2, 3, PixelColor.GREEN)
        self.assertEqual(frame.get_pixel(2, 3), PixelColor.GREEN)
        frame.unset_pixel(2, 3)
        self.assertEqual(frame.get_pixel(2, 3), PixelColor.OFF)

    def test_clear_invert_and_flips(self):
        frame = PixelFrame.from_rows(["100", "020"])
        frame.invert(PixelColor.AMBER)
        self.assertEqual(frame.to_rows(), ["033", "303"])
        frame.flip_horizontal()
        self.assertEqual(frame.to_rows(), ["330", "303"])
        frame.flip_vertical()
        self.assertEqual(frame.to_rows(), ["303", "330"])
        frame.clear()
        self.assertEqual(frame.to_rows(), ["000", "000"])

    def test_duplicate_is_independent(self):
        frame = PixelFrame.from_rows(["100"])
        clone = frame.duplicate()
        clone.set_pixel(1, 0, PixelColor.RED)
        self.assertEqual(frame.to_rows(), ["100"])
        self.assertEqual(clone.to_rows(), ["110"])

    def test_invalid_dimensions_and_colors(self):
        with self.assertRaises(PixelDocumentError):
            PixelFrame(width=256, height=7)
        with self.assertRaises(PixelDocumentError):
            PixelFrame.from_rows(["19"])


class PixelAnimationTests(unittest.TestCase):
    def test_frame_ordering_and_loop(self):
        animation = PixelAnimation([AnimationFrame(PixelFrame.from_rows(["1"]), 100)])
        animation.add_frame(PixelFrame.from_rows(["2"]), duration_ms=150)
        animation.move_frame(1, 0)
        self.assertEqual([item.frame.to_rows()[0] for item in animation.frames], ["2", "1"])
        self.assertEqual(animation.next_index(1), 0)
        animation.loop = False
        self.assertEqual(animation.next_index(1), 1)

    def test_duplicate_delete_and_duration_validation(self):
        animation = PixelAnimation([AnimationFrame(PixelFrame.from_rows(["1"]), 100)])
        duplicate_index = animation.duplicate_frame(0)
        self.assertEqual(duplicate_index, 1)
        animation.delete_frame(0)
        self.assertEqual(animation.frame_count(), 1)
        with self.assertRaises(PixelDocumentError):
            animation.delete_frame(0)
        with self.assertRaises(PixelDocumentError):
            AnimationFrame(PixelFrame.from_rows(["1"]), 10)


class PixelDocumentTests(unittest.TestCase):
    def test_save_load_roundtrip(self):
        document = PixelDocument.new(width=3, height=7, title="Demo")
        document.frames[0].frame.set_pixel(1, 1, PixelColor.YELLOW)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.bbpixel"
            document.save(path)
            loaded = PixelDocument.load(path)
        self.assertEqual(loaded.title, "Demo")
        self.assertEqual(loaded.frames[0].frame.get_pixel(1, 1), PixelColor.YELLOW)

    def test_malformed_and_unsupported_versions(self):
        with self.assertRaises(PixelDocumentError):
            PixelDocument.from_json("{")
        payload = PixelDocument.new().to_dict()
        payload["version"] = 999
        with self.assertRaises(PixelDocumentError):
            PixelDocument.from_dict(payload)
        payload = PixelDocument.new().to_dict()
        del payload["animation"]
        loaded = PixelDocument.from_dict(payload)
        self.assertEqual(loaded.width, 90)


if __name__ == "__main__":
    unittest.main()

