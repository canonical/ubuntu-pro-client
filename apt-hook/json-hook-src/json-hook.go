package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"strconv"
)

type jsonRPCPackageVersion struct {
	Id           int    `json:"id"`
	Version      string `json:"version"`
	Architecture string `json:"architecture"`
	Pin          int    `json:"pin"`
	Origins      []struct {
		Archive  string `json:"archive"`
		Codename string `json:"codename"`
		Version  string `json:"version"`
		Origin   string `json:"origin"`
		Label    string `json:"label"`
		Site     string `json:"site"`
	} `json:"origins"`
}
type jsonRPC struct {
	JsonRPC string `json:"jsonrpc"`
	Method  string `json:"method"`
	Params  struct {
		Command         string   `json:"command"`
		UnknownPackages []string `json:"unknown-packages"`
		Packages        []struct {
			Id           int    `json:"id"`
			Name         string `json:"name"`
			Architecture string `json:"architecture"`
			Mode         string `json:"mode"`
			Automatic    bool   `json:"automatic"`
			Versions     struct {
				Candidate jsonRPCPackageVersion `json:"candidate"`
				Install   jsonRPCPackageVersion `json:"install"`
				Current   jsonRPCPackageVersion `json:"current"`
			} `json:"versions"`
		} `json:"packages"`
	} `json:"params"`
}

func updatesFromSource(count int, source string, first bool) string {
	security := ""
	if first {
		security = "security "
	}
	updates := "updates"
	if count == 1 {
		updates = "update"
	}
	return fmt.Sprintf("%d %s %s%s", count, source, security, updates)
}

func createUpdateMessage(standardSecurityCount int, esmInfraCount int, esmAppsCount int) string {
	displayStandard := true
	displayEsmInfra := true
	displayEsmApps := true
	if standardSecurityCount == 0 {
		displayStandard = false
	}
	if esmInfraCount == 0 {
		displayEsmInfra = false
	}
	if esmAppsCount == 0 {
		displayEsmApps = false
	}

	if !displayStandard && !displayEsmInfra && !displayEsmApps {
		return ""
	}

	esmInfraFirst := false
	esmAppsFirst := false
	if !displayStandard && displayEsmInfra {
		esmInfraFirst = true
	} else if !displayStandard && !displayEsmInfra && displayEsmApps {
		esmAppsFirst = true
	}

	standardUpdates := ""
	afterStandard := ""
	esmInfraUpdates := ""
	afterInfra := ""
	esmAppsUpdates := ""

	if displayStandard {
		standardUpdates = updatesFromSource(standardSecurityCount, "standard", true)
		if displayEsmInfra && displayEsmApps {
			afterStandard = ", "
		} else if displayEsmInfra || displayEsmApps {
			afterStandard = " and "
		}
	}
	if displayEsmInfra {
		esmInfraUpdates = updatesFromSource(esmInfraCount, "esm-infra", esmInfraFirst)
		if displayEsmApps {
			afterInfra = " and "
		}
	}
	if displayEsmApps {
		esmAppsUpdates = updatesFromSource(esmAppsCount, "esm-apps", esmAppsFirst)
	}

	return standardUpdates + afterStandard + esmInfraUpdates + afterInfra + esmAppsUpdates
}

func fromOriginAndArchive(pkgVersion jsonRPCPackageVersion, origin string, archive string) bool {
	for _, pkgOrigin := range pkgVersion.Origins {
		if pkgOrigin.Origin == origin && pkgOrigin.Archive == archive {
			return true
		}
	}
	return false
}

func distroFromPackageOrigin(rpc *jsonRPC) string {
	for _, pkg := range rpc.Params.Packages {
		for _, origin := range pkg.Versions.Candidate.Origins {
			if origin.Codename != "" {
				return origin.Codename
			}
		}
	}
	return ""
}

func countSecurityUpdates(rpc *jsonRPC) (int, int, int) {
	esmAppsCount := 0
	esmInfraCount := 0
	standardSecurityCount := 0
	distro := distroFromPackageOrigin(rpc)
	for _, pkg := range rpc.Params.Packages {
		if pkg.Mode == "upgrade" {
			if fromOriginAndArchive(pkg.Versions.Install, "UbuntuESMApps", fmt.Sprintf("%s-apps-security", distro)) {
				esmAppsCount++
			} else if fromOriginAndArchive(pkg.Versions.Install, "UbuntuESM", fmt.Sprintf("%s-infra-security", distro)) {
				esmInfraCount++
			} else if fromOriginAndArchive(pkg.Versions.Install, "Ubuntu", fmt.Sprintf("%s-security", distro)) {
				standardSecurityCount++
			}
		}
	}
	return standardSecurityCount, esmInfraCount, esmAppsCount
}

// readRpc reads a apt json rpc protocol 0.2 message as described in
// https://salsa.debian.org/apt-team/apt/blob/main/doc/json-hooks-protocol.md#wire-protocol
func readRpc(r *bufio.Reader) (*jsonRPC, error) {
	line, err := r.ReadBytes('\n')
	if err != nil && err != io.EOF {
		return nil, fmt.Errorf("cannot read json-rpc: %v", err)
	}

	var rpc jsonRPC
	if err := json.Unmarshal(line, &rpc); err != nil {
		return nil, err
	}
	// empty \n
	emptyNL, _, err := r.ReadLine()
	if err != nil {
		return nil, err
	}
	if string(emptyNL) != "" {
		return nil, fmt.Errorf("unexpected line: %q (empty)", emptyNL)
	}

	return &rpc, nil
}

func printEsmUpgrades() error {
	sockFd := os.Getenv("APT_HOOK_SOCKET")
	if sockFd == "" {
		return fmt.Errorf("cannot find APT_HOOK_SOCKET env")
	}

	fd, err := strconv.Atoi(sockFd)
	if err != nil {
		return fmt.Errorf("expected APT_HOOK_SOCKET to be a decimal integer, found %q", sockFd)
	}

	f := os.NewFile(uintptr(fd), "apt-hook-socket")
	if f == nil {
		return fmt.Errorf("cannot open file descriptor %v", fd)
	}
	defer f.Close()

	conn, err := net.FileConn(f)
	if err != nil {
		return fmt.Errorf("cannot connect to %v: %v", fd, err)
	}
	defer conn.Close()

	r := bufio.NewReader(conn)

	// handshake
	rpc, err := readRpc(r)
	if err != nil {
		return err
	}
	if rpc.Method != "org.debian.apt.hooks.hello" {
		return fmt.Errorf("expected 'hello' method, got: %v", rpc.Method)
	}
	if _, err := conn.Write([]byte(`{"jsonrpc":"2.0","id":0,"result":{"version":"0.2"}}` + "\n\n")); err != nil {
		return err
	}

	// payload
	rpc, err = readRpc(r)
	if err != nil {
		return err
	}
	if rpc.Method == "org.debian.apt.hooks.install.statistics" {
		standardSecurityCount, esmInfraCount, esmAppsCount := countSecurityUpdates(rpc)
		msg := createUpdateMessage(standardSecurityCount, esmInfraCount, esmAppsCount)
		if msg != "" {
			fmt.Println(msg)
		}
	}

	// bye
	rpc, err = readRpc(r)
	if err != nil {
		return err
	}
	if rpc.Method != "org.debian.apt.hooks.bye" {
		return fmt.Errorf("expected 'bye' method, got: %v", rpc.Method)
	}

	return nil
}

func main() {
	err := printEsmUpgrades()
	if err != nil {
		println(err.Error())
	}
}
