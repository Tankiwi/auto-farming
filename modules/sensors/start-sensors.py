#!/usr/bin/env python3
"""Select and supervise the installed Jetson ROS 2 sensor drivers.

Examples: python3 start-sensors.py astra
          python3 start-sensors.py microdia
          python3 start-sensors.py lidar astra
          python3 start-sensors.py all --dry-run
IMU uses the sibling read-imu.py passive serial receiver. No motion commands or
persistent device configuration are sent.
"""
import argparse
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time


SETUPS = (
    '/opt/ros/humble/setup.bash',
    '/home/jetson/yahboomcar_ros2_ws/software/library_ws/install/setup.bash',
    '/home/jetson/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash',
)
DRIVERS = {
    'astra': ('astra_camera', 'astro_pro_plus.launch.xml', 'astra_camera_node'),
    'microdia': ('usb_cam', None, 'usb_cam_node_exe'),
    'lidar': ('ydlidar_ros2_driver', 'ydlidar_raw_launch.py', 'ydlidar_ros2_driver_node'),
    'imu': (None, None, 'read-imu.py'),
}
MICRODIA_DEVICE = ('/dev/v4l/by-id/'
                   'usb-Sonix_Technology_Co.__Ltd._USB_2.0_Camera-video-index0')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='启动指定传感器驱动；Ctrl+C 停止本次启动的驱动。')
    parser.add_argument('sensors', nargs='+', choices=(*DRIVERS, 'camera', 'all'),
                        help='astra=Astra；microdia=USB 相机；lidar=雷达；imu=九轴；all=全部；camera 是 astra 别名')
    parser.add_argument('--domain-id', type=int, default=77, help='ROS domain，默认 77')
    parser.add_argument('--dry-run', action='store_true', help='仅显示配置和命令，不启动驱动')
    parser.add_argument('--microdia-device', default=MICRODIA_DEVICE,
                        help='Microdia 图像采集设备，默认使用已核对的 by-id 路径')
    args = parser.parse_args(argv)
    if not 0 <= args.domain_id <= 232:
        parser.error('--domain-id 必须在 0～232 范围内')
    names = ['astra' if name == 'camera' else name for name in args.sensors]
    args.sensors = list(DRIVERS) if 'all' in names else list(dict.fromkeys(names))
    return args


def driver_command(name, microdia_device):
    if name == 'imu':
        return [sys.executable, '-u', str(Path(__file__).resolve().with_name('read-imu.py'))]
    if name != 'microdia':
        return ['ros2', 'launch', *DRIVERS[name][:2]]
    # Do not load usb_cam's sample MJPEG configuration: this device advertises YUYV.
    # Separate namespace keeps these topics distinct from Astra's /camera/ topics.
    return ['ros2', 'run', 'usb_cam', 'usb_cam_node_exe', '--ros-args',
            '-r', '__ns:=/microdia', '-r', '__node:=microdia_camera',
            '-p', f'video_device:={microdia_device}',
            '-p', 'pixel_format:=yuyv', '-p', 'io_method:=mmap',
            '-p', 'image_width:=640', '-p', 'image_height:=480',
            '-p', 'framerate:=30.0', '-p', 'frame_id:=microdia_optical_frame',
            '-p', 'camera_name:=microdia', '-p', 'brightness:=-1']


def validate_microdia(device):
    # usb_cam 0.8.1 handles relative symlinks poorly; pass a resolved device path.
    path = Path(device).resolve(strict=True)
    if not path.is_char_device():
        raise RuntimeError(f'不是视频字符设备：{path}')
    props = subprocess.run(['udevadm', 'info', '--query=property', f'--name={path}'],
                           capture_output=True, text=True, check=True, timeout=10).stdout
    properties = dict(line.split('=', 1) for line in props.splitlines() if '=' in line)
    if (properties.get('ID_VENDOR_ID'), properties.get('ID_MODEL_ID')) != ('0c45', '6340'):
        raise RuntimeError(f'{path} 不是已核对的 Microdia 0c45:6340；拒绝打开其他相机。')
    # Metadata-only nodes reject the video-format query. Neither query starts capture.
    subprocess.run(['v4l2-ctl', '-d', str(path), '--get-fmt-video'],
                   capture_output=True, text=True, check=True, timeout=10)
    formats = subprocess.run(['v4l2-ctl', '-d', str(path), '--list-formats-ext'],
                             capture_output=True, text=True, check=True, timeout=10).stdout
    if "'YUYV'" not in formats or '640x480' not in formats:
        raise RuntimeError(f'{path} 未声明本程序所用的 YUYV 640x480 格式。')
    return str(path)


def load_environment(domain_id):
    for path in SETUPS:
        if not Path(path).is_file():
            raise RuntimeError(f'环境文件不存在：{path}')
    # Pass paths as arguments, never interpolate user input into shell code.
    result = subprocess.run(
        ['bash', '--noprofile', '--norc', '-c',
         'for setup in "$@"; do source "$setup" >/dev/null || exit 1; done; env -0',
         'sensor-environment', *SETUPS],
        capture_output=True, check=True, timeout=20,
    )
    env = dict(os.fsdecode(item).split('=', 1) for item in result.stdout.split(b'\0')
               if b'=' in item)
    env['ROS_DOMAIN_ID'] = str(domain_id)
    return env


def check_existing(sensors):
    """Conservative check across visible processes; never stop existing drivers."""
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except (OSError, ProcessLookupError):
            continue
        names = {Path(arg).name for arg in argv if arg}
        for sensor in sensors:
            package, launch_file, executable = DRIVERS[sensor]
            if executable in names or (launch_file and package in argv and launch_file in argv):
                raise RuntimeError(f'已发现 {sensor} 驱动进程 PID={entry.name}，请先检查已有终端；不重复启动。')


def stop_drivers(processes):
    # Each launch owns a separate process group, including its driver children.
    # Signal only groups created by this program, never pkill unrelated nodes.
    for sig, timeout in ((signal.SIGINT, 10), (signal.SIGTERM, 5), (signal.SIGKILL, 2)):
        for name, proc in processes:
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + timeout
        for name, proc in processes:
            try:
                proc.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        # A launcher may exit before its children; the next signal also cleans
        # any remaining children in its process group.


def main(argv=None):
    args = parse_args(argv)
    print(f'ROS_DOMAIN_ID={args.domain_id}', flush=True)
    for name in args.sensors:
        print(f'{name}: {shlex.join(driver_command(name, args.microdia_device))}', flush=True)
    if args.dry_run:
        print('仅预览；未检查设备环境、未启动驱动。')
        return 0
    if sys.platform != 'linux':
        print('请上传到 Jetson Linux 后用 python3 运行；Windows 仅支持 --dry-run。', file=sys.stderr)
        return 2

    processes = []
    locks = []
    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True

    old_handlers = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        import fcntl
        # Protect simultaneous launches through this script for the same user.
        for name in sorted(args.sensors):
            lock_dir = Path.home() / '.cache' / 'farm-sensors'
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock = (lock_dir / f'{name}.lock').open('a')
            locks.append(lock)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(f'另一个启动程序正在管理 {name}。')
        env = load_environment(args.domain_id)
        check_existing(args.sensors)
        if 'microdia' in args.sensors:
            args.microdia_device = validate_microdia(args.microdia_device)
            print(f'Microdia 采集节点：{args.microdia_device}', flush=True)
        for name in args.sensors:
            if stopping:
                return 130
            if name == 'imu':
                reader = Path(__file__).resolve().with_name('read-imu.py')
                if not reader.is_file():
                    raise RuntimeError(f'请将 IMU 读取程序与启动器放在同一目录：{reader}')
                if not Path('/dev/myserial').is_char_device():
                    raise RuntimeError('底板串口 /dev/myserial 不存在。')
                owners = subprocess.run(['fuser', '/dev/myserial'], capture_output=True,
                                        text=True, timeout=5)
                if owners.returncode not in (0, 1) or owners.stdout.strip():
                    raise RuntimeError('底板串口已占用或无法检查；请先检查底盘/机械臂程序。')
                subprocess.run([sys.executable, '-c',
                                'import serial, rclpy; from sensor_msgs.msg import Imu; '
                                'from std_msgs.msg import Int32MultiArray, Float64MultiArray'],
                               env=env, check=True, timeout=15)
                continue
            # Resolve packages/launch files without starting hardware first.
            package, launch_file, executable = DRIVERS[name]
            prefix = subprocess.run(['ros2', 'pkg', 'prefix', package], env=env,
                                    capture_output=True, text=True, check=True, timeout=15).stdout.strip()
            if launch_file is None:
                if not (Path(prefix) / 'lib' / package / executable).is_file():
                    raise RuntimeError(f'驱动程序不存在：{package}/{executable}')
            elif not (Path(prefix) / 'share' / package / 'launch' / launch_file).is_file():
                raise RuntimeError(f'启动文件不存在：{package}/{launch_file}')
        for name in args.sensors:
            if stopping:
                return 130
            proc = subprocess.Popen(driver_command(name, args.microdia_device),
                                    env=env, start_new_session=True)
            processes.append((name, proc))
        print('驱动已发起启动，日志如下；收到数据才表示采集通过。Ctrl+C 停止。', flush=True)
        while not stopping:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    raise RuntimeError(f'{name} 启动进程已退出，退出码 {code}；停止本次其他驱动。')
            time.sleep(0.2)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'启动失败：{exc}', file=sys.stderr, flush=True)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(os.fsdecode(exc.stderr), file=sys.stderr)
        return 1
    finally:
        if processes:
            print('正在停止本次启动的驱动……', flush=True)
            stop_drivers(processes)
        for lock in locks:
            lock.close()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
