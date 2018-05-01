
class DnD:
    '''
    Python wrapper for the tkDnD tk extension.
    source: https://mail.python.org/pipermail/tkinter-discuss/2005-July/000476.html
    '''
    _subst_format = ('%A', '%a', '%T', '%W', '%X', '%Y', '%x', '%y','%D')
    _subst_format_str = " ".join(_subst_format)

    def __init__(self, tkroot):
        self._tkroot = tkroot
        tkroot.tk.eval('package require tkdnd')

    def bindtarget(self, widget, type=None, sequence=None, command=None, priority=50):
        command = self._generate_callback(command, self._subst_format)
        tkcmd = self._generate_tkcommand('bindtarget', widget, type, sequence, command, priority)
        res = self._tkroot.tk.eval(tkcmd)
        if type == None:
            res = res.split()
        return res

    def cleartarget(self, widget):
        '''Unregister widget as drop target.'''
        self._tkroot.tk.call('dnd', 'cleartarget', widget)

    def _generate_callback(self, command, arguments):
        '''Register command as tk callback with an optional list of arguments.'''
        cmd = None
        if command:
            cmd = self._tkroot._register(command)
            if arguments:
                cmd = '{%s %s}' % (cmd, ' '.join(arguments))
        return cmd

    def _generate_tkcommand(self, base, widget, *opts):
        '''Create the command string that will be passed to tk.'''
        tkcmd = 'dnd %s %s' % (base, widget)
        for i in opts:
            if i is not None:
                tkcmd += ' %s' % i
        return tkcmd

    def tcl_list_to_python_list(self, lst):
        tk_inst = self._tkroot.tk.eval
        tcl_list_len = int(tk_inst("set lst {%s}; llength $lst" % lst))
        result = []
        for i in range(tcl_list_len):
            result.append(tk_inst("lindex $lst %d" % i))
        return result

