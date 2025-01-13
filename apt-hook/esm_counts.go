package main

import (
	"fmt"
	"path/filepath"
	"strings"
	"bufio"
	"os"
	"os/exec"
)

const (
	systemPkgPath = "/var/lib/dpkg/status"
)

type PkgStatus struct {
	Name	string
	Version string
	Status  string
	Source  string
}

type ESMUpdates struct {
	InfraPackages []string
	AppsPackages  []string
}

func getDpkgArch() string {
	cmd := exec.Command("dpkg", "--print-architecture")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	arch := strings.TrimSpace(string(out))
	return arch
}

func getESMPackagesFilePath(series string, esmType string) (string, string) {
    arch := getDpkgArch()

    const baseDir = "/var/lib/ubuntu-advantage/apt-esm/var/lib/apt/lists"

    security := filepath.Join(baseDir,
        fmt.Sprintf("esm.ubuntu.com_%s_ubuntu_dists_%s-%s-security_main_binary-%s_Packages",
            esmType, series, esmType, arch))

    updates := filepath.Join(baseDir,
        fmt.Sprintf("esm.ubuntu.com_%s_ubuntu_dists_%s-%s-updates_main_binary-%s_Packages",
            esmType, series, esmType, arch))

    return security, updates
}

func getESMPackages(osRelease OSRelease, esmType string) ([]PkgStatus, error) {
    securityPath, updatesPath := getESMPackagesFilePath(osRelease.VersionCodename, esmType)

    securityPkgs, err := readPackages(securityPath)
    if err != nil {
        return nil, fmt.Errorf("reading security packages: %w", err)
    }

    updatesPkgs, err := readPackages(updatesPath)
    if err != nil {
        return nil, fmt.Errorf("reading updates packages: %w", err)
    }

    pkgMap := make(map[string]PkgStatus)
    for _, pkg := range securityPkgs {
        pkgMap[pkg.Name] = pkg
    }
    for _, pkg := range updatesPkgs {
        pkgMap[pkg.Name] = pkg
    }

    allPackages := make([]PkgStatus, 0, len(pkgMap))
    for _, pkg := range pkgMap {
        allPackages = append(allPackages, pkg)
    }
    return allPackages, nil
}


func readPackages(filepath string) ([]PkgStatus, error) {
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		return []PkgStatus{}, nil
	}
	file, err := os.Open(filepath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var packages []PkgStatus
	var curPackage PkgStatus

	scanner := bufio.NewScanner(file)
	parsingPackage := false

	for scanner.Scan(){
		line := strings.TrimSpace(scanner.Text())

		if strings.HasPrefix(line, "Package:") {
			if parsingPackage {
				packages = append(packages, curPackage)
			}

			curPackage = PkgStatus{}
			curPackage.Name = strings.TrimSpace(strings.TrimPrefix(line, "Package:"))
			parsingPackage = true
		} else if strings.HasPrefix(line, "Version:") {
			curPackage.Version = strings.TrimSpace(strings.TrimPrefix(line, "Version:"))
		} else if strings.HasPrefix(line, "Status:") {
			curPackage.Status = strings.TrimSpace(strings.TrimPrefix(line, "Status:"))
		} else if strings.HasPrefix(line, "Source:") {
			curPackage.Source = strings.TrimSpace(strings.TrimPrefix(line, "Source:"))
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	if parsingPackage {
		packages = append(packages, curPackage)
	}

	return packages, nil
}

// GetPotentialESMUpdates returns a list of packages that are available for
// updates from ESM Apps and Infra
func GetPotentialESMUpdates() (*ESMUpdates, error) {
	updates := &ESMUpdates{}

	systemPkgs, err := readPackages(systemPkgPath)
	if err != nil {
		return nil, fmt.Errorf("reading system packages: %w", err)
	}

	osRelease := ParseOSRelease()
	esmAppsPackages, err := getESMPackages(osRelease, "apps")
	if err != nil {
		return nil, fmt.Errorf("reading esm apps packages: %w", err)
	}
	esmInfraPackages, err := getESMPackages(osRelease, "infra")
	if err != nil {
		return nil, fmt.Errorf("reading esm infra packages: %w", err)
	}

	for _, sysPkg := range systemPkgs {
		// If installed
		if !strings.Contains(sysPkg.Status, "installed") {
			continue
		}

		for _, esmPkg := range esmAppsPackages {
			if esmPkg.Name == sysPkg.Name && CompareVersions(esmPkg.Version, sysPkg.Version) > 0 {
				updates.AppsPackages = append(updates.AppsPackages, esmPkg.Name)
			}
		}

		for _, infraPkg := range esmInfraPackages {
			if infraPkg.Name == sysPkg.Name && CompareVersions(infraPkg.Version, sysPkg.Version) > 0 {
				updates.InfraPackages = append(updates.InfraPackages, infraPkg.Name)
			}
		}
	}

	return updates, nil
}
