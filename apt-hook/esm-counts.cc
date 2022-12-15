#include <apt-pkg/cachefile.h>
#include <apt-pkg/debversion.h>
#include <apt-pkg/error.h>
#include <apt-pkg/init.h>
#include <apt-pkg/pkgsystem.h>
#include <apt-pkg/strutl.h>

#include <string>
#include <vector>

#include "esm-counts.hh"

enum ESMSource { None, Apps, Infra, Both };

static ESMSource detect_esm_source(pkgCache::VerIterator esm_ver) {
   // check if any of the origins match an esm origin
   bool infra = false;
   bool apps = false;

   for (pkgCache::VerFileIterator pf = esm_ver.FileList(); !pf.end(); pf++) {
      if (DeNull(pf.File().Origin()) == std::string("UbuntuESM")) {
         infra = true;
      } else if (DeNull(pf.File().Origin()) == std::string("UbuntuESMApps")) {
         apps = true;
      }
   }

   if (infra && apps) {
      return Both;
   } else if (infra) {
      return Infra;
   } else if (apps) {
      return Apps;
   } else {
      return None;
   }
}

bool get_potential_esm_updates(ESMUpdates &updates) {
   if (!pkgInitConfig(*_config)) {
      return false;
   }

   // set up system cache
   if (!pkgInitSystem(*_config, _system)) {
      return false;
   }
   pkgCacheFile system_cachefile;
   pkgCache *system_cache = system_cachefile.GetPkgCache();
   if (system_cache == NULL) {
      return false;
   }

   // set up esm cache
   _config->Set("Dir", "/var/lib/ubuntu-advantage/apt-esm/");
   _config->Set("Dir::State::status", "/var/lib/ubuntu-advantage/apt-esm/var/lib/dpkg/status");
   if (!pkgInitSystem(*_config, _system)) {
      return false;
   }
   pkgCacheFile esm_cachefile;
   pkgCache *esm_cache = esm_cachefile.GetPkgCache();
   if (esm_cache == NULL) {
      return false;
   }

   // instantiate deb versioning system to use compare version function later
   debVersioningSystem deb_vs;

   // look for updates available in esm cache for system cache packages
   for (pkgCache::PkgIterator system_pkg = system_cache->PkgBegin(); !system_pkg.end(); system_pkg++) {
      pkgCache::VerIterator cur_system_ver = system_pkg.CurrentVer();
      if (cur_system_ver.end()) {
         // this package is not installed
         continue;
      }

      const char *name = system_pkg.Name();
      pkgCache::PkgIterator esm_pkg = esm_cache->FindPkg(name);
      if (esm_pkg.end()) {
         // this package is not in the esm cache
         continue;
      }

      pkgCache::VerIterator highest_esm_ver = esm_pkg.VersionList();
      if (highest_esm_ver.end()) {
         // this package doesn't have an available version in the esm cache
         continue;
      }

      char const * const cur_system_ver_str = cur_system_ver.VerStr();
      char const * const highest_esm_ver_str = highest_esm_ver.VerStr();
      if (
         deb_vs.DoCmpVersion(
            cur_system_ver_str,
            cur_system_ver_str + strlen(cur_system_ver_str),
            highest_esm_ver_str,
            highest_esm_ver_str + strlen(highest_esm_ver_str)
         ) > 0
      ) {
         // system ver is equal to or higher than esm ver
         continue;
      }

      ESMSource src = detect_esm_source(highest_esm_ver);
      if (src == Both) {
         updates.infra_packages.push_back(name);
         updates.apps_packages.push_back(name);
      } else if (src == Infra) {
         updates.infra_packages.push_back(name);
      } else if (src == Apps) {
         updates.apps_packages.push_back(name);
      }
   }

   if (_error->PendingError()) {
      std::cerr << "pro-hook: apt errors" << std::endl;
      _error->DumpErrors();
      return false;
   }

   return true;
}
