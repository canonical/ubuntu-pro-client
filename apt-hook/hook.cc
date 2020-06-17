/*
 * Copyright (C) 2018-2019 Canonical Ltd
 * Author: Julian Andres Klode <juliank@ubuntu.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3 of the License.
 *
 * This package is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
*/

#include <apt-pkg/cachefile.h>
#include <apt-pkg/error.h>
#include <apt-pkg/init.h>
#include <apt-pkg/pkgsystem.h>
#include <apt-pkg/policy.h>
#include <apt-pkg/strutl.h>

#include <fstream>
#include <sstream>
#include <string>

#include <assert.h>
#include <sys/stat.h>
#include <libintl.h>
#include <locale.h>

struct result {
   int enabled_esms_i;
   int disabled_esms_i;
   int enabled_esms_a;
   int disabled_esms_a;
};

// Return parent pid of specified pid, using /proc (pid might be self)
static std::string getppid_of(std::string pid)
{
   std::string status_path;
   std::string line;

   if (pid == "")
      return "";

   strprintf(status_path, "/proc/%s/status", pid.c_str());

   std::ifstream stream(status_path.c_str(), std::ios::in);

   while (not stream.fail()) {
      getline(stream, line);

      if (line.find("PPid:") != 0)
	 continue;

      // Erase everything before a number
      line.erase(0, line.find_first_of("0123456789"));

      return line;
   }

   return "";
}

// Get cmdline of specified pid. Arguments terminated with 0
static std::string getcmdline(std::string pid)
{
   std::string cmdline_path;

   if (pid == "")
      return "";

   strprintf(cmdline_path, "/proc/%s/cmdline", pid.c_str());
   std::ifstream stream(cmdline_path.c_str(), std::ios::in);
   std::ostringstream cmdline;
   char buf[4096];

   do
   {
      stream.read(buf, sizeof(buf));
      cmdline.write(buf, stream.gcount());
   } while (stream.gcount() > 0);

   return cmdline.str();
}

// Check if a cmdline is eligible for showing ESM updates. Only apt
// update and the various upgrade commands are
static std::string command_used;
static bool cmdline_eligible(std::string const &cmdline)
{
   const std::string commands[] = {"update", "upgrade", "dist-upgrade", "full-upgrade", "safe-upgrade"};

   for (size_t i = 0; i < sizeof(commands) / sizeof(commands[0]); i++)
   {
      if (cmdline.find('\0' + commands[i] + '\0') != std::string::npos)
      {
         command_used = commands[i];
         return true;
      }
   }

   return false;
}

// Check if we have an ESM upgrade for the specified package
static void check_esm_upgrade(pkgCache::PkgIterator pkg, pkgPolicy *policy, result &res)
{
   pkgCache::VerIterator cur = pkg.CurrentVer();

   if (cur.end())
      return;

   // Search all versions >= cur (list in decreasing order)
   for (pkgCache::VerIterator ver = pkg.VersionList(); !ver.end() && ver->ID != cur->ID; ver++)
   {
      for (pkgCache::VerFileIterator pf = ver.FileList(); !pf.end(); pf++)
      {
	 // TODO: Just look at the origin, not pinning.
	 if (pf.File().Archive() != 0 && pf.File().Origin() == std::string("UbuntuESM"))
	 {
	    if (policy->GetPriority(pf.File()) == -32768)
	       res.disabled_esms_i++;
	    else
	       res.enabled_esms_i++;

	    return;
	 }

	 if (pf.File().Archive() != 0 && pf.File().Origin() == std::string("UbuntuESMApps"))
	 {
	    if (policy->GetPriority(pf.File()) == -32768)
	       res.disabled_esms_a++;
	    else
	       res.enabled_esms_a++;

	    return;
	 }
      }
   }
}

// Calculate the update count
static int get_update_count(result &res)
{
   int count = 0;
   if (!pkgInitConfig(*_config))
      return -1;

   if (!pkgInitSystem(*_config, _system))
      return -1;

   pkgCacheFile cachefile;

   pkgCache *cache = cachefile.GetPkgCache();
   pkgPolicy *policy = cachefile.GetPolicy();

   if (cache == NULL || policy == NULL)
      return -1;

   for (pkgCache::PkgIterator pkg = cache->PkgBegin(); !pkg.end(); pkg++)
   {
      check_esm_upgrade(pkg, policy, res);
   }
   return count;
}

// Preserves \0 bytes in a string literal
template<std::size_t n>
std::string make_cmdline(const char (&s)[n])
{
   return std::string(s, n);
}

bool has_arg(char **argv, const char *arg)
{
   for (; *argv; argv++) {
      if (strcmp(*argv, arg) == 0)
         return true;
   }
   return false;
}

int main(int argc, char *argv[])
{
   (void) argc;   // unused
   setlocale(LC_ALL, "");
   textdomain("ubuntu-advantage");
   // Self testing
   // Dropped: see #1824523
   // if (access("/proc/self/status", R_OK) == 0) {
   //    std::string ppid;
   //    strprintf(ppid, "%d", getppid());
   //    assert(ppid == getppid_of("self"));
   // }
   assert(cmdline_eligible(make_cmdline("apt\0update\0")));
   //assert(cmdline_eligible(make_cmdline("apt-get\0update\0")));
   //assert(!cmdline_eligible(make_cmdline("apt-get\0install\0")));
   assert(!cmdline_eligible(make_cmdline("apt\0install\0")));
   assert(cmdline_eligible(make_cmdline("aptitude\0upgrade\0")));
   assert(cmdline_eligible(make_cmdline("aptitude\0update\0")));
   command_used = "";

   result res = {0, 0, 0, 0};

   // useful for testing
   if (has_arg(argv, "test"))
      command_used = "update";

   if (has_arg(argv, "test") || cmdline_eligible(getcmdline(getppid_of(getppid_of("self")))))
      get_update_count(res);
   if (_error->PendingError())
   {
      _error->DumpErrors();
      return 1;
   }

   if (command_used == "update")
   {
      if (res.enabled_esms_i > 0)
      {
         ioprintf(std::cout,
                  ngettext("%d of the updates is from UA Infrastructure ESM.",
                           "%d of the updates are from UA Infrastructure ESM.",
                           res.enabled_esms_i),
                  res.enabled_esms_i);
         ioprintf(std::cout, "\n");
      }
      if (res.enabled_esms_a > 0)
      {
         ioprintf(std::cout,
                  ngettext("%d of the updates is from UA Apps ESM.",
                           "%d of the updates are from UA Apps ESM.",
                           res.enabled_esms_a),
                  res.enabled_esms_a);
         ioprintf(std::cout, "\n");
      }
   }

   if (res.disabled_esms_i > 0 || res.disabled_esms_a > 0)
   {
      if (command_used != "update")
         std::cout << std::endl;
      if (res.disabled_esms_i > 0)
      {
         ioprintf(std::cout,
                  ngettext("%d additional update is available with UA Infrastructure ESM.",
                           "%d additional updates are available with UA Infrastructure ESM.",
                           res.disabled_esms_i),
                  res.disabled_esms_i);
         ioprintf(std::cout, "\n");
      }
      if (res.disabled_esms_a > 0)
      {
         ioprintf(std::cout,
                  ngettext("%d additional update is available with UA Apps ESM.",
                           "%d additional updates are available with UA Apps ESM.",
                           res.disabled_esms_a),
                  res.disabled_esms_a);
         ioprintf(std::cout, "\n");
      }

      ioprintf(std::cout, gettext("To see these additional updates run: apt list --upgradable"));
      ioprintf(std::cout, "\n");
      ioprintf(std::cout, gettext("See https://ubuntu.com/advantage or run: sudo ua status"));
      ioprintf(std::cout, "\n");
   }

   return 0;
}
