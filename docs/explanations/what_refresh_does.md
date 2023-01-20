# What `pro refresh` does

When you run the `pro refresh` command on your machine, three distinct stages
are performed.

## Contract

The contract information on the machine is refreshed. If we find any deltas
between the old contract and the new one, we process that delta and apply the
changes to the machine.

If you need *only* this stage during refresh, run `pro refresh contract`.

## Configuration

If there is any config change made to `/etc/ubuntu-advantage/uaclient.conf`,
those changes will now be applied to the machine.

If you need *only* this stage during refresh, run `pro refresh config`.

## MOTD and APT messages

Processes new MOTD and APT messages, and refreshes the machine to use them.

If you need *only* this stage during refresh, run `pro refresh messages`.
