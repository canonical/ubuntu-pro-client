all: build

build: json-hook

json-hook: json-hook.cc
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o json-hook json-hook-main.cc json-hook.cc esm-counts.cc -ljson-c -lapt-pkg $(LDLIBS)

test:
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o json-hook-test json-hook.cc json-hook.test.cc esm-counts.cc -ljson-c -lapt-pkg -lboost_unit_test_framework $(LDLIBS)
	./json-hook-test

install-conf:
	install -D -m 644 20apt-esm-hook.conf $(DESTDIR)/etc/apt/apt.conf.d/20apt-esm-hook.conf

install: json-hook
	install -D -m 755 json-hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-json-hook

clean:
	rm -f json-hook json-hook-test

.PHONY: test
