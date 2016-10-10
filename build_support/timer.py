# Copyright (C) Intel Corp.  2014.  All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE COPYRIGHT OWNER(S) AND/OR ITS SUPPLIERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#  **********************************************************************/
#  * Authors:
#  *   Mark Janes <mark.a.janes@intel.com>
#  **********************************************************************/

import threading, time, os, signal, sys

from build_support import check_gpu_hang

def quit_all(to):
    if not to.is_expired():
        return to.start()

    print( "ERROR: *** component timed out.")
    check_gpu_hang(identify_test=False)
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

