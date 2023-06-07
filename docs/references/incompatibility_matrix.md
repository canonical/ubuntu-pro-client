# Incompatibility matrix for Ubuntu Pro services

Some Ubuntu Pro services are incompatible with each other. The following
matrix display the services that are incompatible:

|                 | fips    | fips-updates   | livepatch   | realtime-kernel   |    
| ----------------|:-------:|:--------------:|:-----------:|:-----------------:|
| fips            |         |      X         |     X       |       X           |
| fips-updates    |   X     |                |     X       |       X           |
| livepatch       |   X     |      X         |             |       X           |
| realtime-kernel |   X     |      X         |     X       |                   |
