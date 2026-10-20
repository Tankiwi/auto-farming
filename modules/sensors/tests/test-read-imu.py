"""Protocol tests based on archived Rosmaster 3.3.1; no hardware/ROS imports."""
import importlib.util
from pathlib import Path
import struct
import unittest

SPEC = importlib.util.spec_from_file_location(
    'imu_reader', Path(__file__).resolve().parents[1] / 'read-imu.py')
imu = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(imu)


def packet(function, payload):
    body = bytes([len(payload) + 3, function]) + payload
    return b'\xff\xfb' + body + bytes([sum(body) & 255])


class ImuTests(unittest.TestCase):
    def test_fragmented_frame_with_noise(self):
        decoder = imu.FrameDecoder()
        wire = packet(0x0E, struct.pack('<9h', *range(9)))
        self.assertEqual(decoder.feed(b'noise' + wire[:1]), [])
        self.assertEqual(decoder.feed(wire[1:12]), [])
        self.assertEqual(decoder.feed(wire[12:]), [(0x0E, struct.pack('<9h', *range(9)))])

    def test_corrupt_checksum_recovers(self):
        decoder = imu.FrameDecoder()
        good = packet(0x0C, struct.pack('<3h', 100, 200, 300))
        bad = good[:-1] + bytes([good[-1] ^ 1])
        self.assertEqual(decoder.feed(bad + good), [(0x0C, struct.pack('<3h', 100, 200, 300))])
        self.assertGreaterEqual(decoder.bad_checksums, 1)

    def test_multiple_frames(self):
        decoder = imu.FrameDecoder()
        self.assertEqual(decoder.feed(packet(0x51, b'\x03\x05') * 2),
                         [(0x51, b'\x03\x05')] * 2)

    def test_bad_length_resynchronizes(self):
        decoder = imu.FrameDecoder()
        self.assertEqual(decoder.feed(b'\xff\xfb\x00\x01' + packet(0x51, b'\x03\x05')),
                         [(0x51, b'\x03\x05')])

    def test_mpu_conversion_and_signs(self):
        raw = (1000, -2000, 3000, 1000, 2000, -3000, -32768, 0, 32767)
        values, gyro, accel = imu.decode_raw(0x0B, struct.pack('<9h', *raw))
        self.assertEqual(values, raw)
        self.assertAlmostEqual(gyro[1], 2000 / 3754.9)
        self.assertAlmostEqual(gyro[2], -3000 / 3754.9)
        self.assertAlmostEqual(accel[2], -3000 / 1671.84)

    def test_icm_conversion(self):
        raw = (1000, -2000, 3000, -4000, 5000, 6000, 7, 8, 9)
        values, gyro, accel = imu.decode_raw(0x0E, struct.pack('<9h', *raw))
        self.assertEqual(gyro, (1, -2, 3))
        self.assertEqual(accel, (-4, 5, 6))
        self.assertEqual(values[6:], (7, 8, 9))

    def test_attitude_order_and_scale(self):
        self.assertEqual(imu.decode_attitude(0x0C, struct.pack('<3h', 10000, -20000, 30000)),
                         (1, -2, 3))

    def test_reject_wrong_type_and_payload_length(self):
        self.assertIsNone(imu.decode_raw(0x0C, bytes(18)))
        self.assertIsNone(imu.decode_raw(0x0B, bytes(17)))
        self.assertIsNone(imu.decode_attitude(0x0E, bytes(6)))
        self.assertIsNone(imu.decode_attitude(0x0C, bytes(7)))


if __name__ == '__main__':
    unittest.main()
