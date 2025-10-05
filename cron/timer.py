"Return elapsed time and CPU time."

import time


class Timer:
    "Return elapsed time and CPU time since creation of the instance."

    def __init__(self):
        self.time = time.time()
        self.process_time = time.process_time()

    def __str__(self):
        return ", ".join([f"{k}={v:.3f}" for k, v in self().items()])

    def __call__(self):
        return {"elapsed time": time.time() - self.time,
                "CPU time": time.process_time() - self.process_time}


if __name__ == "__main__":
    timer = Timer()
    time.sleep(1)
    for a in range(1_000_000):
        b = a + a
    print(str(timer))
