"""Offline tests; no ROS, device access, or real process signals."""
import importlib.util
from pathlib import Path
import signal
import subprocess
import unittest
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[1] / 'start-sensors.py'
SPEC = importlib.util.spec_from_file_location('sensor_launcher', SCRIPT)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_alias_and_selection(self):
        args = launcher.parse_args(['camera', 'astra', 'microdia'])
        self.assertEqual(args.sensors, ['astra', 'microdia'])
        self.assertEqual(launcher.parse_args(['all']).sensors, ['astra', 'microdia', 'lidar', 'imu'])

    def test_imu_uses_passive_reader_not_chassis_launch(self):
        command = launcher.driver_command('imu', '')
        self.assertEqual(Path(command[2]).name, 'read-imu.py')
        self.assertNotIn('ros2', command)
        self.assertNotIn('Rosmaster', ' '.join(command))

    def test_preview_does_not_inspect_or_launch(self):
        with patch.object(launcher.subprocess, 'Popen') as start, \
                patch.object(launcher, 'load_environment') as env, \
                patch.object(launcher, 'validate_microdia') as validate:
            self.assertEqual(launcher.main(['all', '--dry-run']), 0)
            start.assert_not_called()
            env.assert_not_called()
            validate.assert_not_called()

    def test_microdia_command_namespace_and_format(self):
        command = launcher.driver_command('microdia', '/dev/video0')
        self.assertIn('__ns:=/microdia', command)
        self.assertIn('pixel_format:=yuyv', command)
        self.assertIn('video_device:=/dev/video0', command)
        self.assertNotIn('mjpeg2rgb', command)

    def test_device_path_is_one_argument(self):
        path = '/tmp/device with spaces; ignored'
        self.assertIn(f'video_device:={path}', launcher.driver_command('microdia', path))

    def test_other_sensor_commands_unchanged(self):
        self.assertEqual(launcher.driver_command('astra', ''),
                         ['ros2', 'launch', 'astra_camera', 'astro_pro_plus.launch.xml'])
        self.assertEqual(launcher.driver_command('lidar', ''),
                         ['ros2', 'launch', 'ydlidar_ros2_driver', 'ydlidar_raw_launch.py'])

    def test_wrong_usb_device_rejected(self):
        device = Mock()
        device.is_char_device.return_value = True
        with patch.object(launcher.Path, 'resolve', return_value=device), \
                patch.object(launcher.subprocess, 'run', return_value=Mock(stdout='ID_VENDOR_ID=2bc5\nID_MODEL_ID=050f')):
            with self.assertRaisesRegex(RuntimeError, '不是已核对'):
                launcher.validate_microdia('/dev/video0')

    def test_resolves_symlink_before_passing_to_driver(self):
        device = Mock()
        device.__str__ = Mock(return_value='/dev/video0')
        device.is_char_device.return_value = True
        outputs = [Mock(stdout='ID_VENDOR_ID=0c45\nID_MODEL_ID=6340'),
                   Mock(stdout='Video Capture'), Mock(stdout="'YUYV' 640x480")]
        with patch.object(launcher.Path, 'resolve', return_value=device), \
                patch.object(launcher.subprocess, 'run', side_effect=outputs):
            self.assertEqual(launcher.validate_microdia('/dev/v4l/by-id/example'), '/dev/video0')

    def test_metadata_node_rejected(self):
        device = Mock()
        device.is_char_device.return_value = True
        with patch.object(launcher.Path, 'resolve', return_value=device), \
                patch.object(launcher.subprocess, 'run', side_effect=[
                    Mock(stdout='ID_VENDOR_ID=0c45\nID_MODEL_ID=6340'),
                    subprocess.CalledProcessError(1, 'v4l2-ctl')]):
            with self.assertRaises(subprocess.CalledProcessError):
                launcher.validate_microdia('/dev/video1')

    def test_missing_environment_rejected(self):
        with patch.object(launcher, 'SETUPS', ('/nonexistent-farm-setup',)):
            with self.assertRaisesRegex(RuntimeError, '环境文件不存在'):
                launcher.load_environment(77)

    def test_stop_only_owned_groups_and_escalate_on_timeout(self):
        proc = Mock(pid=10001)
        proc.wait.side_effect = [subprocess.TimeoutExpired('driver', 10), None, None]
        with patch.object(signal, 'SIGKILL', 9, create=True), \
                patch.object(launcher.os, 'killpg', create=True) as kill:
            launcher.stop_drivers([('microdia', proc)])
            self.assertEqual([call.args[0] for call in kill.call_args_list], [10001] * 3)
            self.assertEqual([call.args[1] for call in kill.call_args_list],
                             [signal.SIGINT, signal.SIGTERM, 9])


if __name__ == '__main__':
    unittest.main()
