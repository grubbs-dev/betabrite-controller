import unittest
from unittest.mock import patch

from betabrite_controller.graphics_protocol import (
    DEFAULT_GRAPHIC_TEXT_LABEL,
    GraphicsProtocolError,
    SimulatedBetaBriteTransport,
    delete_graphic,
    encode_animation_storage_sequence,
    encode_display_graphic,
    encode_graphic,
    encode_static_graphic_sequence,
    encode_stop_priority_text,
)
from betabrite_controller.pixel_model import AnimationFrame, PixelAnimation, PixelColor, PixelFrame
from betabrite_controller.service import transmit_graphic


class GraphicsProtocolTests(unittest.TestCase):
    def sample_frame(self):
        frame = PixelFrame(width=3, height=2)
        frame.set_pixel(0, 0, PixelColor.RED)
        frame.set_pixel(1, 0, PixelColor.GREEN)
        frame.set_pixel(2, 1, PixelColor.AMBER)
        return frame

    def test_encode_graphic_exact_bytes(self):
        self.assertEqual(
            encode_graphic(self.sample_frame(), label="A"),
            bytes.fromhex("0000000000015a303002ff494130323033ff3132300d3030330d033032393404"),
        )

    def test_encode_display_graphic_exact_bytes(self):
        self.assertEqual(
            encode_display_graphic(graphic_label="A"),
            bytes.fromhex("0000000000015a303002ff41421b26621441033031383004"),
        )
        self.assertEqual(DEFAULT_GRAPHIC_TEXT_LABEL, "B")

    def test_priority_text_stop_is_documented_recovery_packet(self):
        self.assertEqual(
            encode_stop_priority_text(),
            bytes.fromhex("0000000000015a303002413004"),
        )

    def test_graphics_display_never_uses_priority_text_file(self):
        with self.assertRaises(GraphicsProtocolError):
            encode_display_graphic(graphic_label="A", text_label="0")

    def test_static_graphic_sequence_cleans_stale_priority_without_reactivating_it(self):
        packets = encode_static_graphic_sequence(self.sample_frame(), graphic_label="A")

        self.assertEqual(packets[0], encode_stop_priority_text())
        display_packet = packets[-1]
        self.assertIn(b"AB\x1b&b\x14A", display_packet)
        self.assertNotIn(b"A0\x1b&b\x14A", b"".join(packets))

    def test_rejects_invalid_dimensions_and_labels(self):
        with self.assertRaises(GraphicsProtocolError):
            encode_graphic(self.sample_frame(), label="too-long")
        with self.assertRaises(ValueError):
            PixelFrame(width=256, height=7)

    def test_animation_storage_sequence_uses_distinct_labels(self):
        animation = PixelAnimation(
            [
                AnimationFrame(PixelFrame.from_rows(["1"]), 100),
                AnimationFrame(PixelFrame.from_rows(["2"]), 100),
            ]
        )
        packets = encode_animation_storage_sequence(animation, labels="AB")
        self.assertIn(b"IA", packets[0])
        self.assertIn(b"IB", packets[1])
        with self.assertRaises(GraphicsProtocolError):
            encode_animation_storage_sequence(animation, labels="A")

    def test_delete_is_not_faked(self):
        with self.assertRaises(GraphicsProtocolError):
            delete_graphic(label="A")

    @patch("betabrite_controller.graphics_protocol.resolve_port", return_value="COM7")
    @patch("betabrite_controller.graphics_protocol.Sign")
    def test_service_transmits_static_graphic_packets(self, sign_class, resolve_port):
        result = transmit_graphic("COM7", self.sample_frame(), label="A")
        handle = sign_class.return_value
        handle.open.assert_called_once_with("COM7", baudrate=9600, bytesize=7, parity="E", stopbits=1, timeout=1, dtr=False)
        self.assertEqual(handle._ser.write_timeout, 5)
        payloads = [call.args[0] for call in handle.send.call_args_list]
        self.assertEqual(payloads, [
            encode_stop_priority_text(),
            encode_graphic(self.sample_frame(), label="A"),
            encode_display_graphic(graphic_label="A"),
        ])
        handle.close.assert_called_once()
        self.assertTrue(result.ready)
        self.assertEqual(result.source, "graphics")

    def test_virtual_transport_captures_exact_payloads(self):
        transport = SimulatedBetaBriteTransport()
        frame = self.sample_frame()
        transport.send_static_graphic(frame, graphic_label="A")
        self.assertEqual(transport.payloads, [
            encode_stop_priority_text(),
            encode_graphic(frame, label="A"),
            encode_display_graphic(graphic_label="A"),
        ])


if __name__ == "__main__":
    unittest.main()
