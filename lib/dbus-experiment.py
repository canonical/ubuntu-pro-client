import logging
import sys

import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject as gobject

import dbus

LOG = logging.getLogger("ubuntupro.dbus")


class HelloWorldService(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName(
            "com.ubuntu.BikeshedService", bus=dbus.SystemBus()
        )
        dbus.service.Object.__init__(
            self, bus_name, "/com/ubuntu/BikeshedService"
        )

    @dbus.service.method("com.ubuntu.BikeshedService")
    def hello_world(self):
        return "Hello, World!"


def main() -> int:
    DBusGMainLoop(set_as_default=True)
    hw_service = HelloWorldService()
    loop = gobject.MainLoop()
    loop.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
