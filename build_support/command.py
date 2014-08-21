"""handles abstraction of command execution on unix and windows"""
import os, subprocess, sys, shutil, atexit, signal, stat
import platform

def killMajorProcesses():
    return

# keep a list of subprocess, so they can be killed if the timeout
# mechanism expires
all_processes = {}

def kill_all_subprocesses():
    global all_processes
    sys.stdout.flush()

    for p in all_processes.keys():
        if p.poll() is None:
            # in unix, any subprocess the executes another command
            # will create a process that won't be killed.  We uses
            # process groups to manage
            # this. http://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true
            os.killpg(p.pid, signal.SIGTERM)

            try:
                p.terminate()
                p.kill()
            except:
                # If we couldn't kill the process, ignore errors if the process ended on it's own
                if p.poll():
                    return
                else:
                    print "Couldn't kill {0}".format(p)  # otherwise raise so we know a process is stuck
                    raise
    all_processes = {}

# signal has a different signature
def kill_all_subprocesses_signal(ignore, _):
    kill_all_subprocesses()

# register routine to kill subprocesses
atexit.register(kill_all_subprocesses)

signal.signal(signal.SIGINT, kill_all_subprocesses_signal)
signal.signal(signal.SIGABRT, kill_all_subprocesses_signal)
signal.signal(signal.SIGTERM, kill_all_subprocesses_signal)
signal.signal(signal.SIGFPE, kill_all_subprocesses_signal)
signal.signal(signal.SIGILL, kill_all_subprocesses_signal)
signal.signal(signal.SIGSEGV, kill_all_subprocesses_signal)

def system():
    return platform.system().lower()

def run_batch_command(commands, streamedOutput=True, noop=False, env = None, 
                      expected_return_code=0, quiet=False):
    if not env:
        env = {}

    # first command needs to have only \ path separators
    envStrs = [a[0]+"="+a[1] for a in env.items()]
    if not quiet:
        print " ".join(envStrs) + " " + " ".join(commands)
    sys.stdout.flush()

    procEnv = dict(os.environ.items() + env.items())

    if noop:
        return 0

    if streamedOutput is True:
        p = subprocess.Popen(commands, env=procEnv, 
                    preexec_fn=os.setsid)
    else:
        p = subprocess.Popen(commands, env=procEnv, 
                    preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    global all_processes
    all_processes[p] = True
    (out, err) = p.communicate()
    
    if (expected_return_code != None):
        if p.returncode != expected_return_code:
            raise subprocess.CalledProcessError(p.returncode,commands) 
    
    del all_processes[p]
    
    if out and not quiet:
        print out
    
    if err and not quiet:
        print err    
    
    return (out,err)

def on_error(func, path, _):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it prints an error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    # Is the error an access error ?

    os.chmod(path, stat.S_IWRITE)
    try:
        func(path)
    except:
        print "encountered deletion error for path: " + path
        raise

def rmfile(filename):
    # remove a read only file
    try:
        os.remove(filename)
    except OSError, e:
        on_error(rmfile, filename, None)

def rmtree(in_path):
    # DE3015 - if the tree has any unicode file/dir names in it, we
    # have to start with a unicode string.
    unicode_path = unicode(in_path)
    if os.path.exists(unicode_path):
        print "Deleting {0}".format(unicode_path)
        if os.path.isdir(unicode_path):
            shutil.rmtree(unicode_path, onerror=on_error)
        else:
            rmfile(unicode_path)

