#! /bin/bash
shellcheck -S warning -C always -P tools/{*.sh,make-release,make-tarball} \
-P demo/{*.sh,demo-contract-service} \
-P lib/*.sh \
-P sru/release-27{,.3,.5,.8}/*.sh \
-P update-motd.d/** \
