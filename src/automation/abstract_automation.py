import threading
import abc

class AbstractAutomation(threading.Thread, abc.ABC):
    def __init__(self):
        threading.Thread.__init__(self)
        self.paused = False
        self.stopped = False
        self.running = False
        self.pause_cond = threading.Condition(threading.Lock())
        self._stop_event = threading.Event()
        self._prev_url = None

    @abc.abstractmethod
    def run(self):
        # Example implementation
        self.running = True
        while True:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()
                if self.stopped:
                    break

                # Add your loop here

    def pause(self):
        self.paused = True
        self.pause_cond.acquire()

    def resume(self):
        self.paused = False
        self.pause_cond.notify()
        self.pause_cond.release()

    def stop(self):
        self._stop_event.set()
        self.stopped = True
