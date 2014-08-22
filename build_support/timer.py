import threading, time, os, signal, subprocess, sys

from build_support import command

def quit_all(to):
    if not to.is_expired():
        return to.start()

    print( "ERROR: *** component timed out.")
    sys.stdout.flush()
    os.kill(os.getpid(), signal.SIGINT)

class TimeOut:
    def __init__(self, time_limit):
        self._time_limit = time_limit
        self._duration = time_limit.GetDuration() * 60
        self._expiration = time.time() + self._duration
        self._timer = None

    def end(self):
        # if the timer is not cancelled, the outstanding thread will
        # prevent the parent process from completing
        self._timer.cancel()

    def start(self):
        time_remaining = self._expiration - time.time()
        print ("INFO: starting timer at: " + str(time.time()) + 
               ", time remaining is: " + str(time_remaining))
        sys.stdout.flush()
        assert(time_remaining > 0)

        self._timer = threading.Timer(time_remaining, lambda: quit_all(self))
        self._timer.start()


    def is_expired(self):
        # fuzz: within 10 seconds counts as expired
        if time.time() > (self._expiration - 10):
            return True
        print ("WARN: timer expired prematurely, at: " + str(time.time()) + 
               ", expected times is: " + str(self._expiration) )
        sys.stdout.flush()
        return False

