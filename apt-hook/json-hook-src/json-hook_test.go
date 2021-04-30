package main

import (
	"encoding/json"
	"fmt"
	"testing"
)

func TestCreateUpdateMessages(t *testing.T) {
	type params struct {
		standardSecurityCount int
		esmInfraCount         int
		esmAppsCount          int
		expectedMessage       string
	}
	testParamsList := []params{
		{0, 0, 0, ""},
		{0, 0, 1, "1 esm-apps security update"},
		{0, 0, 2, "2 esm-apps security updates"},
		{0, 1, 0, "1 esm-infra security update"},
		{0, 1, 1, "1 esm-infra security update and 1 esm-apps update"},
		{0, 1, 2, "1 esm-infra security update and 2 esm-apps updates"},
		{0, 2, 0, "2 esm-infra security updates"},
		{0, 2, 1, "2 esm-infra security updates and 1 esm-apps update"},
		{0, 2, 2, "2 esm-infra security updates and 2 esm-apps updates"},
		{1, 0, 0, "1 standard security update"},
		{1, 0, 1, "1 standard security update and 1 esm-apps update"},
		{1, 0, 2, "1 standard security update and 2 esm-apps updates"},
		{1, 1, 0, "1 standard security update and 1 esm-infra update"},
		{1, 1, 1, "1 standard security update, 1 esm-infra update and 1 esm-apps update"},
		{1, 1, 2, "1 standard security update, 1 esm-infra update and 2 esm-apps updates"},
		{1, 2, 0, "1 standard security update and 2 esm-infra updates"},
		{1, 2, 1, "1 standard security update, 2 esm-infra updates and 1 esm-apps update"},
		{1, 2, 2, "1 standard security update, 2 esm-infra updates and 2 esm-apps updates"},
		{2, 0, 0, "2 standard security updates"},
		{2, 0, 1, "2 standard security updates and 1 esm-apps update"},
		{2, 0, 2, "2 standard security updates and 2 esm-apps updates"},
		{2, 1, 0, "2 standard security updates and 1 esm-infra update"},
		{2, 1, 1, "2 standard security updates, 1 esm-infra update and 1 esm-apps update"},
		{2, 1, 2, "2 standard security updates, 1 esm-infra update and 2 esm-apps updates"},
		{2, 2, 0, "2 standard security updates and 2 esm-infra updates"},
		{2, 2, 1, "2 standard security updates, 2 esm-infra updates and 1 esm-apps update"},
		{2, 2, 2, "2 standard security updates, 2 esm-infra updates and 2 esm-apps updates"},
	}

	for i, testParams := range testParamsList {
		t.Run(fmt.Sprintf("Case %d", i), func(t *testing.T) {
			actual := createUpdateMessage(testParams.standardSecurityCount, testParams.esmInfraCount, testParams.esmAppsCount)
			if actual != testParams.expectedMessage {
				t.Logf("expected: \"%s\", got: \"%s\"", testParams.expectedMessage, actual)
				t.Fail()
			}
		})
	}
}

func TestCountSecurityUpdates(t *testing.T) {
	type params struct {
		rpc                           string
		expectedStandardSecurityCount int
		expectedEsmInfraCount         int
		expectedEsmAppsCount          int
	}
	testParamsList := []params{
		{mockJson, 1, 2, 3},
	}

	for i, testParams := range testParamsList {
		t.Run(fmt.Sprintf("Case %d", i), func(t *testing.T) {
			rpc := &jsonRPC{}
			if err := json.Unmarshal([]byte(mockJson), rpc); err != nil {
				t.Error(err)
			}

			actualStandard, actualInfra, actualApps := countSecurityUpdates(rpc)
			if actualStandard != testParams.expectedStandardSecurityCount {
				t.Logf("expected: %d, got: %d", testParams.expectedStandardSecurityCount, actualStandard)
				t.Fail()
			}
			if actualInfra != testParams.expectedEsmInfraCount {
				t.Logf("expected: %d, got: %d", testParams.expectedEsmInfraCount, actualInfra)
				t.Fail()
			}
			if actualApps != testParams.expectedEsmAppsCount {
				t.Logf("expected: %d, got: %d", testParams.expectedEsmAppsCount, actualApps)
				t.Fail()
			}
		})
	}
}

const mockJson = `
{
    "jsonrpc": "2.0",
    "method": "org.debian.apt.hooks.install.statistics",
    "params": {
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
                                "archive": "hirsute-apps-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-apps-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-apps-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-apps-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-infra-security",
                                "codename": "hirsute",
                                "version": "21.04",
                                "origin": "UbuntuESM",
                                "label": "Ubuntu",
                                "site": ""
                            },
                            {
                                "archive": "hirsute",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-infra-security",
                                "codename": "hirsute",
                                "version": "21.04",
                                "origin": "UbuntuESM",
                                "label": "Ubuntu",
                                "site": ""
                            },
                            {
                                "archive": "hirsute",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-infra-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-infra-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-apps-security",
                                "codename": "hirsute",
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
                                "archive": "hirsute-apps-security",
                                "codename": "hirsute",
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
                                "archive": "hirsute-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
                                "archive": "hirsute-security",
                                "codename": "hirsute",
                                "version": "21.04",
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
}
`
