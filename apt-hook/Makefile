all: hook

hook: hook.cc
	$(CXX) -Wall -Wextra -pedantic $(CXXFLAGS) $(CPPFLAGS) $(LDFLAGS) -g -o hook hook.cc -lapt-pkg $(LDLIBS)

clean:
	rm -f hook
