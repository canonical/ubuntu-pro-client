GO_BIN = $(shell which go)
# Try go-1.14 and go-1.10 if not in path
ifeq ($(GO_BIN),)
	ifneq ($(wildcard /usr/lib/go-1.14/bin/go),)
		GO_BIN = /usr/lib/go-1.14/bin/go
	else ifneq ($(wildcard /usr/lib/go-1.10/bin/go),)
		GO_BIN = /usr/lib/go-1.10/bin/go
	endif
endif

GOPATH := $(HOME)/go
export GOPATH

all: build

build: json-hook

json-hook:
	GOCACHE=/tmp/ GOPATH=$(GOPATH) $(GO_BIN) build -buildmode=pie -ldflags "-extldflags=-z,relro" -o json-hook .

install-conf:
	install -D -m 644 20apt-esm-hook.conf $(DESTDIR)/etc/apt/apt.conf.d/20apt-esm-hook.conf

install: json-hook
	install -D -m 755 json-hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-json-hook

clean:
	rm -f json-hook

.PHONY: all build install install-conf clean
