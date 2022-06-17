from uaclient import util


def update():
    # TODO catch error and throw better error
    # TODO this might not be installed
    util.subp(["update-grub"])
