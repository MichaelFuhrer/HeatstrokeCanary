import lib.BerryIMU.IMU as IMU
from collections import deque
import time
import threading
import numpy as np
from statistics import mean
import types


class motion_monitor:

    def __init__(self, verbose=False):
        # Top-level variables
        self.__is_parked = False
        self.__running = False
        self.__avg_motion = 0
        self.__motion_threshold = 4200
        self.__verbose = verbose

        # Internal thread/loop variables
        self.__thread = None
        self.__lock = threading.Lock()
        self.__pause_time = 0.1  # motion_monitor executes its internal loop every second

        # Debouncing variables
        self.__transition_time = 3  # Car must be in a new state for 5 seconds for self.__is_parked to update
        self.__debounce_time = time.time()

        # Event handlers
        self.__on_parked = None  # Function pointer that is called when the motion_monitor transitions to parked
        self.__on_moving = None  # Function pointer that is called when the motion_monitor transitions to not-parked

        # Deque used to calculate average motion
        self.__deque_size = 20
        self.__deque_count = 0
        self.__measurements = deque([0.0] * self.__deque_size, self.__deque_size)

        # Check connection w/ IMU and init it
        IMU.detectIMU()
        if IMU.BerryIMUversion == 99:
            raise RuntimeError("No BerryIMU detected on I2C Bus! Ensure connection is secure.")
        IMU.initIMU()

    # Creates a non-blocking thread that will periodically check IMU and update
    def start(self, on_parked: types.FunctionType = None, on_moving: types.FunctionType = None):
        if self.__thread is not None:
            raise RuntimeWarning("Motion monitor is already running!")
            return

        self.__on_parked = on_parked
        self.__on_moving = on_moving

        self.__running = True
        self.__thread = threading.Thread(target=self.__internal_start)
        self.__thread.start()

    def stop(self):
        if self.__thread is None:
            raise RuntimeWarning("Motion monitor is not running!")
            return

        with self.__lock:
            self.__running = False

        self.__thread.join()
        self.__thread = None

    def is_parked(self):
        with self.__lock:
            return self.__is_parked

    def get_avg_motion(self):
        with self.__lock:
            return self.__avg_motion

    def calibrate(self):
        print("Motion monitor calibrating; please lay the IMU down motionless on a steady table.")
        input("Press enter to start calibration...")
        print("Calibrating...", end='')
        for i in range(self.__deque_size):
            self.__queryIMU()
            if i % (self.__deque_size / 10) == 0:
                print('.', end='')

        self.__motion_threshold = self.__avg_motion + 25
        print("Calibration complete!")

    # Main monitor behavior loop
    def __internal_start(self):
        while self.__running:
            self.__queryIMU()
            self.__calc_whether_parked()
            time.sleep(self.__pause_time)

    def __internal_is_running(self):
        with self.__lock:
            return self.__running

    # Gets the magnitude of acceleration from the IMU, appends it to the measurements deque, and recalculates the
    # average acceleration
    def __queryIMU(self):
        acc = np.array([IMU.readACCx(), IMU.readACCy(), IMU.readACCz()])
        acc_mag = np.linalg.norm(acc)
        if self.__deque_count >= self.__deque_size:
            self.__measurements.pop()

        self.__measurements.appendleft(acc_mag)
        self.__deque_count = min(self.__deque_count + 1, self.__deque_size)
        # Recalculate average acceleration
        with self.__lock:
            self.__avg_motion = mean(list(self.__measurements)[0:self.__deque_count])
            if self.__verbose:
                print(f"Average Acceleration: {self.__avg_motion}\tThreshold:{self.__motion_threshold}")  # DEBUG

    # Uses a debouncing technique with the average acceleration to mark whether the car is parked or not
    def __calc_whether_parked(self):
        with self.__lock:
            if self.__is_parked:
                # Car is currently marked as parked
                if self.__avg_motion > self.__motion_threshold:
                    if time.time() > (self.__debounce_time + self.__transition_time):
                        # Car has been moving for more than transition time, update status
                        self.__is_parked = False
                        if self.__on_moving is not None:
                            self.__on_moving()
                else:
                    self.__debounce_time = time.time()
            else:
                # Car is currently marked as moving
                if self.__avg_motion <= self.__motion_threshold:
                    if time.time() > (self.__debounce_time + self.__transition_time):
                        # Car has been stationary for more than transition time, update status
                        self.__is_parked = True
                        if self.__on_parked is not None:
                            self.__on_parked()
                else:
                    self.__debounce_time = time.time()

            if self.__verbose:
                print(f"Parked: {str(self.__is_parked)}\tTimer: {(time.time() - self.__debounce_time)}")  # DEBUG


def main():
    try:
        mm = motion_monitor(verbose=True)
        mm.calibrate()
        mm.start()
        time.sleep(20)
    finally:
        mm.stop()


if __name__ == "__main__":
    main()
