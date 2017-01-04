'''
A very basic logger with some additional traceback information.

log = logger.Logger(__file__, logFile=LOG_FILE)
if __name__ == '__main__':
    logger.setExceptionHook(log)
log.info(message)
'''

import logging
import os
import traceback
import sys
import cStringIO

CRITICAL    = logging.CRITICAL
ERROR       = logging.ERROR
WARNING     = logging.WARNING
INFO        = logging.INFO
DEBUG       = logging.DEBUG
NOTSET      = logging.NOTSET


def setExceptionHook(logger):
    sys.excepthook = logger.handle_exception

class Logger(logging.Logger):
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, name, level=logging.INFO, logFile=None):
        logging.Logger.__init__(self, name, level=logging.INFO)


        if logFile is not None:
            self.setLogFile(logFile)

        log_sh = logging.StreamHandler()
        log_sh.setLevel(NOTSET)
        log_sh.setFormatter(self.log_formatter)
        self.addHandler(log_sh)

    def exc_plus(self):
        self.error(exc_plus())

    def setLogFile(self, filePath):
        log_fh = logging.FileHandler(filePath)
        log_fh.setLevel(NOTSET)
        log_fh.setFormatter(self.log_formatter)
        self.addHandler(log_fh)
        

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        self.error("Uncaught exception:\n%s\n%s: %s" % (exc_plus(tb=exc_traceback), exc_type.__name__, exc_value))


def exc_plus(trunc=3000, tb=None):
    """
    Return the usual traceback information, followed by a listing of all the
    local variables in each frame.
    """

    if tb is None and not any(sys.exc_info()):
        raise RuntimeError('No exception on stack')

    ret = cStringIO.StringIO()
    traceback.print_exc(file=ret)

    if tb is None:
        tb = sys.exc_info()[2]
    while 1:
        if not tb.tb_next:
            break
        tb = tb.tb_next
    stack = []
    f = tb.tb_frame
    while f:
        stack.append(f)
        f = f.f_back
    stack.reverse()

    ret.write(' '*4 + "Locals by frame, innermost last:\n")
    for frame in stack:
        ret.write(' '*6 + "Frame %s in %s at line %s:\n" % (frame.f_code.co_name, frame.f_code.co_filename, frame.f_lineno))
        for k, v in sorted(frame.f_locals.iteritems()):
            try:
                v = repr(v)
                if len(v) > trunc:
                    v = v[:trunc-len('---truncated---')]+'---truncated---'
                ret.write(' '*8 + '%-16s'%str(k) + ' = ' +  str(v)[:trunc] + '\n')
            except:
                ret.write(' '*8 + 'FAILED TO PRINT VALUE')
    return ret.getvalue()