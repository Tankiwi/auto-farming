#!/usr/bin/env python3
"""Bounded, relative, single-servo round-trip test on the Jetson host.

    from arm import test_motor
    result = test_motor(2, 5, 2000)  # ID, signed software degrees, milliseconds

No ROS, homing, automatic torque enabling, or movement retries.
"""
import argparse
import contextlib
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

PORT = '/dev/myserial'
OWNER = b'/home/jetson/Rosmaster/rosmaster/rosmaster_main.py'
LOCK = '/tmp/farm-arm-check.lock'  # Shared with arm-check.py.
TOLERANCE = 15
MAX_AMPLITUDE_DEG = 10
POSITION_MARGIN = 50  # Test boundary only; not calibrated mechanical limits.


def _mapping(motor_id):
    if motor_id in (1, 2, 3, 4):
        return 900, 3100, -2200 / 180
    if motor_id == 5:
        return 380, 3700, 3320 / 270
    return 900, 3100, 2200 / 180


def _angle(motor_id, position):
    low, _, units_per_degree = _mapping(motor_id)
    return (180 if motor_id <= 4 else 0) + (position - low) / units_per_degree


def _process_identity(pid):
    text = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
    return text[0], text[19]  # state, start time (not just a reusable PID)


@contextlib.contextmanager
def _serial_session():
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Run on the Jetson Linux host, not Windows or the tutorial container')
    import fcntl
    import serial

    with open(LOCK, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owners = subprocess.run(['fuser', PORT], capture_output=True, text=True)
        if owners.returncode not in (0, 1):
            raise RuntimeError('Cannot inspect serial ownership: ' + owners.stderr)
        pids = [int(item) for item in owners.stdout.split()]
        if len(pids) > 1:
            raise RuntimeError(f'Multiple serial owners: {pids}')
        pid = pids[0] if pids else None
        paused = False
        watchdog = None
        start = None
        try:
            if pid is not None:
                proc = Path(f'/proc/{pid}')
                if proc.stat().st_uid != os.getuid() or OWNER not in (proc / 'cmdline').read_bytes().split(b'\0'):
                    raise RuntimeError(f'Unknown serial owner: {pid}')
                state, start = _process_identity(pid)
                if state in ('T', 't'):
                    raise RuntimeError('Original process is already paused')
                rescue = (
                    'import time,os,signal;from pathlib import Path;time.sleep(30);'
                    f'p=Path("/proc/{pid}/stat");'
                    f'os.kill({pid},signal.SIGCONT) if p.exists() and '
                    f'p.read_text().split(") ",1)[1].split()[19]=={start!r} else None'
                )
                watchdog = subprocess.Popen(
                    ['python3', '-c', rescue], start_new_session=True,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                paused = True
                os.kill(pid, signal.SIGSTOP)
                time.sleep(.1)
                if _process_identity(pid) != ('T', start):
                    raise RuntimeError('Could not verify paused serial owner')
            with serial.Serial(PORT, 115200, timeout=.1, write_timeout=1, exclusive=True) as port:
                yield port
        finally:
            restored = not paused
            if paused:
                try:
                    _, current_start = _process_identity(pid)
                except FileNotFoundError:
                    restored = True  # Original exited; do not signal another process.
                else:
                    if current_start == start:
                        os.kill(pid, signal.SIGCONT)
                    restored = True
            if watchdog is not None and restored:
                watchdog.terminate()
                watchdog.wait(timeout=2)


def _send(port, fields):
    frame = bytes(fields + [(sum(fields) + 5) & 255])
    if port.write(frame) != len(frame):
        raise RuntimeError('Incomplete serial write; do not retry movement automatically')
    port.flush()


def _query(port, function, parameter=0):
    time.sleep(.12)  # Space read requests; this is not a proven timeout fix.
    port.reset_input_buffer()
    _send(port, [255, 252, 5, 80, function, parameter])
    buffer = bytearray()
    deadline = time.monotonic() + .7
    while time.monotonic() < deadline:
        buffer.extend(port.read(port.in_waiting or 1))
        while len(buffer) >= 4:
            index = buffer.find(b'\xff\xfb')
            if index < 0:
                buffer[:] = buffer[-1:]
                break
            del buffer[:index]
            if len(buffer) < 4:
                break
            length = buffer[2]
            if not 3 <= length <= 64:
                del buffer[0]
                continue
            if len(buffer) < length + 2:
                break
            packet = bytes(buffer[:length + 2])
            del buffer[:length + 2]
            if sum(packet[2:-1]) & 255 == packet[-1] and packet[3] == function:
                return packet[4:-1]
    raise RuntimeError(f'No valid reply: function={function}, parameter={parameter}')


def _read_position(port, motor_id):
    data = _query(port, 32, motor_id)
    if len(data) != 3:
        raise RuntimeError('Unexpected position reply size')
    returned_id, position = struct.unpack('<Bh', data)
    if returned_id != motor_id:
        raise RuntimeError('Reply servo ID does not match request')
    return position


def test_motor(motor_id, amplitude_deg, duration_ms):
    """Test one servo, moving relative to current position then returning.

    motor_id: integer 1..6. amplitude_deg: signed software angle, 0 < abs <= 10.
    duration_ms: integer 500..2000, PER DIRECTION, not the whole test duration.
    Caller must ensure a stationary chassis, clear workspace, no load and an
    onsite power cutoff. Does not enable torque, calibrate, or clear faults.
    Returns a dict. Only status='passed' means both feedback checks passed;
    this does not verify physical limits or replace onsite observation.
    On outbound failure there is NO automatic return, compensation or retry.
    Communication/OS errors raise exceptions; cleanup resumes the known owner.
    """
    if type(motor_id) is not int or motor_id not in range(1, 7):
        raise ValueError('motor_id must be an integer from 1 to 6')
    if isinstance(amplitude_deg, bool) or not isinstance(amplitude_deg, (int, float)):
        raise ValueError('amplitude_deg must be a finite number')
    if not math.isfinite(amplitude_deg) or not 0 < abs(amplitude_deg) <= MAX_AMPLITUDE_DEG:
        raise ValueError('Use a nonzero amplitude between -10 and +10 degrees')
    if type(duration_ms) is not int or not 500 <= duration_ms <= 2000:
        raise ValueError('duration_ms must be an integer from 500 to 2000 milliseconds')
    low, high, units_per_degree = _mapping(motor_id)
    step = round(amplitude_deg * units_per_degree)
    if abs(step) < 2:
        raise ValueError('Amplitude is too small for this position resolution')
    with _serial_session() as port:
        version = _query(port, 81)
        if len(version) != 2:
            raise RuntimeError('Unexpected firmware reply')
        samples = [_read_position(port, motor_id) for _ in range(3)]
        if max(samples) - min(samples) > 5:
            raise RuntimeError('Current position is unstable; no movement sent')
        start = samples[-1]
        target = start + step
        if not all(low + POSITION_MARGIN <= value <= high - POSITION_MARGIN for value in (*samples, target)):
            raise ValueError('Current or target position outside the test boundary; no movement sent')
        result = {
            'motor_id': motor_id, 'requested_delta_deg': amplitude_deg,
            'duration_ms_per_direction': duration_ms, 'firmware': list(version),
            'start_position': start, 'target_position': target,
            'start_angle_deg': round(_angle(motor_id, start), 3),
            'target_angle_deg': round(_angle(motor_id, target), 3),
            'return_command_sent': False, 'tolerance_units': TOLERANCE,
        }

        def move(position):
            _send(port, [255, 252, 8, 32, motor_id,
                         *struct.pack('<h', position), *struct.pack('<h', duration_ms)])
            time.sleep(duration_ms / 1000 + .5)

        move(target)
        actual = _read_position(port, motor_id)
        moved = abs(actual - start) >= max(2, abs(step) / 2)
        result.update(out_position=actual, out_error_units=actual - target,
                      actual_delta_deg=round((actual - start) / units_per_degree, 3))
        if not moved:
            result['status'] = 'no_movement'
            return result
        if abs(actual - target) > TOLERANCE:
            result['status'] = 'target_not_reached'
            return result
        time.sleep(1)
        result['return_command_sent'] = True
        move(start)
        back = _read_position(port, motor_id)
        result.update(return_position=back, return_error_units=back - start)
        result['status'] = 'passed' if abs(back - start) <= TOLERANCE else 'return_out_of_tolerance'
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('motor_id', type=int, help='Servo ID, 1..6')
    parser.add_argument('amplitude_deg', type=float, help='Signed relative software angle, max 10 degrees')
    parser.add_argument('duration_ms', type=int, help='Time per direction, 500..2000 milliseconds')
    args = parser.parse_args()
    try:
        result = test_motor(args.motor_id, args.amplitude_deg, args.duration_ms)
    except (ValueError, RuntimeError, OSError, ImportError) as error:
        print(f'Test aborted: {error}. No automatic retry; check the arm before running again.', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
