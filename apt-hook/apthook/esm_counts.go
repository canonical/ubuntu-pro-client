package apthook

import (
	"fmt"
	"strings"
)

const (
	systemPkgStatus = "/var/lib/dpkg/status"
	esmPkgStatus	= "/var/lib/ubuntu-advantage/apt-esm/var/lib/dpkg/status"
)
// Instead of esmPkgStatus
// we need to use the following from var/lib/ubuntu-advantage/apt-esm/var/lib/apt/lists:
// esmAppsSecurityList
// esmAppsUpdatesList
// esmInfraSecurityList
// esmInfraUpdatesList


type PackageStatus struct {
	Name	string
	Version string
	Status  string
	Source  string
}

// Func to get file pathes for esm packages
// Based on os release codename

// Packages need to be read and parsed from all above files
// and then returned as a slice of PackageStatus
func readPackages(filepath string) ([]PackageStatus, error) {
	file, err := os.Open(filepath)
	if err != nil {
		return nil, error
	}
	defer file.Close()

	var packages []PackageStatus
	var curPackage PackageStatus

	scanner := bufio.NewScanner(file)
	parsingPackage := false

	for scanner.Scan(){
		line := strings.TrimSpace(scanner.Text())

		if strings.HasPrefix(line, "Package:") {
			if parsingPackage {
				packages = append(packages, currentPackage)
			}

			curPackage = PackageStatus{}
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
