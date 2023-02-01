#include <json-c/json.h>
#include <string>

struct jsonrpc_request {
    bool notification;
    int64_t id;
    json_object *root_msg;
    std::string method;
    json_object *params;
};
struct security_package_counts {
    int64_t standard;
    int64_t esm_infra;
    int64_t esm_apps;
};

enum ESMType {APPS, INFRA};

bool read_jsonrpc_request(std::istream &in, jsonrpc_request &req);
bool string_ends_with(std::string str, std::string ends_with);
bool version_from_origin_and_archive_ends_with(json_object *version, std::string from_origin, std::string archive_ends_with);
bool count_security_packages_from_apt_stats_json(json_object *stats, security_package_counts &result);
std::string create_count_message(security_package_counts &counts);
int run();
