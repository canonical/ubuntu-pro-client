package apthook

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

func getEsmPackagesFilePath(osRelease OSRelease) (string, string) {
    curSeries := osRelease.VersionCodename
    curArch := getDpkgArch()

    const baseDir = "/var/lib/ubuntu-advantage/apt-esm/var/lib/apt/lists"

    security := filepath.Join(baseDir,
        fmt.Sprintf("esm.ubuntu.com_apps_ubuntu_dists_%s-apps-security_main_binary-%s_Packages",
            curSeries, curArch))

    updates := filepath.Join(baseDir,
        fmt.Sprintf("esm.ubuntu.com_apps_ubuntu_dists_%s-apps-updates_main_binary-%s_Packages",
            curSeries, curArch))

    return security, updates
}

func readPackages(filepath string) ([]PkgStatus, error) {
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

	// Can return a dict (map) for faster lookup instead of iterating?
	return packages, nil
}

// GetPotentialESMUpdates returns a list of packages that are available for
// updates in the ESM repo
func GetPotentialESMUpdates() (*ESMUpdates, error) {
	updates := &ESMUpdates{}

	systemPkgs, err := readPackages(systemPkgPath)
	if err != nil {
		return nil, fmt.Errorf("reading system packages: %w", err)
	}

	// Get ESM package list paths (currently only apps)
	osRelease := ParseOSRelease()
	securityPath, updatesPath := getEsmPackagesFilePath(osRelease)

	securityPkgs, err := readPackages(securityPath)
	if err != nil {
		return nil, fmt.Errorf("reading security packages: %w", err)
	}

	updatesPkgs, err := readPackages(updatesPath)
	if err != nil {
		return nil, fmt.Errorf("reading updates packages: %w", err)
	}

	for _, sysPkg := range systemPkgs {
		// If installed
		if !strings.Contains(sysPkg.Status, "installed") {
			continue
		}

		// Check security packages path
		for _, secPkg := range securityPkgs {
			if secPkg.Name == sysPkg.Name && CompareVersions(secPkg.Version, sysPkg.Version) < 0{
				// Check ESM Source
				if strings.Contains(secPkg.Source, "UbuntuESMApps") {
					updates.AppsPackages = append(updates.AppsPackages, secPkg.Name)
				} else if strings.Contains(secPkg.Source, "UbuntuESM") {
					updates.InfraPackages = append(updates.InfraPackages, secPkg.Name)
				}
			}
		}

		// Check updates packages path
		for _, updatesPkg := range updatesPkgs {
			if updatesPkg.Name == sysPkg.Name && CompareVersions(updatesPkg.Version, sysPkg.Version) < 0{
				// Check ESM Source
				if strings.Contains(updatesPkg.Source, "UbuntuESMApps") {
					updates.AppsPackages = append(updates.AppsPackages, updatesPkg.Name)
				} else if strings.Contains(updatesPkg.Source, "UbuntuESM") {
					updates.InfraPackages = append(updates.InfraPackages, updatesPkg.Name)
				}
			}
		}
	}

	return updates, nil
}
