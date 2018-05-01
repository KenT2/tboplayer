import sys
import logging
import cStringIO
import traceback
import dbus

class Logger(logging.Logger):
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, name, level=logging.INFO, logFile=None):
        logging.Logger.__init__(self, name, level=logging.INFO)
        if logFile is not None:
            self.setLogFile(logFile)
        log_sh = logging.StreamHandler()
        log_sh.setLevel(logging.NOTSET)
        log_sh.setFormatter(self.log_formatter)
        self.addHandler(log_sh)

    def enableLogging(self):
        self.setLevel(logging.DEBUG)

    def disableLogging(self):
        self.setLevel(logging.ERROR)

    def logException(self):
        s = cStringIO.StringIO()
        traceback.print_exc(file=s)
        self.error(s.getvalue())

    def setLogFile(self, filePath):
        log_fh = logging.FileHandler(filePath)
        log_fh.setLevel(logging.ERROR)
        log_fh.setFormatter(self.log_formatter)
        self.addHandler(log_fh)


# global logger
log = Logger(__file__)

class ExceptionCatcher:
    '''
    Exception handler for Tkinter
    when set to Tkinter.CallWrapper, catches unhandled exceptions thrown by window elements,
    logs the exception and signals quit to the erroring window.
    Exiting tboplayer is preferable when errors occure rather than possibly having
    uncontrollable omxplayer running in fullscreen.
    '''
    def __init__(self, func, subst, widget):
        self.func = func
        self.subst = subst
        self.widget = widget

    def __call__(self, *args):
        try:
            if self.subst:
                args = apply(self.subst, args)
            return apply(self.func, args)
        except dbus.DBusException:
            pass
        except SystemExit, msg:
            raise SystemExit, msg
        except Exception:
            log.logException()
            sys.exc_clear()

