# Early review sign-off
As the Client has a very broad exception for SRUs, there are some features which
need pre-evaluation from people outside the team.

This pre-evaluation should be performed at specification time, even before any
implementation, to prevent frustration from any side when trying to SRU and to
avoid possible blockers for the process.

The review for such special features must be performed by:
1. A SRU team member, and
2. Someone from the Ubuntu Core Development team with appropriate expertise on
   the topic being changed.

There may be the case where a single person matches both of the descriptions
above - that is acceptable from the review perspective.

## Features which need special attention

The team should request the aforementioned pre-evaluation of any feature which
involves:

- How the Client interacts with APT
- How the Client interacts with systemd
- Anything that changes network traffic patterns, including anything
that might "phone home"
- Anything that changes the use of persistent processes or scheduled
jobs
- Changes that affect what part of the namespace in PATH we consume
- Actions that take place without an explicit user opt-in*

New items may be eventually added to this list
(preferrably before any problem happens!).


\* executing a CLI command to perform a specific task counts a
   opt-in for that task.
