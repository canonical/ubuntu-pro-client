#!/bin/bash
export GOPATH=/root/go
export PATH=$GOPATH/bin:/usr/local/go/bin:$PATH
cd /root/ua-contracts
make demo
