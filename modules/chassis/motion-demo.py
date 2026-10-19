#!/usr/bin/env python3
"""Preview a ground-motion example; --run --clear-confirmed runs on Jetson.

Uses the installed official Rosmaster_Lib. Its constructor enables arm torque.
Speed/time targets are not measured distance/angle. No auto-increase or retry.
"""
import argparse
import contextlib
import signal
import subprocess
import sys
import threading
import time

PORT = '/dev/myserial'


class ReceiverStopped(Exception):
    """Local request to end the vendor's otherwise infinite receive loop."""


class InterruptibleSerial:
    def __init__(self, physical, stopped):
        self.physical, self.stopped = physical, stopped

    def __getattr__(self, name):
        return getattr(self.physical, name)

    def read(self, size=1):
        data = bytearray()
        while len(data) < size:
            if self.stopped.is_set():
                raise ReceiverStopped()
            data.extend(self.physical.read(size - len(data)))
        return bytes(data)


@contextlib.contextmanager
def managed_receiver(bot):
    """Use the verified 3.3.1 parser; stop/join its reader before serial close.

    This intentionally depends on a private vendor method in the archived version.
    It does not change the installed library or its public motion methods.
    """
    receive = getattr(bot, '_Rosmaster__receive_data', None)
    if receive is None:
        raise RuntimeError('Unsupported library receive implementation')
    physical = bot.ser
    old_timeout = physical.timeout
    physical.timeout = .05
    stopped = threading.Event()
    bot.ser = InterruptibleSerial(physical, stopped)
    failures = []

    def worker():
        try:
            receive()
        except ReceiverStopped:
            pass
        except Exception as error:
            failures.append(error)

    thread = threading.Thread(target=worker, name='motion-demo-receive')
    thread.start()
    try:
        yield failures
    finally:
        stopped.set()
        thread.join()  # Reads time out every .05 s; do not close under a live read.
        bot.ser = physical
        physical.timeout = old_timeout


def validate_board(version, car_type):
    if version != 3.5 or car_type != 2:
        raise RuntimeError(
            f'Board mismatch: firmware={version}, car_type={car_type}; '
            'expected 3.5 / X3PLUS type 2. Motion plan NOT sent. '
            'car_type=1 means the board reports X3 configuration; '
            'do not bypass this check or auto-reconfigure.'
        )
# name, vx (m/s), vy (m/s), wz (rad/s), duration (s)
PLAN = (
    ('forward', .20, 0., 0., 3.),
    ('backward', -.20, 0., 0., 3.),
    ('rotate-left', 0., 0., .5, 2.),
    ('rotate-right', 0., 0., -.5, 2.),
)


def hold(bot, vx, vy, wz, seconds):
    """Repeat velocity requests at about 10 Hz until the local timer expires."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        bot.set_car_motion(vx, vy, wz)
        time.sleep(min(.1, max(0., deadline - time.monotonic())))


def stop(bot):
    # These are stop requests; no claim of physical braking or emergency stop.
    for _ in range(3):
        bot.set_car_motion(0., 0., 0.)
        time.sleep(.05)


def interrupted(signum, _frame):
    raise SystemExit(f'Interrupted by signal {signum}; attempting stop in finally')


def execute(bot):
    """Run the plan with stop requests between steps and on Python unwinding."""
    try:
        stop(bot)
        for name, vx, vy, wz, seconds in PLAN:
            print(f'{name}: vx={vx}, vy={vy}, wz={wz}, seconds={seconds}', flush=True)
            try:
                hold(bot, vx, vy, wz, seconds)
            finally:
                stop(bot)
            print('Zero velocity requested. Observe the car during this pause.', flush=True)
            time.sleep(2.)
    finally:
        stop(bot)


@contextlib.contextmanager
def serial_available():
    import fcntl  # Linux only; preview also works on Windows.
    with open('/tmp/farm-arm-check.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owners = subprocess.run(['fuser', PORT], capture_output=True, text=True)
        if owners.returncode not in (0, 1) or owners.stdout.strip():
            raise RuntimeError('Serial is occupied or ownership cannot be checked')
        yield


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--configure-x3plus', action='store_true',
                      help='Explicitly persist board type 2, read it back, then exit without running the plan')
    parser.add_argument('--clear-confirmed', action='store_true',
                        help='Clear ground, no load, secured arm, onsite power cutoff; constructor enables torque')
    args = parser.parse_args()
    for row in PLAN:
        print(row)
    print('Pause 2 s after each step; predicted forward travel 0.30 m, each rotation 28.6 deg.')
    print('Predictions are speed x time only, not measured results or guaranteed return.')
    if not (args.run or args.configure_x3plus):
        print('PREVIEW ONLY: no library instance, serial access, or movement.')
        return 0
    if not args.clear_confirmed:
        parser.error('Hardware access requires --clear-confirmed, including arm torque side effect')
    if not sys.platform.startswith('linux'):
        parser.error('Run on the Jetson Linux host, not Windows')
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupted)
    from Rosmaster_Lib import Rosmaster
    with serial_available():
        bot = Rosmaster(car_type=2, com=PORT)  # Opens serial AND enables all arm torque.
        try:
            with managed_receiver(bot) as failures:
                time.sleep(.2)
                version = bot.get_version()
                car_type = bot.get_car_type_from_machine()
                print(f'Firmware={version}; board car_type={car_type}', flush=True)
                if failures:
                    raise RuntimeError(f'Receive thread failed: {failures[0]}')
                if args.configure_x3plus:
                    if version != 3.5 or car_type not in (1, 2):
                        raise RuntimeError('Unexpected firmware/type; configuration NOT written')
                    if car_type != 2:
                        print('Explicit configuration: persisting X3PLUS board type 2; no motion plan.', flush=True)
                        bot.set_car_type(2)
                        time.sleep(.2)
                    readback = bot.get_car_type_from_machine()
                    if failures:
                        raise RuntimeError(f'Receive thread failed: {failures[0]}')
                    if readback != 2:
                        raise RuntimeError(f'Configuration readback failed: {readback}; no retry or motion')
                    print('CONFIGURED: board car_type=2 read back. No motion plan executed.', flush=True)
                    return 0
                validate_board(version, car_type)
                print('Starting in 3 s. Ctrl+C attempts zero velocity; onsite cutoff remains required.', flush=True)
                time.sleep(3.)
                execute(bot)
                print('Command sequence completed. Motion accuracy and physical stop require observation.', flush=True)
        finally:
            try:
                # PWM zero is independent of the unconfirmed board car type.
                for _ in range(3):
                    bot.set_motor(0, 0, 0, 0)
                    time.sleep(.05)
            finally:
                bot.ser.close()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError) as error:
        print(f'ABORTED: {error}', file=sys.stderr)
        raise SystemExit(1)
