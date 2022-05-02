#define BOOST_TEST_DYN_LINK
#define BOOST_TEST_MODULE Main
#include <boost/test/unit_test.hpp>

#include "json-hook.hh"

BOOST_AUTO_TEST_SUITE(JSON_Hook)

BOOST_AUTO_TEST_SUITE(Count_Message)

void count_message_test(int standard_count, int infra_count, int apps_count, std::string expected_message) {
    security_package_counts counts;
    counts.standard = standard_count;
    counts.esm_infra = infra_count;
    counts.esm_apps = apps_count;
    std::string message = create_count_message(counts);
    BOOST_CHECK(message == expected_message);
}

BOOST_AUTO_TEST_CASE(Test1) { count_message_test(0, 0, 0, ""); }
BOOST_AUTO_TEST_CASE(Test2) { count_message_test(0, 0, 1, "1 esm-apps security update"); }
BOOST_AUTO_TEST_CASE(Test3) { count_message_test(0, 0, 2, "2 esm-apps security updates"); }
BOOST_AUTO_TEST_CASE(Test4) { count_message_test(0, 1, 0, "1 esm-infra security update"); }
BOOST_AUTO_TEST_CASE(Test5) { count_message_test(0, 1, 1, "1 esm-infra security update and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test6) { count_message_test(0, 1, 2, "1 esm-infra security update and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test7) { count_message_test(0, 2, 0, "2 esm-infra security updates"); }
BOOST_AUTO_TEST_CASE(Test8) { count_message_test(0, 2, 1, "2 esm-infra security updates and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test9) { count_message_test(0, 2, 2, "2 esm-infra security updates and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test10) { count_message_test(1, 0, 0, "1 standard security update"); }
BOOST_AUTO_TEST_CASE(Test11) { count_message_test(1, 0, 1, "1 standard security update and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test12) { count_message_test(1, 0, 2, "1 standard security update and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test13) { count_message_test(1, 1, 0, "1 standard security update and 1 esm-infra update"); }
BOOST_AUTO_TEST_CASE(Test14) { count_message_test(1, 1, 1, "1 standard security update, 1 esm-infra update and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test15) { count_message_test(1, 1, 2, "1 standard security update, 1 esm-infra update and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test16) { count_message_test(1, 2, 0, "1 standard security update and 2 esm-infra updates"); }
BOOST_AUTO_TEST_CASE(Test17) { count_message_test(1, 2, 1, "1 standard security update, 2 esm-infra updates and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test18) { count_message_test(1, 2, 2, "1 standard security update, 2 esm-infra updates and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test19) { count_message_test(2, 0, 0, "2 standard security updates"); }
BOOST_AUTO_TEST_CASE(Test20) { count_message_test(2, 0, 1, "2 standard security updates and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test21) { count_message_test(2, 0, 2, "2 standard security updates and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test22) { count_message_test(2, 1, 0, "2 standard security updates and 1 esm-infra update"); }
BOOST_AUTO_TEST_CASE(Test23) { count_message_test(2, 1, 1, "2 standard security updates, 1 esm-infra update and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test24) { count_message_test(2, 1, 2, "2 standard security updates, 1 esm-infra update and 2 esm-apps updates"); }
BOOST_AUTO_TEST_CASE(Test25) { count_message_test(2, 2, 0, "2 standard security updates and 2 esm-infra updates"); }
BOOST_AUTO_TEST_CASE(Test26) { count_message_test(2, 2, 1, "2 standard security updates, 2 esm-infra updates and 1 esm-apps update"); }
BOOST_AUTO_TEST_CASE(Test27) { count_message_test(2, 2, 2, "2 standard security updates, 2 esm-infra updates and 2 esm-apps updates"); }

BOOST_AUTO_TEST_SUITE_END()

BOOST_AUTO_TEST_SUITE(Count_Security_Updates)

std::string test_json = R"(
    {
        "command": "install",
        "search-terms": [
            "~U"
        ],
        "unknown-packages": [],
        "packages": [
            {
                "id": 418,
                "name": "base-files",
                "architecture": "amd64",
                "mode": "upgrade",
                "automatic": true,
                "versions": {
                    "candidate": {
                        "id": 86,
                        "version": "11ubuntu19",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-apps-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESMApps",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "install": {
                        "id": 86,
                        "version": "11ubuntu19",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-apps-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESMApps",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "current": {
                        "id": 95463,
                        "version": "11ubuntu18",
                        "architecture": "amd64",
                        "pin": 100,
                        "origins": []
                    }
                }
            },
            {
                "id": 1085,
                "name": "elfutils",
                "architecture": "amd64",
                "mode": "upgrade",
                "automatic": true,
                "versions": {
                    "candidate": {
                        "id": 371,
                        "version": "0.183-8",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-apps-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESMApps",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "install": {
                        "id": 371,
                        "version": "0.183-8",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-apps-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESMApps",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "current": {
                        "id": 95472,
                        "version": "0.183-6",
                        "architecture": "amd64",
                        "pin": 100,
                        "origins": []
                    }
                }
            },
            {
                "id": 24709,
                "name": "fdroidserver",
                "architecture": "amd64",
                "mode": "upgrade",
                "automatic": false,
                "versions": {
                    "candidate": {
                        "id": 14186,
                        "version": "2.0-1",
                        "architecture": "all",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-infra-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESM",
                                "label": "Ubuntu",
                                "site": ""
                            },
                            {
                                "archive": "focal",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "Ubuntu",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "install": {
                        "id": 14186,
                        "version": "2.0-1",
                        "architecture": "all",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-infra-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESM",
                                "label": "Ubuntu",
                                "site": ""
                            },
                            {
                                "archive": "focal",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "Ubuntu",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "current": {
                        "id": 95474,
                        "version": "1.1.9-1",
                        "architecture": "all",
                        "pin": 100,
                        "origins": []
                    }
                }
            },
            {
                "id": 238,
                "name": "gdb",
                "architecture": "amd64",
                "mode": "upgrade",
                "automatic": true,
                "versions": {
                    "candidate": {
                        "id": 705,
                        "version": "10.1-2ubuntu2",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-infra-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESM",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "install": {
                        "id": 705,
                        "version": "10.1-2ubuntu2",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-infra-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "UbuntuESM",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "current": {
                        "id": 95475,
                        "version": "10.1-2ubuntu1",
                        "architecture": "amd64",
                        "pin": 100,
                        "origins": []
                    }
                }
            },
            {
                "id": 126271,
                "name": "google-chrome-stable",
                "architecture": "amd64",
                "mode": "upgrade",
                "automatic": true,
                "versions": {
                    "candidate": {
                        "id": 95416,
                        "version": "90.0.4430.85-1",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-apps-security",
                                "codename": "focal",
                                "version": "1.0",
                                "origin": "UbuntuESMApps",
                                "label": "Google",
                                "site": "dl.google.com"
                            }
                        ]
                    },
                    "install": {
                        "id": 95416,
                        "version": "90.0.4430.85-1",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-apps-security",
                                "codename": "focal",
                                "version": "1.0",
                                "origin": "UbuntuESMApps",
                                "label": "Google",
                                "site": "dl.google.com"
                            }
                        ]
                    },
                    "current": {
                        "id": 95477,
                        "version": "90.0.4430.72-1",
                        "architecture": "amd64",
                        "pin": 100,
                        "origins": []
                    }
                }
            },
            {
                "id": 1499,
                "name": "libasm1",
                "architecture": "amd64",
                "mode": "upgrade",
                "automatic": true,
                "versions": {
                    "candidate": {
                        "id": 1763,
                        "version": "0.183-8",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "Ubuntu",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "install": {
                        "id": 1763,
                        "version": "0.183-8",
                        "architecture": "amd64",
                        "pin": 500,
                        "origins": [
                            {
                                "archive": "focal-security",
                                "codename": "focal",
                                "version": "20.04",
                                "origin": "Ubuntu",
                                "label": "Ubuntu",
                                "site": ""
                            }
                        ]
                    },
                    "current": {
                        "id": 95482,
                        "version": "0.183-6",
                        "architecture": "amd64",
                        "pin": 100,
                        "origins": []
                    }
                }
            }
        ]
    }
)";

BOOST_AUTO_TEST_CASE(Test1) {
    security_package_counts counts;
    json_object *stats = json_tokener_parse(test_json.c_str());
    count_security_packages_from_apt_stats_json(stats, counts);
    BOOST_CHECK(counts.standard == 1);
    BOOST_CHECK(counts.esm_infra == 2);
    BOOST_CHECK(counts.esm_apps == 3);
}

BOOST_AUTO_TEST_SUITE_END()

BOOST_AUTO_TEST_SUITE_END()
