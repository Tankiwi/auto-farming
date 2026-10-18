"""Offline tests: never open a serial port or signal a real process."""
import contextlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arm


class FakePort:
    def __init__(self):
        self.frames = []

    def write(self, frame):
        self.frames.append(frame)
        return len(frame)

    def flush(self):
        pass


class MotorTests(unittest.TestCase):
    def simulate(self, motor_id, amplitude, positions):
        port = FakePort()
        cleaned = []

        @contextlib.contextmanager
        def session():
            try:
                yield port
            finally:
                cleaned.append(True)

        with patch.object(arm, '_serial_session', session), \
             patch.object(arm, '_query', return_value=bytes([3, 5])), \
             patch.object(arm, '_read_position', side_effect=positions), \
             patch.object(arm.time, 'sleep'):
            try:
                result = arm.test_motor(motor_id, amplitude, 2000)
            except Exception as error:
                return error, port.frames, cleaned
        return result, port.frames, cleaned

    def test_mapping_endpoints_and_direction(self):
        for sid in range(1, 5):
            self.assertEqual(arm._angle(sid, 3100), 0)
            self.assertEqual(arm._angle(sid, 900), 180)
        self.assertEqual(arm._angle(5, 380), 0)
        self.assertEqual(arm._angle(5, 3700), 270)
        self.assertEqual(arm._angle(6, 900), 0)
        self.assertEqual(arm._angle(6, 3100), 180)

    def test_signed_delta_frames_for_all_six_servos(self):
        for sid in range(1, 7):
            for amplitude in (-5, 5):
                with self.subTest(sid=sid, amplitude=amplitude):
                    target = 2000 + round(amplitude * arm._mapping(sid)[2])
                    result, frames, cleaned = self.simulate(sid, amplitude, [2000] * 3 + [target, 2000])
                    self.assertEqual(result['status'], 'passed')
                    self.assertEqual(len(frames), 2)
                    self.assertEqual(frames[0][:5], bytes([255, 252, 8, 32, sid]))
                    self.assertEqual(struct.unpack('<hh', frames[0][5:9]), (target, 2000))
                    self.assertEqual(struct.unpack('<h', frames[1][5:7])[0], 2000)
                    self.assertEqual(frames[0][-1], (sum(frames[0][:-1]) + 5) & 255)
                    self.assertEqual(cleaned, [True])

    def test_no_motion_cannot_pass_even_within_fifteen_units(self):
        result, frames, cleaned = self.simulate(6, 1, [2000] * 4)
        self.assertEqual(result['status'], 'no_movement')
        self.assertFalse(result['return_command_sent'])
        self.assertEqual(len(frames), 1)
        self.assertEqual(cleaned, [True])

    def test_partial_outbound_does_not_trigger_return_or_retry(self):
        result, frames, _ = self.simulate(6, 10, [2000] * 3 + [2080])
        self.assertEqual(result['status'], 'target_not_reached')
        self.assertEqual(len(frames), 1)

    def test_return_error_is_reported_not_compensated(self):
        result, frames, _ = self.simulate(6, 5, [2000] * 3 + [2061, 2021])
        self.assertEqual(result['status'], 'return_out_of_tolerance')
        self.assertEqual(result['return_error_units'], 21)
        self.assertEqual(len(frames), 2)

    def test_read_timeout_after_move_does_not_repeat_motion(self):
        error, frames, cleaned = self.simulate(2, 5, [2000] * 3 + [RuntimeError('timeout')])
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(len(frames), 1)
        self.assertEqual(cleaned, [True])

    def test_unstable_or_outside_position_never_writes_motion(self):
        for positions in ([2000, 2010, 2000], [806, 806, 806]):
            result, frames, cleaned = self.simulate(2, 5, positions)
            self.assertIsInstance(result, (ValueError, RuntimeError))
            self.assertEqual(frames, [])
            self.assertEqual(cleaned, [True])

    def test_bad_arguments_never_acquire_hardware(self):
        invalid = [(0, 5, 2000), (7, 5, 2000), (True, 5, 2000),
                   (1, 0, 2000), (1, 11, 2000), (1, float('nan'), 2000),
                   (1, float('inf'), 2000), (1, True, 2000), (1, 5, 0),
                   (1, 5, 2001), (1, 5, True), (1, .001, 2000)]
        with patch.object(arm, '_serial_session') as hardware:
            for args in invalid:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    arm.test_motor(*args)
            hardware.assert_not_called()

    def test_target_outside_test_boundary_never_writes_motion(self):
        result, frames, _ = self.simulate(6, -10, [970] * 3)
        self.assertIsInstance(result, ValueError)
        self.assertEqual(frames, [])

    def test_wrong_servo_reply_is_rejected(self):
        with patch.object(arm, '_query', return_value=struct.pack('<Bh', 1, 2000)):
            with self.assertRaises(RuntimeError):
                arm._read_position(None, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
