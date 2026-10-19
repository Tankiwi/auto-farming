"""Regression checks against the archived vendor parser; no device access."""
import contextlib
import importlib.util
from pathlib import Path
import queue
import sys
import threading
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('motion_demo', ROOT / 'modules/chassis/motion-demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class FakeSerial:
    instances = []
    apply_configuration = True

    def __init__(self, *args, **kwargs):
        self.timeout = None
        self.incoming = queue.Queue()
        self.writes = []
        self.active_reads = 0
        self.closed = False
        self.car_type = 1
        self.instances.append(self)

    def isOpen(self):
        return not self.closed

    def write(self, packet):
        packet = bytes(packet)
        self.writes.append(packet)
        if packet[3] == 21 and self.apply_configuration:
            self.car_type = packet[4]
        if packet[3] == 80:
            function = packet[4]
            payload = {81: [3, 5], 21: [self.car_type]}[function]
            body = [len(payload) + 3, function] + payload
            for value in [255, 251] + body + [sum(body) & 255]:
                self.incoming.put(value)
        return len(packet)

    def read(self, size=1):
        self.active_reads += 1
        try:
            try:
                return bytes([self.incoming.get(timeout=.005)])
            except queue.Empty:
                return b''
        finally:
            self.active_reads -= 1

    def close(self):
        if self.active_reads:
            raise AssertionError('Closed serial during active receiver read')
        self.closed = True


class DemoRegression(unittest.TestCase):
    def test_type_one_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'car_type=1'):
            demo.validate_board(3.5, 1)
        demo.validate_board(3.5, 2)

    def run_mode(self, mode, expected_error=None):
        namespace = {'__name__': 'vendor_snapshot'}
        with mock.patch.dict(sys.modules, {'serial': types.SimpleNamespace(Serial=FakeSerial)}):
            exec(compile((ROOT / 'docs/reports/2026-10-19-rosmaster-lib-source.txt').read_bytes(),
                         'vendor_snapshot', 'exec'), namespace)
        fake_library = types.SimpleNamespace(Rosmaster=namespace['Rosmaster'])
        with mock.patch.dict(sys.modules, {'Rosmaster_Lib': fake_library}), \
             mock.patch.object(demo.sys, 'platform', 'linux'), \
             mock.patch.object(demo.sys, 'argv', ['demo', mode, '--clear-confirmed']), \
             mock.patch.object(demo, 'signal', types.SimpleNamespace(SIGTERM=15, SIGHUP=1, signal=mock.Mock())), \
             mock.patch.object(demo, 'serial_available', contextlib.nullcontext), \
             mock.patch.object(demo, 'execute') as execute:
            if expected_error:
                with self.assertRaisesRegex(RuntimeError, expected_error):
                    demo.main()
            else:
                self.assertEqual(demo.main(), 0)
        execute.assert_not_called()
        port = FakeSerial.instances[-1]
        self.assertTrue(port.closed)
        self.assertFalse(any(t.name == 'motion-demo-receive' for t in threading.enumerate()))
        self.assertFalse(any(p[3] == 18 for p in port.writes))
        zeros = [p for p in port.writes if p[3] == 16]
        self.assertEqual(len(zeros), 3)
        self.assertTrue(all(p[4:8] == bytes(4) for p in zeros))
        return port

    def test_mismatch_cleanup_with_actual_vendor_parser(self):
        port = self.run_mode('--run', 'car_type=1')
        self.assertFalse(any(p[3] == 21 for p in port.writes))

    def test_explicit_configuration_reads_back_without_motion(self):
        port = self.run_mode('--configure-x3plus')
        configs = [p for p in port.writes if p[3] == 21]
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0][4:6], bytes([2, 95]))

    def test_failed_configuration_does_not_retry_or_move(self):
        with mock.patch.object(FakeSerial, 'apply_configuration', False):
            port = self.run_mode('--configure-x3plus', 'readback failed')
        self.assertEqual(len([p for p in port.writes if p[3] == 21]), 1)


if __name__ == '__main__':
    unittest.main()
