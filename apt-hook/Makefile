GO_BIN = $(shell which go)
# Try go-1.10 if not in path
ifeq ($(GO_BIN),)
    GO_BIN = /usr/lib/go-1.10/bin/go
endif

all: build

build: hook ubuntu-advantage.pot json-hook

ubuntu-advantage.pot: hook.cc
	xgettext hook.cc -o ubuntu-advantage.pot

hook: hook.cc
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o hook hook.cc -lapt-pkg $(LDLIBS)

json-hook:
	cd json-hook-src && GOCACHE=/tmp/ $(GO_BIN) build json-hook.go

install: hook json-hook
	install -D -m 644 20apt-esm-hook.conf $(DESTDIR)/etc/apt/apt.conf.d/20apt-esm-hook.conf
	install -D -m 755 hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-hook
	install -D -m 755 json-hook-src/json-hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-json-hook

clean:
	rm -f hook ubuntu-advantage.pot json-hook-src/json-hook

test:
	cd json-hook-src && GOCACHE=/tmp/ $(GO_BIN) test
