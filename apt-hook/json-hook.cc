#include <ext/stdio_filebuf.h>
#include <fstream>
#include <iostream>
#include <json-c/json.h>
#include <libintl.h>
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

bool version_from_origin(json_object *version, std::string from_origin) {
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

        if (origin_origin == from_origin) {
            return true;
        }
    }

    return false;
}

bool collect_pro_packages_from_pre_prompt_json(json_object *pre_prompt, std::vector<std::string> *expired_packages) {
    bool has_key = false;

    json_object *packages;
    has_key = json_object_object_get_ex(pre_prompt, "packages", &packages);
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
        
        has_key = json_object_object_get_ex(package, "name", &tmp);
        if (!has_key) {
            continue;
        }
        std::string package_name(json_object_get_string(tmp));

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

            if (
                version_from_origin(install, "UbuntuESM")
                || version_from_origin(install, "UbuntuESMApps")
                || version_from_origin(install, "UbuntuCC")
                || version_from_origin(install, "UbuntuCIS")
                || version_from_origin(install, "UbuntuFIPS")
                || version_from_origin(install, "UbuntuFIPSUpdates")
                || version_from_origin(install, "UbuntuFIPSPreview")
                || version_from_origin(install, "UbuntuRealtimeKernel")
                || version_from_origin(install, "UbuntuROS")
                || version_from_origin(install, "UbuntuROSUpdates")
            ) {
                expired_packages->push_back(package_name);
            }
        }
    }

    return true;
}

#define MAX_COUNT_MESSAGE_LEN 256
std::string create_count_message(security_package_counts &counts) {
    char buf[MAX_COUNT_MESSAGE_LEN] = {0};

    if (counts.esm_apps == 0) {
        if (counts.esm_infra == 0) {
            if (counts.standard == 0) {
                return "";
            } else if (counts.standard == 1) {
                return std::string(gettext("1 standard LTS security update"));
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates"),
                    counts.standard
                );
                return std::string(buf);
            }
        } else if (counts.esm_infra == 1) {
            if (counts.standard == 0) {
                return std::string(gettext("1 esm-infra security update"));
            } else if (counts.standard == 1) {
                return std::string(gettext("1 standard LTS security update and 1 esm-infra security update"));
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates and 1 esm-infra security update"),
                    counts.standard
                );
                return std::string(buf);
            }
        } else if (counts.esm_infra > 1) {
            if (counts.standard == 0) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu esm-infra security updates"),
                    counts.esm_infra
                );
                return std::string(buf);
            } else if (counts.standard == 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("1 standard LTS security update and %lu esm-infra security updates"),
                    counts.esm_infra
                );
                return std::string(buf);
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates and %lu esm-infra security updates"),
                    counts.standard,
                    counts.esm_infra
                );
                return std::string(buf);
            }
        }
    } else if (counts.esm_apps == 1) {
        if (counts.esm_infra == 0) {
            if (counts.standard == 0) {
                return std::string(gettext("1 esm-apps security update"));
            } else if (counts.standard == 1) {
                return std::string(gettext("1 standard LTS security update and 1 esm-apps security update"));
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates and 1 esm-apps security update"),
                    counts.standard
                );
                return std::string(buf);
            }
        } else if (counts.esm_infra == 1) {
            if (counts.standard == 0) {
                return std::string(gettext("1 esm-infra security update and 1 esm-apps security update"));
            } else if (counts.standard == 1) {
                return std::string(gettext("1 standard LTS security update, 1 esm-infra security update and 1 esm-apps security update"));
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates, 1 esm-infra security update and 1 esm-apps security update"),
                    counts.standard
                );
                return std::string(buf);
            }
        } else if (counts.esm_infra > 1) {
            if (counts.standard == 0) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu esm-infra security updates and 1 esm-apps security update"),
                    counts.esm_infra
                );
                return std::string(buf);
            } else if (counts.standard == 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("1 standard LTS security update, %lu esm-infra security updates and 1 esm-apps security update"),
                    counts.esm_infra
                );
                return std::string(buf);
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates, %lu esm-infra security updates and 1 esm-apps security update"),
                    counts.standard,
                    counts.esm_infra
                );
                return std::string(buf);
            }
        }
    } else if (counts.esm_apps > 1) {
        if (counts.esm_infra == 0) {
            if (counts.standard == 0) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu esm-apps security updates"),
                    counts.esm_apps
                );
                return std::string(buf);
            } else if (counts.standard == 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("1 standard LTS security update and %lu esm-apps security updates"),
                    counts.esm_apps
                );
                return std::string(buf);
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates and %lu esm-apps security updates"),
                    counts.standard,
                    counts.esm_apps
                );
                return std::string(buf);
            }
        } else if (counts.esm_infra == 1) {
            if (counts.standard == 0) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("1 esm-infra security update and %lu esm-apps security updates"),
                    counts.esm_apps
                );
                return std::string(buf);
            } else if (counts.standard == 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("1 standard LTS security update, 1 esm-infra security update and %lu esm-apps security updates"),
                    counts.esm_apps
                );
                return std::string(buf);
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates, 1 esm-infra security update and %lu esm-apps security updates"),
                    counts.standard,
                    counts.esm_apps
                );
                return std::string(buf);
            }
        } else if (counts.esm_infra > 1) {
            if (counts.standard == 0) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu esm-infra security updates and %lu esm-apps security updates"),
                    counts.esm_infra,
                    counts.esm_apps
                );
                return std::string(buf);
            } else if (counts.standard == 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("1 standard LTS security update, %lu esm-infra security updates and %lu esm-apps security updates"),
                    counts.esm_infra,
                    counts.esm_apps
                );
                return std::string(buf);
            } else if (counts.standard > 1) {
                std::snprintf(
                    buf,
                    MAX_COUNT_MESSAGE_LEN,
                    gettext("%lu standard LTS security updates, %lu esm-infra security updates and %lu esm-apps security updates"),
                    counts.standard,
                    counts.esm_infra,
                    counts.esm_apps
                );
                return std::string(buf);
            }
        }
    }

    return "";
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

void print_learn_more_with_context() {
    CloudID cloud_id = get_cloud_id();
    ESMInfraSeries esm_infra_series = get_esm_infra_series();

    if (esm_infra_series == XENIAL) {
        if (cloud_id == AZURE) {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro for 16.04 on Azure at %s"
                ),
                "https://ubuntu.com/16-04/azure"
            );
            printf("\n");
            return;
        } else {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro for 16.04 at %s"
                ),
                "https://ubuntu.com/16-04"
            );
            printf("\n");
            return;
        }
    } else if (esm_infra_series == BIONIC) {
        if (cloud_id == AZURE) {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro for 18.04 on Azure at %s"
                ),
                "https://ubuntu.com/18-04/azure"
            );
            printf("\n");
            return;
        } else {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro for 18.04 at %s"
                ),
                "https://ubuntu.com/18-04"
            );
            printf("\n");
            return;
        }
    } else {
        if (cloud_id == AZURE) {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro on Azure at %s"
                ),
                "https://ubuntu.com/azure/pro"
            );
            printf("\n");
            return;
        } else if (cloud_id == AWS) {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro on AWS at %s"
                ),
                "https://ubuntu.com/aws/pro"
            );
            printf("\n");
            return;
        } else if (cloud_id == GCE) {
            printf(
                gettext(
                    "Learn more about Ubuntu Pro on GCP at %s"
                ),
                "https://ubuntu.com/gcp/pro"
            );
            printf("\n");
            return;
        }
    }

    printf(
        gettext(
            "Learn more about Ubuntu Pro at %s"
        ),
        "https://ubuntu.com/pro"
    );
    printf("\n");
    return;
}

void print_package_names(std::vector<std::string> package_names) {
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
}

void print_esm_packages(ESMType esm_type, std::vector<std::string> package_names) {
    if (esm_type == APPS) {
        printf(
            ngettext(
                "Get another security update through Ubuntu Pro with 'esm-apps' enabled:",
                "Get more security updates through Ubuntu Pro with 'esm-apps' enabled:",
                package_names.size()
            )
        );
        printf("\n");
    } else {
        printf(
            ngettext(
                "The following security update requires Ubuntu Pro with 'esm-infra' enabled:",
                "The following security updates require Ubuntu Pro with 'esm-infra' enabled:",
                package_names.size()
            )
        );
        printf("\n");
    }

    print_package_names(package_names);

    print_learn_more_with_context();
}

void print_expired_pro_packages(std::vector<std::string> package_names) {
    printf(
        gettext(
            "The following packages will fail to download because your Ubuntu Pro subscription has expired"
        )
    );
    printf("\n");

    print_package_names(package_names);

    printf(
        gettext(
            "Renew your subscription or `sudo pro detach` to remove these errors"
        )
    );
    printf("\n");
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
            if (!esm_updates.infra_packages.empty()) {
                print_esm_packages(INFRA, esm_updates.infra_packages);
            } else if (!esm_updates.apps_packages.empty()) {
                print_esm_packages(APPS, esm_updates.apps_packages);
            }
        }

        // APT News
        std::ifstream apt_news_file("/var/lib/ubuntu-advantage/messages/apt-news");
        if (apt_news_file.is_open()) {
            std::cout << apt_news_file.rdbuf();
            apt_news_file.close();
        }

        // Expired explanation
        std::ifstream expired_notice("/var/lib/ubuntu-advantage/notices/5-contract_expired");
        if (expired_notice.is_open()) {
            std::vector<std::string> expired_packages;
            bool success = collect_pro_packages_from_pre_prompt_json(hook_req.params, &expired_packages);
            if (success && expired_packages.size() > 0) {
                print_expired_pro_packages(expired_packages);
            }
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
