#include <libintl.h>

#include "json-hook.hh"

int main(int argc, char *argv[])
{
    (void) argc;
    (void) argv;
    setlocale(LC_ALL, "");
    textdomain("ubuntu-pro");
    return run();
}
