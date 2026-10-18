#!/usr/bin/env python3
"""Jetson-only protocol probe and bounded servo-6 test; no ROS required.

Default: query firmware and servo positions. --move-servo6 --clear-confirmed:
move servo 6 by -10 degrees, dwell, return. Never enables torque or homes.
"""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time

import serial

PORT = '/dev/myserial'
OWNER = b'/home/jetson/Rosmaster/rosmaster/rosmaster_main.py'


def process_start(pid):
    return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[19]


@contextlib.contextmanager
def serial_access():
    # A stopped process retains its descriptor but cannot read or write.
    # Resume it without rerunning initialization, which would enable torque.
    result = subprocess.run(['fuser', PORT], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError('Cannot inspect serial ownership: ' + result.stderr)
    pids = [int(p) for p in result.stdout.split()]
    if len(pids) > 1:
        raise RuntimeError(f'Multiple serial users; refuse access: {pids}')
    pid = pids[0] if pids else None
    watchdog = None
    paused = False
    start = None
    try:
        if pid is not None:
            proc = Path(f'/proc/{pid}')
            if proc.stat().st_uid != os.getuid() or OWNER not in (proc / 'cmdline').read_bytes().split(b'\0'):
                raise RuntimeError(f'Unknown serial owner: {pid}')
            state = (proc / 'stat').read_text().split(') ', 1)[1].split()[0]
            if state in ('T', 't'):
                raise RuntimeError('Owner already stopped; do not change its state')
            start = process_start(pid)
            code = (
                'import os,signal,time;from pathlib import Path;time.sleep(30);'
                f'p=Path("/proc/{pid}/stat");'
                f'os.kill({pid},signal.SIGCONT) if p.exists() and '
                f'p.read_text().split(") ",1)[1].split()[19]=={start!r} else None'
            )
            watchdog = subprocess.Popen(
                ['python3', '-c', code], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            os.kill(pid, signal.SIGSTOP)
            paused = True
            time.sleep(.1)
            if (proc / 'stat').read_text().split(') ', 1)[1].split()[0] not in ('T', 't'):
                raise RuntimeError('Failed to pause original process')
            print('PAUSED_OWNER', pid, flush=True)
        with serial.Serial(PORT, 115200, timeout=.1, write_timeout=1, exclusive=True) as port:
            yield port
    finally:
        resumed = not paused
        if paused and process_start(pid) == start:
            os.kill(pid, signal.SIGCONT)
            resumed = True
            print('RESUMED_OWNER', pid, flush=True)
        if watchdog is not None and resumed:
            watchdog.terminate()


def send(port, data):
    port.write(bytes(data + [(sum(data) + 5) & 255]))
    port.flush()


def query(port, function, parameter=0):
    port.reset_input_buffer()
    send(port, [255, 252, 5, 80, function, parameter])
    buf = bytearray()
    deadline = time.monotonic() + .7
    while time.monotonic() < deadline:
        buf.extend(port.read(port.in_waiting or 1))
        while len(buf) >= 4:
            index = buf.find(b'\xff\xfb')
            if index < 0:
                buf[:] = buf[-1:]
                break
            if index:
                del buf[:index]
            if len(buf) < 4:
                break
            length = buf[2]
            if not 3 <= length <= 64:
                del buf[0]
                continue
            if len(buf) < length + 2:
                break
            packet = bytes(buf[:length + 2])
            del buf[:length + 2]
            if sum(packet[2:-1]) & 255 == packet[-1] and packet[3] == function:
                return packet[4:-1]
    raise RuntimeError(f'No valid reply: function={function}, parameter={parameter}')


def position(port, servo):
    data = query(port, 32, servo)
    if len(data) != 3:
        raise RuntimeError('Unexpected position reply size')
    sid, pulse = struct.unpack('<Bh', data)
    if sid != servo:
        raise RuntimeError('Unexpected servo ID')
    return pulse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--move-servo6', action='store_true')
    parser.add_argument('--clear-confirmed', action='store_true')
    args = parser.parse_args()
    if args.move_servo6 and not args.clear_confirmed:
        parser.error('Confirm empty workspace, no load and onsite power cutoff with --clear-confirmed')
    with open('/tmp/farm-arm-check.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with serial_access() as port:
            version = query(port, 81)
            if len(version) != 2:
                raise RuntimeError('Unexpected firmware reply')
            print('FIRMWARE', list(version), flush=True)
            readings = {sid: position(port, sid) for sid in range(1, 7)}
            print('SERVO_PULSES', json.dumps(readings), flush=True)
            if not args.move_servo6:
                return
            initial = readings[6]
            time.sleep(.2)
            stable = position(port, 6)
            if abs(stable - initial) > 5 or not 1100 <= stable <= 2900:
                raise RuntimeError('Servo 6 unstable or outside test margin')
            target = stable - 300  # About -10 degrees per inspected library mapping.
            def move(pulse):
                if not 1000 <= pulse <= 3000:
                    raise RuntimeError('Target outside test margin')
                send(port, [255, 252, 8, 32, 6, *struct.pack('<h', pulse), *struct.pack('<h', 2000)])
            print('MOVE_SERVO_6', stable, 'TO', target, 'DURATION_MS', 2000, flush=True)
            move(target)
            time.sleep(2.5)
            actual = position(port, 6)
            print('AFTER_OUT', actual, flush=True)
            if abs(actual - target) > 15:
                raise RuntimeError('Target not reached; no further command sent')
            time.sleep(3)
            move(stable)
            time.sleep(2.5)
            back = position(port, 6)
            print('AFTER_RETURN', back, 'ERROR_PULSES', back - stable, flush=True)
            if abs(back - stable) > 15:
                raise RuntimeError('Return position outside test tolerance')
            print('POSITION_FEEDBACK_PASSED; onsite visual confirmation still required', flush=True)


if __name__ == '__main__':
    main()
