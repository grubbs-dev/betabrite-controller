import unittest
from unittest.mock import patch

from betabrite_controller.graphics_protocol import (
    CURRENT_TEXT_FILE_SIZES,
    DEFAULT_CONFIGURED_GRAPHIC_LABEL,
    DEFAULT_GRAPHIC_TEXT_LABEL,
    GraphicsProtocolError,
    SimulatedBetaBriteTransport,
    delete_graphic,
    encode_animation_storage_sequence,
    encode_current_text_memory_config_rollback,
    encode_display_graphic,
    encode_graphic,
    encode_graphics_return_to_text,
    encode_known_good_text,
    encode_minimal_graphics_memory_config,
    encode_read_memory_config,
    encode_read_small_dots,
    encode_static_graphic_sequence,
    encode_stop_priority_text,
    has_compatible_graphics_slot,
    parse_memory_config_response,
    parse_memory_config_payload,
)
from betabrite_controller.pixel_model import AnimationFrame, PixelAnimation, PixelColor, PixelFrame
from betabrite_controller.service import initialize_graphics_support, return_to_text, transmit_graphic


def _packet_checksum(packet):
    etx_index = packet.index(b"\x03")
    return packet[etx_index + 1 : etx_index + 5].decode("ascii")


VALID_MEMORY_RESPONSE = bytes.fromhex(
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "01 30 30 30 02 "
    "45 24 41 41 55 30 31 30 30 46 46 30 30 42 41 55 30 30 41 42 46 46 30 30 "
    "43 41 55 30 30 41 42 46 46 30 30 44 44 55 30 37 30 37 32 30 30 30 "
    "03 30 41 41 45 04"
)

VALID_DOTS_D_RESPONSE = bytes.fromhex(
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "01 30 30 30 02 "
    "49 44 30 37 30 37 32 30 30 30 30 30 32 0d 30 32 30 30 30 32 30 0d "
    "30 30 32 30 32 30 30 0d 30 30 30 32 30 30 30 0d 30 30 32 30 32 30 30 0d "
    "30 32 30 30 30 32 30 0d 32 30 30 30 30 30 32 0d 03 30 42 30 35 04"
)


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

    def test_minimal_graphics_memory_config_exact_bytes(self):
        self.assertEqual(
            encode_minimal_graphics_memory_config(),
            bytes.fromhex(
                "0000000000015a303002ff45244141553031303046463030"
                "42415530304142464630304341553030414246463030"
                "4444553037303732303030033041414504"
            ),
        )
        self.assertEqual(DEFAULT_CONFIGURED_GRAPHIC_LABEL, "D")

    def test_minimal_graphics_memory_config_preserves_text_entries_and_adds_dots(self):
        packet = encode_minimal_graphics_memory_config()

        self.assertIn(b"E$AAU0100FF00", packet)
        self.assertIn(b"BAU00ABFF00", packet)
        self.assertIn(b"CAU00ABFF00", packet)
        self.assertIn(b"DDU07072000", packet)
        self.assertNotIn(b"A0", packet)

    def test_minimal_graphics_memory_config_checksum(self):
        self.assertEqual(_packet_checksum(encode_minimal_graphics_memory_config()), "0AAE")

    def test_current_text_memory_config_rollback_exact_bytes(self):
        self.assertEqual(
            encode_current_text_memory_config_rollback(),
            bytes.fromhex(
                "0000000000015a303002ff45244141553732363246463030"
                "42415530304142464630304341553030414246463030033038353104"
            ),
        )
        self.assertEqual(CURRENT_TEXT_FILE_SIZES, {"A": 0x7262, "B": 0x00AB, "C": 0x00AB})
        self.assertEqual(_packet_checksum(encode_current_text_memory_config_rollback()), "0851")

    def test_graphics_memory_config_rejects_text_label_collision(self):
        with self.assertRaises(GraphicsProtocolError):
            encode_minimal_graphics_memory_config(graphic_label="A")
        with self.assertRaises(GraphicsProtocolError):
            encode_minimal_graphics_memory_config(graphic_label=DEFAULT_GRAPHIC_TEXT_LABEL)
        with self.assertRaises(GraphicsProtocolError):
            encode_minimal_graphics_memory_config(graphic_label="C")

    def test_memory_config_parser_handles_current_and_expected_layouts(self):
        current = parse_memory_config_payload("E$AAU7262FF00BAU00ABFF00CAU00ABFF00")
        self.assertEqual([entry.raw for entry in current], [
            "AAU7262FF00",
            "BAU00ABFF00",
            "CAU00ABFF00",
        ])

        expected = parse_memory_config_payload("E$AAU0100FF00BAU00ABFF00CAU00ABFF00DDU07072000")
        self.assertEqual([entry.raw for entry in expected], [
            "AAU0100FF00",
            "BAU00ABFF00",
            "CAU00ABFF00",
            "DDU07072000",
        ])
        self.assertEqual(expected[-1].file_type, "D")
        self.assertEqual(expected[-1].size, "0707")
        self.assertEqual(expected[-1].suffix, "2000")

    def test_memory_config_response_parser_and_slot_detection(self):
        entries = parse_memory_config_response(VALID_MEMORY_RESPONSE)

        self.assertEqual([entry.raw for entry in entries], [
            "AAU0100FF00",
            "BAU00ABFF00",
            "CAU00ABFF00",
            "DDU07072000",
        ])
        self.assertTrue(has_compatible_graphics_slot(entries))
        self.assertFalse(has_compatible_graphics_slot(entries, graphic_label="E"))

    def test_read_memory_config_query_is_read_only_fixture(self):
        self.assertEqual(
            encode_read_memory_config().to_bytes(),
            bytes.fromhex("0000000000015a303002ff462404"),
        )

    def test_return_to_text_overwrites_wrapper_without_touching_dots(self):
        packet = encode_graphics_return_to_text()
        self.assertEqual(
            packet,
            bytes.fromhex("0000000000015a303002ff41421b26621c32475245454e204f4b033033413404"),
        )
        self.assertNotIn(b"\x14D", packet)
        self.assertNotIn(b"ID", packet)
        self.assertNotIn(b"E$", packet)

    def test_static_graphic_sequence_cleans_stale_priority_without_reactivating_it(self):
        packets = encode_static_graphic_sequence(self.sample_frame())

        self.assertEqual(len(packets), 2)
        self.assertIn(b"ID", packets[0])
        display_packet = packets[-1]
        self.assertIn(b"AB\x1b&b\x14D", display_packet)
        self.assertNotIn(b"A0", b"".join(packets))

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
        handle = sign_class.return_value
        handle.read_response.return_value = VALID_MEMORY_RESPONSE

        result = transmit_graphic("COM7", self.sample_frame())

        handle = sign_class.return_value
        handle.open.assert_called_once_with("COM7", baudrate=9600, bytesize=7, parity="E", stopbits=1, timeout=1, dtr=False)
        self.assertEqual(handle._ser.write_timeout, 5)
        payloads = [call.args[0] for call in handle.send.call_args_list]
        self.assertEqual(payloads[0].to_bytes(), encode_read_memory_config().to_bytes())
        self.assertEqual(payloads[1:], [
            encode_graphic(self.sample_frame(), label=DEFAULT_CONFIGURED_GRAPHIC_LABEL),
            encode_display_graphic(graphic_label=DEFAULT_CONFIGURED_GRAPHIC_LABEL),
        ])
        handle.close.assert_called_once()
        self.assertTrue(result.ready)
        self.assertEqual(result.source, "graphics")

    @patch("betabrite_controller.graphics_protocol.resolve_port", return_value="COM7")
    @patch("betabrite_controller.graphics_protocol.Sign")
    def test_controller_can_verify_dots_readback_before_wrapper(self, sign_class, resolve_port):
        handle = sign_class.return_value
        handle.read_response.side_effect = [VALID_MEMORY_RESPONSE, VALID_DOTS_D_RESPONSE]
        from betabrite_controller.graphics_protocol import BetaBriteGraphicsController

        BetaBriteGraphicsController(port="COM7").send_static_graphic(
            self.sample_frame(),
            verify_readback=True,
        )

        payloads = [call.args[0] for call in handle.send.call_args_list]
        self.assertEqual(payloads[0].to_bytes(), encode_read_memory_config().to_bytes())
        self.assertEqual(payloads[1], encode_graphic(self.sample_frame(), label=DEFAULT_CONFIGURED_GRAPHIC_LABEL))
        self.assertEqual(payloads[2].to_bytes(), encode_read_small_dots().to_bytes())
        self.assertEqual(payloads[3], encode_display_graphic(graphic_label=DEFAULT_CONFIGURED_GRAPHIC_LABEL))

    @patch("betabrite_controller.graphics_protocol.resolve_port", return_value="COM7")
    @patch("betabrite_controller.graphics_protocol.Sign")
    def test_service_blocks_graphics_without_dots_allocation(self, sign_class, resolve_port):
        sign_class.return_value.read_response.return_value = bytes.fromhex(
            "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
            "01 30 30 30 02 45 24 41 41 55 37 32 36 32 46 46 30 30 42 41 55 30 30 41 42 "
            "46 46 30 30 43 41 55 30 30 41 42 46 46 30 30 03 30 38 35 31 04"
        )

        result = transmit_graphic("COM7", self.sample_frame())

        payloads = [call.args[0] for call in sign_class.return_value.send.call_args_list]
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0].to_bytes(), encode_read_memory_config().to_bytes())
        self.assertFalse(result.ready)
        self.assertEqual(result.state, "graphics-not-initialized")
        self.assertIn("Initialize Graphics Support", result.message)

    @patch("betabrite_controller.graphics_protocol.resolve_port", return_value="COM7")
    @patch("betabrite_controller.graphics_protocol.Sign")
    def test_initialize_graphics_support_reads_configures_verifies_and_restores_text(self, sign_class, resolve_port):
        handle = sign_class.return_value
        handle.read_response.side_effect = [
            bytes.fromhex(
                "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
                "01 30 30 30 02 45 24 41 41 55 37 32 36 32 46 46 30 30 42 41 55 30 30 41 42 "
                "46 46 30 30 43 41 55 30 30 41 42 46 46 30 30 03 30 38 35 31 04"
            ),
            VALID_MEMORY_RESPONSE,
        ]

        result = initialize_graphics_support("COM7")

        payloads = [call.args[0] for call in handle.send.call_args_list]
        self.assertEqual(payloads[0].to_bytes(), encode_read_memory_config().to_bytes())
        self.assertEqual(payloads[1], encode_minimal_graphics_memory_config())
        self.assertEqual(payloads[2].to_bytes(), encode_read_memory_config().to_bytes())
        self.assertEqual(payloads[3], encode_known_good_text(text_label="A"))
        self.assertEqual(payloads[4], encode_known_good_text(text_label="B"))
        self.assertEqual(payloads[5], encode_known_good_text(text_label="C"))
        self.assertTrue(result.ready)
        self.assertEqual(result.source, "graphics-init")
        self.assertIn("DOTS D is ready", result.message)

    @patch("betabrite_controller.graphics_protocol.resolve_port", return_value="COM7")
    @patch("betabrite_controller.graphics_protocol.Sign")
    def test_return_to_text_only_overwrites_wrapper_text(self, sign_class, resolve_port):
        result = return_to_text("COM7")

        payloads = [call.args[0] for call in sign_class.return_value.send.call_args_list]
        self.assertEqual(payloads, [encode_graphics_return_to_text()])
        self.assertTrue(result.ready)
        self.assertEqual(result.source, "graphics-return")

    def test_virtual_transport_captures_exact_payloads(self):
        transport = SimulatedBetaBriteTransport()
        frame = self.sample_frame()
        transport.send_static_graphic(frame, graphic_label="A")
        self.assertEqual(transport.payloads, [
            encode_graphic(frame, label="A"),
            encode_display_graphic(graphic_label="A"),
        ])


if __name__ == "__main__":
    unittest.main()
