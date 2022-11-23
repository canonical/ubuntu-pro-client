#include <apt-pkg/cachefile.h>
#include <apt-pkg/error.h>
#include <apt-pkg/init.h>
#include <apt-pkg/pkgsystem.h>
#include <apt-pkg/policy.h>
#include <apt-pkg/strutl.h>

#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "esm-templates.hh"


struct result {
   int enabled_esms_i;
   int disabled_esms_i;
   std::vector<std::string> esm_i_packages;

   int enabled_esms_a;
   int disabled_esms_a;
   std::vector<std::string> esm_a_packages;
};

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
         if (pf.File().Archive() != 0 && DeNull(pf.File().Origin()) == std::string("UbuntuESM"))
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
         if (pf.File().Archive() != 0 && DeNull(pf.File().Origin()) == std::string("UbuntuESMApps"))
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

void process_all_templates() {
   int bytes_written;
   int length;

   // Iterate over apt cache looking for esm packages
   result res = {0, 0, std::vector<std::string>(), 0, 0, std::vector<std::string>()};
   get_update_count(res);
   if (_error->PendingError())
   {
      _error->DumpErrors();
      return;
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

   std::array<std::string, 4> static_file_names = {
      APT_PRE_INVOKE_APPS_PKGS_STATIC_PATH,
      MOTD_APPS_PKGS_STATIC_PATH,
      APT_PRE_INVOKE_INFRA_PKGS_STATIC_PATH,
      MOTD_INFRA_PKGS_STATIC_PATH,
   };
   std::array<std::string, 2> apt_static_files = {
      APT_PRE_INVOKE_APPS_PKGS_STATIC_PATH,
      APT_PRE_INVOKE_INFRA_PKGS_STATIC_PATH,
   };
   std::array<std::string, 2> motd_static_files = {
      MOTD_APPS_PKGS_STATIC_PATH,
      MOTD_INFRA_PKGS_STATIC_PATH,
   };

   // Decide which templates to use (nopkg or pkg variants)
   std::vector<std::string> template_file_names;
   if (res.esm_a_packages.size() > 0) {
      template_file_names.push_back(APT_PRE_INVOKE_APPS_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_APPS_PKGS_TEMPLATE_PATH);
   } else {
      template_file_names.push_back(APT_PRE_INVOKE_APPS_NO_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_APPS_NO_PKGS_TEMPLATE_PATH);
   }
   if (res.esm_i_packages.size() > 0) {
      template_file_names.push_back(APT_PRE_INVOKE_INFRA_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_INFRA_PKGS_TEMPLATE_PATH);
   } else {
      template_file_names.push_back(APT_PRE_INVOKE_INFRA_NO_PKGS_TEMPLATE_PATH);
      template_file_names.push_back(MOTD_INFRA_NO_PKGS_TEMPLATE_PATH);
   }
   // Insert values into selected templates and render to separate file
   for (uint i = 0; i < template_file_names.size(); i++) {
      process_template_file(
         template_file_names[i], 
         static_file_names[i], 
         std::to_string(res.esm_a_packages.size()),
         space_separated_esm_a_packages,
         std::to_string(res.esm_i_packages.size()),
         space_separated_esm_i_packages
      );
   }

   // combine rendered files so that there is one apt file and one motd file
   // first apt
   std::ofstream apt_pre_invoke_msg;
   apt_pre_invoke_msg.open(APT_PRE_INVOKE_MESSAGE_STATIC_PATH);
   for (uint i = 0; i < apt_static_files.size(); i++) {
       std::ifstream message_file(apt_static_files[i]);
       if (message_file.is_open()) {
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

   // then motd
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
