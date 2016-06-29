from threading import Timer
import time
import sys
import os

class Watchdog:
    def __init__(self, timeout, userHandler=None):  # timeout in seconds
        self.timeout = timeout
        self.handler = userHandler if userHandler is not None else self.defaultHandler
        self.timer = Timer(self.timeout, self.handler)
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.timer = Timer(self.timeout, self.handler)
        self.timer.start()

    def stop(self):
        self.timer.cancel()

    def defaultHandler(self):
        ##### NOTE - check the __init__.py for the actual code which is run...
        print("Exit due to timeout.")
        print(".")
        time.sleep(5)
        os._exit(1)
        #raise self



if __name__ == "__main__":
    watchdog = Watchdog(5)

    print("Starting...")
    while True:
        time.sleep(1)
        print("Running...")

    watchdog.stop()