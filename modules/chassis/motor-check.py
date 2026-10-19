#!/usr/bin/env python3
"""Jetson-only suspended-wheel test; raw verified Rosmaster 3.3.1 frames.

Default: read version and passive feedback only. --run --clear-confirmed:
channels 1..4, each positive then negative PWM, 0.5 s per pulse.
PWM defaults to 15; larger PWM/duration require explicit arguments. No auto-increase.
Zero PWM is a stop request, not a hardware emergency stop.
"""
import argparse
import collections
import fcntl
import json
import os
import select
import signal
import struct
import subprocess
import time

PORT = '/dev/myserial'


def frame(function, payload):
    fields = [255, 252, len(payload) + 3, function] + list(payload)
    return bytes(fields + [(sum(fields) + 5) & 255])


def send(port, packet):
    if port.write(packet) != len(packet):
        raise RuntimeError('Incomplete serial write')
    port.flush()


class Reader:
    def __init__(self, port):
        self.port, self.buffer = port, bytearray()
        self.counts = collections.Counter()
        self.bad = 0

    def capture(self, seconds):
        samples = []
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.buffer.extend(self.port.read(self.port.in_waiting or 1))
            while len(self.buffer) >= 4:
                index = self.buffer.find(b'\xff\xfb')
                if index < 0:
                    self.buffer[:] = self.buffer[-1:]
                    break
                del self.buffer[:index]
                if len(self.buffer) < 4:
                    break
                length = self.buffer[2]
                if not 3 <= length <= 64:
                    del self.buffer[0]
                    continue
                if len(self.buffer) < length + 2:
                    break
                packet = bytes(self.buffer[:length + 2])
                del self.buffer[:length + 2]
                if sum(packet[2:-1]) & 255 != packet[-1]:
                    self.bad += 1
                    continue
                function, data = packet[3], packet[4:-1]
                self.counts[function] += 1
                samples.append((time.monotonic(), function, data))
        return samples


def encoders(samples):
    return [(t, list(struct.unpack('<4i', d))) for t, f, d in samples
            if f == 13 and len(d) == 16]


def span(rows):
    if len(rows) < 5:
        raise RuntimeError('Insufficient fresh encoder feedback')
    return [max(v[i] for _, v in rows) - min(v[i] for _, v in rows)
            for i in range(4)]


def pulse(port, channel, pwm, seconds):
    """Independent child owns the bounded pulse and stop; parent reads only."""
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(read_fd)
        os.setsid()  # SSH/parent exit does not cancel the timed zero command.
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        status = 0
        try:
            values = [0] * 4
            values[channel - 1] = pwm & 255
            send(port, frame(16, values))
            os.write(write_fd, b'1')
            time.sleep(seconds)
        except BaseException:
            status = 1
        finally:
            try:
                for _ in range(3):
                    send(port, frame(16, [0] * 4))
                    time.sleep(.05)
            except BaseException:
                status = 2
            os.close(write_fd)
            os._exit(status)
    os.close(write_fd)
    ready, _, _ = select.select([read_fd], [], [], 1)
    ok = bool(ready) and os.read(read_fd, 1) == b'1'
    os.close(read_fd)
    if not ok:
        os.waitpid(child, 0)
        raise RuntimeError('Pulse worker did not acknowledge serial write')
    return child


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--clear-confirmed', action='store_true')
    parser.add_argument('--pwm', type=int, choices=(15, 25, 35), default=15)
    parser.add_argument('--pulse-seconds', type=float, choices=(.5, 1.0), default=.5)
    parser.add_argument('--channel', type=int, choices=(1, 2, 3, 4))
    args = parser.parse_args()
    if args.run and not args.clear_confirmed:
        parser.error('Confirm suspended wheels, clear area, no load, immediate power cutoff')
    import serial
    result = {'port': PORT, 'resolved': os.path.realpath(PORT),
              'pwm': args.pwm, 'pulse_seconds': args.pulse_seconds, 'tests': []}
    try:
        with open('/tmp/farm-arm-check.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            owners = subprocess.run(['fuser', PORT], capture_output=True, text=True)
            if owners.returncode not in (0, 1) or owners.stdout.strip():
                raise RuntimeError('Serial occupied or cannot verify ownership: ' + owners.stdout)
            with serial.Serial(PORT, 115200, timeout=.02, write_timeout=.3, exclusive=True) as port:
                reader = Reader(port)
                child = None
                try:
                    send(port, frame(80, [81, 0]))
                    samples = reader.capture(.7)
                    versions = [list(d) for _, f, d in samples if f == 81]
                    if not versions or versions[-1] != [3, 5]:
                        raise RuntimeError('Missing or unexpected firmware version: ' + str(versions))
                    result['firmware'] = versions[-1]
                    result['baseline_span'] = span(encoders(samples))
                    if max(result['baseline_span']) > 3:
                        raise RuntimeError('Wheels not stationary at baseline')
                    result['baseline_encoder'] = encoders(samples)[-1][1]
                    if args.run:
                        for channel in ([args.channel] if args.channel else range(1, 5)):
                            for pwm in (args.pwm, -args.pwm):
                                before = encoders(reader.capture(.3))
                                if max(span(before)) > 3:
                                    raise RuntimeError('Encoder drift before pulse')
                                start = before[-1][1]
                                print('PULSE', channel, pwm, flush=True)
                                child = pulse(port, channel, pwm, args.pulse_seconds)
                                samples = reader.capture(args.pulse_seconds + .8)
                                _, status = os.waitpid(child, 0)
                                child = None
                                if status:
                                    raise RuntimeError('Pulse worker failed: ' + str(status))
                                rows = encoders(samples)
                                if not rows:
                                    raise RuntimeError('No encoder feedback after pulse')
                                end = rows[-1][1]
                                delta = [b - a for a, b in zip(start, end)]
                                stopped = [(t, v) for t, v in rows if t >= rows[-1][0] - .4]
                                stop_span = span(stopped)
                                passed = (abs(delta[channel - 1]) >= 5
                                          and all(abs(d) <= 3 for i, d in enumerate(delta) if i != channel - 1)
                                          and max(stop_span) <= 3)
                                entry = dict(channel=channel, pwm=pwm, start=start, end=end,
                                             delta=delta, stop_span=stop_span,
                                             encoder_samples=len(rows), passed=passed)
                                result['tests'].append(entry)
                                print(json.dumps(entry), flush=True)
                                if not passed:
                                    raise RuntimeError('Movement/isolated channel/stop check failed; no auto-increase')
                            pair = result['tests'][-2:]
                            if pair[0]['delta'][channel-1] * pair[1]['delta'][channel-1] >= 0:
                                raise RuntimeError('Encoder directions did not reverse')
                    result['status'] = 'passed' if args.run else 'read-only'
                finally:
                    if child is not None:
                        os.waitpid(child, 0)  # Allow worker to finish timed stop before closing.
                    if args.run:
                        for _ in range(3):
                            send(port, frame(16, [0] * 4))
                            time.sleep(.05)
                    result['valid_frames'] = dict(reader.counts)
                    result['bad_checksums'] = reader.bad
    except Exception as exc:
        result['status'] = 'failed'
        result['error'] = str(exc)
    print('RESULT_JSON=' + json.dumps(result), flush=True)
    return 1 if result['status'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
