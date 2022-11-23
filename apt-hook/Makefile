all: build

build: hook ubuntu-advantage.pot json-hook

ubuntu-advantage.pot: hook.cc
	xgettext hook.cc -o ubuntu-advantage.pot

hook: hook.cc
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o hook hook.cc esm-templates.cc -lapt-pkg $(LDLIBS)

json-hook: json-hook.cc
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o json-hook json-hook-main.cc json-hook.cc esm-templates.cc -ljson-c -lapt-pkg $(LDLIBS)

test:
	$(CXX) -Wall -Wextra -pedantic -std=c++11 $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o json-hook-test json-hook.cc json-hook.test.cc esm-templates.cc -ljson-c -lapt-pkg -lboost_unit_test_framework $(LDLIBS)
	./json-hook-test

install-conf:
	install -D -m 644 20apt-esm-hook.conf $(DESTDIR)/etc/apt/apt.conf.d/20apt-esm-hook.conf

install: hook json-hook
	install -D -m 755 hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-hook
	install -D -m 755 json-hook $(DESTDIR)/usr/lib/ubuntu-advantage/apt-esm-json-hook

clean:
	rm -f hook json-hook json-hook-test ubuntu-advantage.pot

.PHONY: test
