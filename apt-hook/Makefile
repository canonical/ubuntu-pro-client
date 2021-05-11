# the go hook steps will be skipped if this is a nonempty string
SKIP_GO_HOOK = ""

GO_BIN = $(shell which go)
# Try go-1.14 and go-1.10 if not in path
ifeq ($(GO_BIN),)
	ifneq ($(wildcard /usr/lib/go-1.14/bin/go),)
		GO_BIN = /usr/lib/go-1.14/bin/go
	else ifneq ($(wildcard /usr/lib/go-1.10/bin/go),)
		GO_BIN = /usr/lib/go-1.10/bin/go
	endif
endif

# If still not found then just don't build the go hook
ifeq ($(GO_BIN),)
	SKIP_GO_HOOK = "1"
endif

all: build

build: hook ubuntu-advantage.pot json-hook

ubuntu-advantage.pot: hook.cc
	xgettext hook.cc -o ubuntu-advantage.pot

hook: hook.cc
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o hook hook.cc -lapt-pkg $(LDLIBS)

json-hook:
	[ $(SKIP_GO_HOOK) ] || (cd json-hook-src && GOCACHE=/tmp/ $(GO_BIN) build -buildmode=pie -ldflags -extldflags=-z,relro json-hook.go)

install: hook json-hook
	install -D -m 644 20apt-esm-hook.conf $(DESTDIR)/etc/apt/apt.conf.d/20apt-esm-hook.conf
	install -D -m 755 hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-hook
	[ $(SKIP_GO_HOOK) ] || install -D -m 755 json-hook-src/json-hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-json-hook

clean:
	rm -f hook ubuntu-advantage.pot json-hook-src/json-hook

test:
	[ $(SKIP_GO_HOOK) ] || (cd json-hook-src && GOCACHE=/tmp/ $(GO_BIN) test)
