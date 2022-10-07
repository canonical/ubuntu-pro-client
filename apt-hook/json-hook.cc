#include <ext/stdio_filebuf.h>
#include <fstream>
#include <iostream>
#include <json-c/json.h>
#include <sstream>
#include <string>
#include <vector>

#include "json-hook.hh"

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

int run()
{
    char *fd_c_str = getenv("APT_HOOK_SOCKET");
    if (fd_c_str == NULL) {
        std::cerr << "ua-hook: missing socket fd" << std::endl;
        return 0;
    }
    std::string fd_str(fd_c_str);
    if (fd_str == "") {
        std::cerr << "ua-hook: empty socket fd" << std::endl;
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
        std::cerr << "ua-hook: failed to read hello msg" << std::endl;
        return 0;
    }
    if (hello_req.method != "org.debian.apt.hooks.hello" || hello_req.notification) {
        std::cerr << "ua-hook: invalid hello msg" << std::endl;
        return 0;
    }

    json_object *hello_req_versions;
    success = json_object_object_get_ex(hello_req.params, "versions", &hello_req_versions);
    if (!success) {
        std::cerr << "ua-hook: hello msg missing versions" << std::endl;
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
        std::cerr << "ua-hook: apt doesn't support json hook version 0.2" << std::endl;
        return 0;
    }

    // Write hello response with jsonrpc id
    socket_out << "{\"jsonrpc\":\"2.0\",\"id\":" << hello_req.id << ",\"result\":{\"version\":\"0.2\"}\n\n";
    socket_out.flush();

    json_object_put(hello_req.root_msg);

    jsonrpc_request hook_req;
    success = read_jsonrpc_request(socket_in, hook_req);
    if (!success) {
        std::cerr << "ua-hook: failed to read hook msg" << std::endl;
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
    } else if (hook_req.method == "org.debian.apt.hooks.install.post") {
        std::ifstream apt_news_flag_file("/var/lib/ubuntu-advantage/flags/show-apt-news");
        if (apt_news_flag_file.is_open()) {
            std::cout << std::endl;
            std::cout << "Try Ubuntu Pro beta with a free personal subscription on up to 5 machines." << std::endl;
            std::cout << "Learn more at https://ubuntu.com/pro" << std::endl;
            apt_news_flag_file.close();
        }
    }
    json_object_put(hook_req.root_msg);

    jsonrpc_request bye_req;
    success = read_jsonrpc_request(socket_in, bye_req);
    if (!success) {
        std::cerr << "ua-hook: failed to read bye msg" << std::endl;
        return 0;
    }
    json_object_put(bye_req.root_msg);

    return 0;
}
