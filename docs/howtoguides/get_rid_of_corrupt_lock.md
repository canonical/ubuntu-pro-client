# How to get rid of a corrupt lock

Some pro commands (`attach`, `enable`, `detach` and `disable`) will potentially change the
internal state of your system. Since those commands can run in parallel, we have a lock file
mechanism to guarantee that only one of these commands can run at the same time. The lock follows
this pattern:

```
PROCESS_PID:LOCK_HOLDER_NAME
```

Where:

*PROCESS_PID*: The PID of the process that is running the pro command
*LOCK_HOLDER_NAME*: The name of the command that is using the lock (i.e. `pro disable`)

If the lock file doesn't follow that pattern, we say that it is corrupted. That might happen if we
have any type of disk failures in the system. Once we detect a corrupted lock file, any of
the mentioned pro commands will generate the following output:

```
There is a corrupted lock file in the system. To continue, please remove it
from the system by running:

$ sudo rm /var/lib/ubuntu-advantage/lock
```

You can follow the instructions presented on the output to get rid of the corrupted lock.
After that, running the command should generate a correct lock file and continue as expected.
