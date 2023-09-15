#include <ext/stdio_filebuf.h>
#include <fstream>
#include <iostream>
#include <json-c/json.h>
#include <sstream>
#include <string>
#include <vector>

#include "json-hook.hh"
#include "esm-counts.hh"

bool read_jsonrpc_request(std::istream &in, jsonrpc_request &req) {
    std::string msg_line;
    std::string empty_line;
    getline(in, msg_line);
    getline(in, empty_line);
    json_object *msg = json_tokener_parse(msg_line.c_str());
    json_object *tmp;
    bool has_key = false;

    has_key = json_object_object_get_ex(msg, "jsonrpc", &tmp);
    if (!has_key) {
        json_object_put(msg);
        return false;
    }
    std::string msg_jsonrpc_version(json_object_get_string(tmp));
    if (msg_jsonrpc_version != "2.0") {
        json_object_put(msg);
        return false;
    }

    has_key = json_object_object_get_ex(msg, "method", &tmp);
    if (!has_key) {
        json_object_put(msg);
        return false;
    }
    std::string msg_method(json_object_get_string(tmp));
    req.method = msg_method;

    has_key = json_object_object_get_ex(msg, "params", &tmp);
    if (!has_key) {
        json_object_put(msg);
        return false;
    }
    req.params = tmp;

    has_key = json_object_object_get_ex(msg, "id", &tmp);
    if (has_key) {
        req.id = json_object_get_int64(tmp);
        req.notification = false;
    } else {
        req.notification = true;
    }

    req.root_msg = msg;

    return true;
}

bool string_ends_with(std::string str, std::string ends_with) {
    if (str.length() >= ends_with.length()) {
        int result = ends_with.compare(0, ends_with.length(), str, str.length() - ends_with.length(), ends_with.length());
        return result == 0;
    }
    return false;
}

bool version_from_origin_and_archive_ends_with(json_object *version, std::string from_origin, std::string archive_ends_with) {
    bool has_key = false;
    json_object *origins;
    has_key = json_object_object_get_ex(version, "origins", &origins);
    if (!has_key) {
        return false;
    }
    int64_t origins_length = json_object_array_length(origins);

    for (int64_t i = 0; i < origins_length; i++) {
        json_object *origin = json_object_array_get_idx(origins, i);

        json_object *tmp;
        has_key = json_object_object_get_ex(origin, "origin", &tmp);
        if (!has_key) {
            continue;
        }
        std::string origin_origin(json_object_get_string(tmp));
        has_key = json_object_object_get_ex(origin, "archive", &tmp);
        if (!has_key) {
            continue;
        }
        std::string origin_archive(json_object_get_string(tmp));

        if (origin_origin == from_origin && string_ends_with(origin_archive, archive_ends_with)) {
            return true;
        }
    }

    return false;
}

bool count_security_packages_from_apt_stats_json(json_object *stats, security_package_counts &result) {
    bool has_key = false;
    result.standard = 0;
    result.esm_infra = 0;
    result.esm_apps = 0;

    json_object *packages;
    has_key = json_object_object_get_ex(stats, "packages", &packages);
    if (!has_key) {
        return false;
    }
    int64_t packages_length = json_object_array_length(packages);

    for (int64_t i = 0; i < packages_length; i++) {
        json_object *package = json_object_array_get_idx(packages, i);

        json_object *tmp;
        has_key = json_object_object_get_ex(package, "mode", &tmp);
        if (!has_key) {
            continue;
        }
        std::string package_mode(json_object_get_string(tmp));

        if (package_mode == "upgrade") {
            json_object *versions;
            has_key = json_object_object_get_ex(package, "versions", &versions);
            if (!has_key) {
                continue;
            }

            json_object *install;
            has_key = json_object_object_get_ex(versions, "install", &install);
            if (!has_key) {
                continue;
            }

            if (version_from_origin_and_archive_ends_with(install, "UbuntuESMApps", "-apps-security")) {
                result.esm_apps += 1;
            } else if (version_from_origin_and_archive_ends_with(install, "UbuntuESM", "-infra-security")) {
                result.esm_infra += 1;
            } else if (version_from_origin_and_archive_ends_with(install, "Ubuntu", "-security")) {
                result.standard += 1;
            }
        }
    }

    return true;
}

std::string create_count_message(security_package_counts &counts) {
    std::vector<std::string> count_msgs;

    if (counts.standard + counts.esm_infra + counts.esm_apps == 0) {
        return "";
    }

    if (counts.standard > 0) {
        std::stringstream ss;
        ss << counts.standard << " standard LTS security update";
        if (counts.standard != 1) {
            ss << "s";
        }
        count_msgs.push_back(ss.str());
    }
    if (counts.esm_infra > 0) {
        std::stringstream ss;
        ss << counts.esm_infra << " esm-infra security ";
        ss << "update";
        if (counts.esm_infra != 1) {
            ss << "s";
        }
        count_msgs.push_back(ss.str());
    }
    if (counts.esm_apps > 0) {
        std::stringstream ss;
        ss << counts.esm_apps << " esm-apps security ";
        ss << "update";
        if (counts.esm_apps != 1) {
            ss << "s";
        }
        count_msgs.push_back(ss.str());
    }

    std::stringstream message_ss;
    for (uint i = 0; i < count_msgs.size(); i++) {
        if (count_msgs.size() == 3) {
            if (i == 1) {
                message_ss << ", ";
            } else if (i == 2) {
                message_ss << " and ";
            }
        } else if (count_msgs.size() == 2) {
            if (i == 1) {
                message_ss << " and ";
            }
        }
        message_ss << count_msgs[i];
    }

    return message_ss.str();
}

enum CloudID {AWS, AZURE, GCE, NONE};

CloudID get_cloud_id() {
    std::ifstream cloud_id_file("/run/cloud-init/cloud-id");
    CloudID ret = NONE;
    if (cloud_id_file.is_open()) {
        std::string cloud_id_str((std::istreambuf_iterator<char>(cloud_id_file)), (std::istreambuf_iterator<char>()));
        if (cloud_id_str.find("aws") == 0) {
            ret = AWS;
        } else if (cloud_id_str.find("azure") == 0) {
            ret = AZURE;
        } else if (cloud_id_str.find("gce") == 0) {
            ret = GCE;
        }
        cloud_id_file.close();
    }
    return ret;
}

enum ESMInfraSeries {NOT_ESM_INFRA, XENIAL, BIONIC};

ESMInfraSeries get_esm_infra_series() {
    std::ifstream os_release_file("/etc/os-release");
    ESMInfraSeries ret = NOT_ESM_INFRA;
    if (os_release_file.is_open()) {
        std::string os_release_str((std::istreambuf_iterator<char>(os_release_file)), (std::istreambuf_iterator<char>()));
        if (os_release_str.find("xenial") != os_release_str.npos) {
            ret = XENIAL;
        } else if (os_release_str.find("bionic") != os_release_str.npos) {
            ret = BIONIC;
        }
        os_release_file.close();
    }
    return ret;
}

struct ESMContext {
    std::string context;
    std::string url;
};

ESMContext get_esm_context() {
    CloudID cloud_id = get_cloud_id();
    ESMInfraSeries esm_infra_series = get_esm_infra_series();

    ESMContext ret;
    ret.context = "";
    ret.url = "https://ubuntu.com/pro";

    if (esm_infra_series == XENIAL) {
        if (cloud_id == AZURE) {
            ret.context = " for 16.04 on Azure";
            ret.url = "https://ubuntu.com/16-04/azure";
        } else {
            ret.context = " for 16.04";
            ret.url = "https://ubuntu.com/16-04";
        }
    } else if (esm_infra_series == BIONIC) {
        if (cloud_id == AZURE) {
            ret.context = " for 18.04 on Azure";
            ret.url = "https://ubuntu.com/18-04/azure";
        } else {
            ret.context = " for 18.04";
            ret.url = "https://ubuntu.com/18-04";
        }
    } else {
        if (cloud_id == AZURE) {
            ret.context = " on Azure";
            ret.url = "https://ubuntu.com/azure/pro";
        } else if (cloud_id == AWS) {
            ret.context = " on AWS";
            ret.url = "https://ubuntu.com/aws/pro";
        } else if (cloud_id == GCE) {
            ret.context = " on GCP";
            ret.url = "https://ubuntu.com/gcp/pro";
        }
    }

    return ret;
}

void print_esm_packages(ESMType esm_type, std::vector<std::string> package_names, ESMContext &esm_context) {

    if (esm_type == APPS) {
        std::cout << "Get more security updates through Ubuntu Pro with 'esm-apps' enabled:";
    } else {
        std::cout << "The following security updates require Ubuntu Pro with 'esm-infra' enabled:";
    }

    std::cout << std::endl;

    std::string curr_line = " ";
    for (std::string &name : package_names) {
        if ((curr_line.length() + 1 + name.length()) >= 79) {
            std::cout << curr_line << std::endl;
            curr_line = " ";
        }
        curr_line = curr_line + " " + name;
    }
    if (curr_line.length() > 1) {
        std::cout << curr_line << std::endl;
    }

    std::cout << "Learn more about Ubuntu Pro" << esm_context.context << " at " << esm_context.url << std::endl;
}

int run()
{
    char *fd_c_str = getenv("APT_HOOK_SOCKET");
    if (fd_c_str == NULL) {
        std::cerr << "pro-hook: missing socket fd" << std::endl;
        return 0;
    }
    std::string fd_str(fd_c_str);
    if (fd_str == "") {
        std::cerr << "pro-hook: empty socket fd" << std::endl;
        return 0;
    }
    int fd = stoi(fd_str);
    __gnu_cxx::stdio_filebuf<char> apt_socket_in(fd, std::ios::in);
    __gnu_cxx::stdio_filebuf<char> apt_socket_out(fd, std::ios::out);
    std::istream socket_in(&apt_socket_in);
    std::ostream socket_out(&apt_socket_out);

    bool success = false;

    // Read hello message, verify version, and get jsonrpc id
    jsonrpc_request hello_req;
    success = read_jsonrpc_request(socket_in, hello_req);
    if (!success) {
        std::cerr << "pro-hook: failed to read hello msg" << std::endl;
        return 0;
    }
    if (hello_req.method != "org.debian.apt.hooks.hello" || hello_req.notification) {
        std::cerr << "pro-hook: invalid hello msg" << std::endl;
        return 0;
    }

    json_object *hello_req_versions;
    success = json_object_object_get_ex(hello_req.params, "versions", &hello_req_versions);
    if (!success) {
        std::cerr << "pro-hook: hello msg missing versions" << std::endl;
        return 0;
    }
    int64_t hello_req_versions_length = json_object_array_length(hello_req_versions);

    bool supports_version_02 = false;
    for (int64_t i = 0; i < hello_req_versions_length; i++) {
        std::string version(json_object_get_string(json_object_array_get_idx(hello_req_versions, i)));
        if (version == "0.2") {
            supports_version_02 = true;
            break;
        }
    }
    if (!supports_version_02) {
        std::cerr << "pro-hook: apt doesn't support json hook version 0.2" << std::endl;
        return 0;
    }

    // Write hello response with jsonrpc id
    socket_out << "{\"jsonrpc\":\"2.0\",\"id\":" << hello_req.id << ",\"result\":{\"version\":\"0.2\"}}\n\n";
    socket_out.flush();

    json_object_put(hello_req.root_msg);

    jsonrpc_request hook_req;
    success = read_jsonrpc_request(socket_in, hook_req);
    if (!success) {
        std::cerr << "pro-hook: failed to read hook msg" << std::endl;
        return 0;
    }
    if (hook_req.method == "org.debian.apt.hooks.install.statistics") {
        security_package_counts counts;
        success = count_security_packages_from_apt_stats_json(hook_req.params, counts);
        if (success) {
            std::string message = create_count_message(counts);
            if (message != "") {
                std::cout << message << std::endl;
            }
        }
    } else if (hook_req.method == "org.debian.apt.hooks.install.pre-prompt") {
        // ESM stats
        ESMUpdates esm_updates;
        bool success = get_potential_esm_updates(esm_updates);
        if (success) {
            ESMContext esm_context = get_esm_context();
            if (!esm_updates.infra_packages.empty()) {
                print_esm_packages(INFRA, esm_updates.infra_packages, esm_context);
            } else if (!esm_updates.apps_packages.empty()) {
                print_esm_packages(APPS, esm_updates.apps_packages, esm_context);
            }
        }

        // APT News
        std::ifstream apt_news_file("/var/lib/ubuntu-advantage/messages/apt-news");
        if (apt_news_file.is_open()) {
            std::cout << apt_news_file.rdbuf();
            apt_news_file.close();
        }
    }
    json_object_put(hook_req.root_msg);

    jsonrpc_request bye_req;
    success = read_jsonrpc_request(socket_in, bye_req);
    if (!success) {
        std::cerr << "pro-hook: failed to read bye msg" << std::endl;
        return 0;
    }
    json_object_put(bye_req.root_msg);

    return 0;
}