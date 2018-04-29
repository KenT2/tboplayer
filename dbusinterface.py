import dbus
from dbus.service import Object
from dbus.mainloop.glib import DBusGMainLoop

TBOPLAYER_DBUS_OBJECT = "org.tboplayer.TBOPlayer"
TBOPLAYER_DBUS_PATH = "/org/tboplayer/TBOPlayer"
TBOPLAYER_DBUS_INTERFACE = "org.tboplayer.TBOPlayer"

class TBOPlayerDBusInterface (Object):
    tboplayer_instance = None

    def __init__(self, tboplayer_instance):
        self.tboplayer_instance = tboplayer_instance
        dbus_loop = DBusGMainLoop(set_as_default=True)
        bus_name = dbus.service.BusName(TBOPLAYER_DBUS_OBJECT, bus = dbus.SessionBus(mainloop = dbus_loop))
        Object.__init__(self, bus_name, TBOPLAYER_DBUS_PATH)

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE, in_signature = 'as')
    def openFiles(self, files):
        self.tboplayer_instance._add_files(files)

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE, in_signature='s')
    def openPlaylist(self, file):
        self.tboplayer_instance._open_list(file)

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE, in_signature='s')
    def openUrl(self, url):
        self.tboplayer_instance._add_url(url)

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE, in_signature = 'i')
    def play(self, track_index=0):
        self.tboplayer_instance.play_track_by_index(track_index)

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def pause(self):
        self.tboplayer_instance.toggle_pause()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def stop(self):
        self.tboplayer_instance.stop_track()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def next(self):
        self.tboplayer_instance.skip_to_next_track()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def previous(self):
        self.tboplayer_instance.skip_to_previous_track()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def fullscreen(self):
        self.tboplayer_instance.toggle_full_screen()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def volumnDown(self):
        self.tboplayer_instance.volminus()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def volumnUp(self):
        self.tboplayer_instance.volplus()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE)
    def clearList(self):
        self.tboplayer_instance.clear_list()

    @dbus.service.method(TBOPLAYER_DBUS_INTERFACE, in_signature='ss')
    def setOption(self, option, value):
        try:
            self.tboplayer_instance.set_option(option, value)
        except Exception, e:
            raise e

