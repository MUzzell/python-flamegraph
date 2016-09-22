import sys
import time
import inspect
import pprint
import argparse
import collections
import os
import site
import functools32
import traceback
times = collections.defaultdict(list)
stack = list()
stats = collections.defaultdict(float)
output = []
PATH = os.path.abspath(os.curdir)
main_thread = "main"

from .util import getsitepackages, get_threadname
from twisted.application import app
from twisted.scripts._twistd_unix import ServerOptions, \
        UnixApplicationRunner

sitepackages = getsitepackages()

import _lsprof

#import logging

class TwistedFlameGraphProfiler(app._BasicProfiler):
    """
    Runner for the cProfile module.
    """

    def run(self, reactor):
        """
        Run reactor under the cProfile profiler.
        """
        import pstats
        p = FlameGraphProfile()
        p.runcall(reactor.run)
        if self.saveStats:
            p.dump_stats(self.profileOutput)
        else:
            stream = open(self.profileOutput, 'w')
            s = pstats.Stats(p, stream=stream)
            s.strip_dirs()
            s.sort_stats(-1)
            s.print_stats()
            stream.close()


class FlameGraphProfile(_lsprof.Profiler):
    """Profile(custom_timer=None, time_unit=None, subcalls=True, builtins=True)

    Builds a profiler object using the specified timer function.
    The default timer is a fast built-in one based on real time.
    For custom timer functions returning integers, time_unit can
    be a float specifying a scale (i.e. how long each integer unit
    is, in seconds).
    """

    # Most of the functionality is in the base class.
    # This subclass only adds convenient and backward-compatible methods.

    def label(self, code):
        if isinstance(code, str):
            return ('~', 0, code)    # built-in functions ('~' sorts at the end)
        else:
            return (code.co_filename, code.co_firstlineno, code.co_name)

    def print_stats(self, sort=-1):
        import pstats
        pstats.Stats(self).strip_dirs().sort_stats(sort).print_stats()

    def dump_stats(self, file):
        #print "dumping stats"
        import marshal
        f = open(file, 'wb')
        self.create_stats()
        marshal.dump(self.stats, f)
        f.close()

    def create_stats(self):
        #print "create_stats"
        self.disable()
        self.snapshot_stats()

    def snapshot_stats(self):
        #print "snapshot_stats"
        entries = self.getstats()
        self.stats = {}
        callersdicts = {}
        # call information
        for entry in entries:
            #print entry
            func = self.label(entry.code)
            nc = entry.callcount         # ncalls column of pstats (before '/')
            cc = nc - entry.reccallcount # ncalls column of pstats (after '/')
            tt = entry.inlinetime        # tottime column of pstats
            ct = entry.totaltime         # cumtime column of pstats
            #print "%d %d %f %f" % (nc, cc,tt, ct)
            callers = {}
            callersdicts[id(entry.code)] = callers
            self.stats[func] = cc, nc, tt, ct, callers
        # subcall information
        for entry in entries:
            if entry.calls:
                func = self.label(entry.code)
                for subentry in entry.calls:
                    try:
                        callers = callersdicts[id(subentry.code)]
                    except KeyError:
                        continue
                    nc = subentry.callcount
                    cc = nc - subentry.reccallcount
                    tt = subentry.inlinetime
                    ct = subentry.totaltime
                    if func in callers:
                        prev = callers[func]
                        nc += prev[0]
                        cc += prev[1]
                        tt += prev[2]
                        ct += prev[3]
                    callers[func] = nc, cc, tt, ct

    # The following two methods can be called by clients to use
    # a profiler to profile a statement, given as a string.

    def run(self, cmd):
        import __main__
        dict = __main__.__dict__
        return self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals, locals):
        self.enable()
        try:
            exec cmd in globals, locals
        finally:
            self.disable()
        return self

    # This method is more useful to profile a single function call.
    def runcall(self, func, *args, **kw):
        self.enable()
        try:
            return func(*args, **kw)
        finally:
            self.disable()

@functools32.lru_cache()
def watching(path):
    path = os.path.dirname(path)
    if os.path.commonprefix((path, PATH)) == PATH:
        return True
    for sitepackage in sitepackages:
        if os.path.commonprefix((path, sitepackage)) in sitepackages:
            return True
    return False

def build_flamegraph_entry(frame):
    #print stack
    threadname = get_threadname()
    return "%s`%s.%s" % (
            threadname,
            frame.f_code.co_filename,
            frame.f_code.co_name)

def trace(frame, event, arg):
    try:
        if not watching(frame.f_code.co_filename):
            return
        #stack = times[id(frame)]
        #args = frame.f_code.co_varnames[:frame.f_code.co_argcount]
        #values = frame.f_locals
        if event == 'call':
            #print "call"
            stack.append(build_flamegraph_entry(frame))
        if event == 'return':
            #print stack
            #output.append(sys._current_frames())
            #output.append([(
            #    x.f_code.co_filename,
            #    x.f_code.co_name,
            #    time.time() - stack.pop()
            #    ) for x in sys._current_frames().values()])
            entry = ";".join(stack)
            stack.pop()
            stats[entry] += 1 #(time.time()-call_time)
            #output.append("%s %f" % (entry, time.time() - call_time))
        #if len(stack) == 0:
        #    del times[id(frame)]
        return trace
    except Exception as e:
        traceback.print_exc(e)

def run(args):

    try:
        import threading
        main_thread = threading.current_thread().ident
        #logging.info("Starting Now")
        #print sys.argv
        config = ServerOptions()
        config.parseOptions()
        #app.runReactorWithLogging(
        #    config,
        #    sys.stdout,
        #    sys.stderr,
        #    TwistedFlameGraphProfiler(config['profile'], False),
        #    None
        #)
        #runner = app.ApplicationRunner(config)
        #runner.profiler = TwistedFlameGraphProfiler("/tmp/twisted_flamegraph.log", False)
        #runner.startReactor(None, sys.stdout, sys.stderr )
        #runner.run()
        sys.settrace(trace)
        threading.settrace(trace)
        UnixApplicationRunner(config).run()
        #app.run(args[0], ServerOptions)
    except Exception as e:
        print e.message
    finally:
        #while threading.active_count() > 1:
        #    time.sleep(0.1)
        sys.settrace(None)
        threading.settrace(None)

    write_stats()

def write_stats():
    fd = open("/tmp/twisted_out", "w")
    for key in sorted(stats.keys()):
        fd.write("%s %f\n" % (key, stats[key]* 100))
    fd.close()

def print_output():
    #print "\n".join(["%s, %s, %f" %x for x in output])
    print "\n".join(output)
    pass


def process_args():
    #parser = argparse.ArgumentParser(prog='python -m flamegraph', description="Sample python stack frames for use with FlameGraph")
    #parser.add_argument('script_args', metavar='[arguments...]', type=str, nargs=argparse.REMAINDER,
    #   help='Arguments for script')

    #return parser.parse_args()
    return sys.argv

if __name__ == '__main__':
    args = process_args()
    run(args)
