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

#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include <assert.h>
#include <sys/stat.h>
#include <libintl.h>
#include <locale.h>

#define MOTD_ESM_SERVICE_STATUS_MESSAGE_STATIC_PATH      "/var/lib/ubuntu-advantage/messages/motd-esm-service-status"
#define MOTD_APPS_NO_PKGS_TEMPLATE_PATH                  "/var/lib/ubuntu-advantage/messages/motd-no-packages-apps.tmpl"
#define MOTD_INFRA_NO_PKGS_TEMPLATE_PATH                 "/var/lib/ubuntu-advantage/messages/motd-no-packages-infra.tmpl"
#define MOTD_APPS_PKGS_TEMPLATE_PATH                     "/var/lib/ubuntu-advantage/messages/motd-packages-apps.tmpl"
#define MOTD_INFRA_PKGS_TEMPLATE_PATH                    "/var/lib/ubuntu-advantage/messages/motd-packages-infra.tmpl"
#define MOTD_APPS_PKGS_STATIC_PATH                       "/var/lib/ubuntu-advantage/messages/motd-packages-apps"
#define MOTD_INFRA_PKGS_STATIC_PATH                      "/var/lib/ubuntu-advantage/messages/motd-packages-infra"
#define APT_PRE_INVOKE_APPS_NO_PKGS_TEMPLATE_PATH        "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-apps.tmpl"
#define APT_PRE_INVOKE_INFRA_NO_PKGS_TEMPLATE_PATH       "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-infra.tmpl"
#define APT_PRE_INVOKE_APPS_PKGS_TEMPLATE_PATH           "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps.tmpl"
#define APT_PRE_INVOKE_APPS_PKGS_STATIC_PATH             "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps"
#define APT_PRE_INVOKE_INFRA_PKGS_TEMPLATE_PATH          "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra.tmpl"
#define APT_PRE_INVOKE_INFRA_PKGS_STATIC_PATH            "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra"
#define APT_PRE_INVOKE_MESSAGE_STATIC_PATH               "/var/lib/ubuntu-advantage/messages/apt-pre-invoke-esm-service-status"
#define UBUNTU_NO_WARRANTY_STATIC_PATH                   "/var/lib/ubuntu-advantage/messages/ubuntu-no-warranty"


#define ESM_APPS_PKGS_COUNT_TEMPLATE_VAR "{ESM_APPS_PKG_COUNT}"
#define ESM_APPS_PACKAGES_TEMPLATE_VAR "{ESM_APPS_PACKAGES}"
#define ESM_INFRA_PKGS_COUNT_TEMPLATE_VAR "{ESM_INFRA_PKG_COUNT}"
#define ESM_INFRA_PACKAGES_TEMPLATE_VAR "{ESM_INFRA_PACKAGES}"

enum Subcommand { PreInvoke, PostInvokeStats, PostInvokeSuccess, ProcessTemplates };

struct result {
   int enabled_esms_i;
   int disabled_esms_i;
   std::vector<std::string> esm_i_packages;

   int enabled_esms_a;
   int disabled_esms_a;
   std::vector<std::string> esm_a_packages;
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
         if (pf.File().Archive() != 0 && pf.File().Origin() == std::string("UbuntuESM"))
         {
            if (std::find(res.esm_i_packages.begin(), res.esm_i_packages.end(), pkg.Name()) == res.esm_i_packages.end()) {
                res.esm_i_packages.push_back(pkg.Name());

                // Pin-Priority: never unauthenticated APT repos == -32768
                if (policy->GetPriority(pf.File()) == -32768)
                {
                   res.disabled_esms_i++;
                }
                else
                {
                   res.enabled_esms_i++;
                }
            }
         }
         if (pf.File().Archive() != 0 && pf.File().Origin() == std::string("UbuntuESMApps"))
         {
            if (std::find(res.esm_a_packages.begin(), res.esm_a_packages.end(), pkg.Name()) == res.esm_a_packages.end()) {
                res.esm_a_packages.push_back(pkg.Name());

                // Pin-Priority: never unauthenticated APT repos == -32768
                if (policy->GetPriority(pf.File()) == -32768)
                {
                   res.disabled_esms_a++;
                }
                else
                {
                   res.enabled_esms_a++;
                }
            }
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


static void process_template_file(
   std::string template_file_name,
   std::string static_file_name,
   std::string esm_a_pkgs_count,
   std::string esm_a_pkgs,
   std::string esm_i_pkgs_count,
   std::string esm_i_pkgs
) {
   std::ifstream message_tmpl_file(template_file_name.c_str());
   if (message_tmpl_file.is_open()) {
      // This line loads the whole file contents into a string
      std::string message_tmpl((std::istreambuf_iterator<char>(message_tmpl_file)), (std::istreambuf_iterator<char>()));

      message_tmpl_file.close();

      // Process all template variables
      std::array<std::string, 4> tmpl_var_names = {
         ESM_APPS_PKGS_COUNT_TEMPLATE_VAR,
         ESM_APPS_PACKAGES_TEMPLATE_VAR,
         ESM_INFRA_PKGS_COUNT_TEMPLATE_VAR,
         ESM_INFRA_PACKAGES_TEMPLATE_VAR
      };
      std::array<std::string, 4> tmpl_var_vals = {
         esm_a_pkgs_count,
         esm_a_pkgs,
         esm_i_pkgs_count,
         esm_i_pkgs
      };
      for (uint i = 0; i < tmpl_var_names.size(); i++) {
         size_t pos = message_tmpl.find(tmpl_var_names[i]);
         if (pos != std::string::npos) {
            message_tmpl.replace(pos, tmpl_var_names[i].size(), tmpl_var_vals[i]);
         }
      }

      std::ofstream message_static_file(static_file_name.c_str());
      if (message_static_file.is_open()) {
         message_static_file << message_tmpl;
         message_static_file.close();
      }
   } else {
      remove(static_file_name.c_str());
   }
}

static void process_all_templates(
   int esm_a_pkgs_count,
   std::string esm_a_pkgs,
   int esm_i_pkgs_count,
   std::string esm_i_pkgs
) {
   int bytes_written;
   int length;
   std::array<std::string, 4> static_file_names = {
      APT_PRE_INVOKE_APPS_PKGS_STATIC_PATH,
      MOTD_APPS_PKGS_STATIC_PATH,
      APT_PRE_INVOKE_INFRA_PKGS_STATIC_PATH,
      MOTD_INFRA_PKGS_STATIC_PATH,
   };
   std::array<std::string, 3> apt_static_files = {
      APT_PRE_INVOKE_APPS_PKGS_STATIC_PATH,
      APT_PRE_INVOKE_INFRA_PKGS_STATIC_PATH,
      UBUNTU_NO_WARRANTY_STATIC_PATH
   };
   std::array<std::string, 3> motd_static_files = {
      MOTD_APPS_PKGS_STATIC_PATH,
      MOTD_INFRA_PKGS_STATIC_PATH,
      UBUNTU_NO_WARRANTY_STATIC_PATH
   };

   std::vector<std::string> template_file_names;
   if (esm_a_pkgs_count > 0) {
      template_file_names.push_back(APT_PRE_INVOKE_APPS_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_APPS_PKGS_TEMPLATE_PATH);
   } else {
      template_file_names.push_back(APT_PRE_INVOKE_APPS_NO_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_APPS_NO_PKGS_TEMPLATE_PATH);
   }
   if (esm_i_pkgs_count > 0) {
      template_file_names.push_back(APT_PRE_INVOKE_INFRA_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_INFRA_PKGS_TEMPLATE_PATH);
   } else {
      template_file_names.push_back(APT_PRE_INVOKE_INFRA_NO_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_INFRA_NO_PKGS_TEMPLATE_PATH);
   }
   for (uint i = 0; i < template_file_names.size(); i++) {
      process_template_file(
         template_file_names[i], 
         static_file_names[i], 
         std::to_string(esm_a_pkgs_count),
         esm_a_pkgs,
         std::to_string(esm_i_pkgs_count),
         esm_i_pkgs
      );
   }

   std::ofstream apt_pre_invoke_msg;
   apt_pre_invoke_msg.open(APT_PRE_INVOKE_MESSAGE_STATIC_PATH);
   for (uint i = 0; i < apt_static_files.size(); i++) {
       std::ifstream message_file(apt_static_files[i]);
       if (message_file.is_open()) {
           apt_pre_invoke_msg << std::endl;
           apt_pre_invoke_msg << message_file.rdbuf();
           message_file.close();
       };
   }
   bytes_written = apt_pre_invoke_msg.tellp();
   if (bytes_written > 0) {
       // Then we wrote some content add trailing newline
       apt_pre_invoke_msg << std::endl;
   }
   apt_pre_invoke_msg.close();
   if (bytes_written == 0) {
       // We added nothing. Remove the file
       remove(APT_PRE_INVOKE_MESSAGE_STATIC_PATH);
   }

   std::ofstream motd_msg;
   motd_msg.open(MOTD_ESM_SERVICE_STATUS_MESSAGE_STATIC_PATH);
   for (uint i = 0; i < motd_static_files.size(); i++) {
       std::ifstream message_file(motd_static_files[i]);
       if (message_file.is_open()) {
           message_file.seekg(0, message_file.end);
           length = message_file.tellg();
           if ( length > 0 ) {
               message_file.seekg(0, message_file.beg);
               if ( motd_msg.tellp() > 0 ) {
                   motd_msg << std::endl;
               }
               motd_msg << message_file.rdbuf();
           }
           message_file.close();
       };
   }
   bytes_written = motd_msg.tellp();
   if (bytes_written > 0) {
       // Then we wrote some content add trailing newline
       motd_msg << std::endl;
   }
   motd_msg.close();
   if (bytes_written == 0) {
       // We added nothing. Remove the file
       remove(MOTD_ESM_SERVICE_STATUS_MESSAGE_STATIC_PATH);
   }
}

static void output_file_if_present(std::string file_name) {
   std::ifstream message_file(file_name);
   if (message_file.is_open()) {
      std::cout << message_file.rdbuf();
      message_file.close();
   }
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
   Subcommand subcommand = ProcessTemplates;
   bool test_run = false;

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
   assert(!cmdline_eligible(make_cmdline("apt\0install\0")));
   assert(cmdline_eligible(make_cmdline("aptitude\0upgrade\0")));
   assert(cmdline_eligible(make_cmdline("aptitude\0update\0")));
   command_used = "";

   if (has_arg(argv, "test")) {
      // useful for testing
      test_run = true;
      command_used = "upgrade";
   }
   if (has_arg(argv, "pre-invoke")) {
      subcommand = PreInvoke;
   } else if (has_arg(argv, "post-invoke-stats")) {
      subcommand = PostInvokeStats;
   } else if (has_arg(argv, "post-invoke-success")) {
      subcommand = PostInvokeSuccess;
   } else if (has_arg(argv, "process-templates")) {
      subcommand = ProcessTemplates;
   }

   if (!test_run && subcommand != ProcessTemplates && !cmdline_eligible(getcmdline(getppid_of(getppid_of("self"))))) {
      // Only run on valid apt commands, or when being used to process templates
      return 0;
   }

   // Iterate over apt cache looking for esm packages
   result res = {0, 0, std::vector<std::string>(), 0, 0, std::vector<std::string>()};
   get_update_count(res);
   if (_error->PendingError())
   {
      _error->DumpErrors();
      return 1;
   }

   // Compute all strings necessary to fill in templates
   std::string space_separated_esm_i_packages = "";
   if (res.esm_i_packages.size() > 0) {
      for (uint i = 0; i < res.esm_i_packages.size() - 1; i++) {
         space_separated_esm_i_packages.append(res.esm_i_packages[i]);
         space_separated_esm_i_packages.append(" ");
      }
      space_separated_esm_i_packages.append(res.esm_i_packages[res.esm_i_packages.size() - 1]);
   }
   std::string space_separated_esm_a_packages = "";
   if (res.esm_a_packages.size() > 0) {
      for (uint i = 0; i < res.esm_a_packages.size() - 1; i++) {
         space_separated_esm_a_packages.append(res.esm_a_packages[i]);
         space_separated_esm_a_packages.append(" ");
      }
      space_separated_esm_a_packages.append(res.esm_a_packages[res.esm_a_packages.size() - 1]);
   }
   std::string esm_i_packages_count = std::to_string(res.esm_i_packages.size());
   std::string esm_a_packages_count = std::to_string(res.esm_a_packages.size());

   process_all_templates(
      res.esm_a_packages.size(),
      space_separated_esm_a_packages,
      res.esm_i_packages.size(),
      space_separated_esm_i_packages
   );

   // Execute specified subcommand
   if (subcommand == PreInvoke) {
      if (command_used == "upgrade" || command_used == "dist-upgrade") {
         output_file_if_present(APT_PRE_INVOKE_MESSAGE_STATIC_PATH);
      }
   }

   return 0;
}
