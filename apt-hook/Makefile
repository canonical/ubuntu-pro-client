all: build

build: json-hook

json-hook:
	$ GOCACHE=/tmp/ go build -buildmode=pie -ldflags "-extldgflags=-z,relro" -o json-hook .

install-conf:
	install -D -m 644 20apt-esm-hook.conf $(DESTDIR)/etc/apt/apt.conf.d/20apt-esm-hook.conf

install: json-hook
	install -D -m 755 json-hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-json-hook

clean:
	rm -f json-hook

.PHONY: all build install install-conf clean
