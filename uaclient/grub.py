from uaclient import util


def update():
    # todo catch error and throw better error
    util.subp(["update-grub"])
