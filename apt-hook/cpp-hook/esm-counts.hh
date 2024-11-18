#ifndef PRO_ESM_COUNTS_H
#define PRO_ESM_COUNTS_H

#include <string>
#include <vector>

struct ESMUpdates {
   std::vector<std::string> infra_packages;
   std::vector<std::string> apps_packages;
};

bool get_potential_esm_updates(ESMUpdates &updates);

#endif
