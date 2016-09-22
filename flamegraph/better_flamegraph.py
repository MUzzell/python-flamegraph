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



@functools32.lru_cache()
def watching(path):
    path = os.path.dirname(path)
    if os.path.commonprefix((path, PATH)) == PATH:
        return True
    sitepackages = getsitepackages()
    for sitepackage in sitepackages:
        if os.path.commonprefix((path, sitepackage)) in sitepackages:
            return True
    return False

def build_flamegraph_entry(stack):
    #print stack
    threadname = get_threadname()
    return ";".join(["%s`%s.%s" % (threadname, frm[1].f_code.co_filename, frm[1].f_code.co_name) for frm in stack])

def trace(frame, event, arg):
    try:
        if not watching(frame.f_code.co_filename):
            return
        if event == 'call':
            #print "call"
            stack.append((time.time(), frame))
        if event == 'return':
            entry = build_flamegraph_entry(stack)
            call_time, frm = stack.pop()
            stats[entry] += (time.time()-call_time)
            output.append("%s %f" % (entry, time.time() - call_time))
        #if len(stack) == 0:
        #    del times[id(frame)]
        return trace
    except Exception as e:
        traceback.print_exc(e)

def setup(args):

    sys.argv = [args.script_file] + args.script_args
    sys.path.insert(0, os.path.dirname(args.script_file))

    script_compiled = compile(open(args.script_file, 'rb').read(), args.script_file, 'exec')
    script_globals = {'__name__': '__main__', '__file__': args.script_file, '__package__': None}
    return script_compiled, script_globals

def run(args, script_compiled, script_globals):

    try:
        import threading
        main_thread = threading.current_thread().ident
        sys.settrace(trace)
        threading.settrace(trace)
        exec(script_compiled, script_globals, script_globals)
    except:
        pass
    finally:
        while threading.active_count() > 1:
            time.sleep(0.1)
        sys.settrace(None)
        threading.settrace(None)



def print_stats():
    for key in sorted(stats.keys()):
        print "%s %f" % (key, stats[key]* 100)

def print_output():
    #print "\n".join(["%s, %s, %f" %x for x in output])
    print "\n".join(output)
    pass


def process_args():
    parser = argparse.ArgumentParser(prog='python -m flamegraph', description="Sample python stack frames for use with FlameGraph")
    parser.add_argument('script_file', metavar='script.py', type=str,
        help='Script to profile')
    parser.add_argument('script_args', metavar='[arguments...]', type=str, nargs=argparse.REMAINDER,
        help='Arguments for script')

    return parser.parse_args()


def main():
    args = process_args()
    script, script_args = setup()
    run(args, script, script_args)

if __name__ == '__main__':
    main()