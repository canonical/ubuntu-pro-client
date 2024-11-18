package apthook

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"io/ioutil"
)

const (
	cloudIDFile    = "/run/cloud-init/cloud-id"
	osReleaseFile  = "/etc/os-release"
)

type SecurityCounts struct {
	Standard int
	ESMInfra int
	ESMApps  int
}

// verifyOrigin checks if the package is from a specific origin.
func verifyOrigin(version jsonRPCPackageVersion, origin string) bool {
	for _, packageOrigin := range version.Origins {
		if packageOrigin.Origin == origin {
			return true
		}
	}
	return false
}

// verifyOriginAndArchive checks if the package is from a specific origin and archive.
func verifyOriginAndArchive(version jsonRPCPackageVersion, origin, archive string) bool {
	for _, packageOrigin := range version.Origins {
		if packageOrigin.Origin == origin && packageOrigin.Archive == archive {
			return true
		}
	}
	return false
}

// getCloudID retrieves the cloud ID.
func getCloudID() string {
	file, err := os.Open(cloudIDFile)
	if err != nil {
		return ""
	}
	defer file.Close()

	content, err := ioutil.ReadAll(file)
	if err != nil {
		return ""
	}
	fileContent := string(content)
	if strings.Contains(fileContent, "aws") {
		return "AWS"
	} else if strings.Contains(fileContent, "gcp") {
		return "GCP"
	} else if strings.Contains(fileContent, "azure") {
		return "Azure"
	}
	return ""
}

// ParseOSRelease processes OS release information into a struct.
func ParseOSRelease() OSRelease {
	file, err := os.Open(osReleaseFile)
	if err != nil {
		return OSRelease{}
	}
	defer file.Close()

	rawData := make(map[string]string)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		lineSplit := strings.SplitN(line, "=", 2)
		if len(lineSplit) != 2 {
			continue
		}
		key := strings.ToLower(lineSplit[0])
		value := strings.Trim(lineSplit[1], `"`)
		rawData[key] = value
	}

	return OSRelease{
		Name:            rawData["name"],
		VersionID:       rawData["version_id"],
		Version:         rawData["version"],
		VersionCodename: rawData["version_codename"],
		ID:              rawData["id"],
	}
}

// printPackageNames prints package names from a list.
func printPackageNames(packageNames []string) {
	currLine := " "
	for _, pkg := range packageNames {
		if len(currLine)+1+len(pkg) >= 79 {
			fmt.Println(currLine)
			currLine = " "
		}
		currLine = currLine + " " + pkg
	}
	if len(currLine) > 1 {
		fmt.Println(currLine)
	}
}

// getESMInfraSeries checks if the OS series is esm_infra.
func getESMInfraSeries() string {
	osRelease := ParseOSRelease()
	switch osRelease.VersionCodename {
	case "xenial":
		return "XENIAL"
	case "bionic":
		return "BIONIC"
	default:
		return "NOT_ESM_INFRA"
	}
}

func printLearnMoreContent() {
	cloudID := getCloudID()
	esmInfraSeries := getESMInfraSeries()

	switch esmInfraSeries {
	case "XENIAL":
		if cloudID == "Azure" {
			fmt.Println("Learn more about Ubuntu Pro for 16.04 on Azure at https://ubuntu.com/16-04/azure")
			return
		}
		fmt.Println("Learn more about Ubuntu Pro for 16.04 at https://ubuntu.com/16-04")
		return
	case "BIONIC":
		if cloudID == "Azure" {
			fmt.Println("Learn more about Ubuntu Pro for 18.04 on Azure at https://ubuntu.com/18-04/azure")
			return
		}
		fmt.Println("Learn more about Ubuntu Pro for 18.04 at https://ubuntu.com/18-04")
		return
	default:
		switch cloudID {
		case "Azure":
			fmt.Println("Learn more about Ubuntu Pro on Azure at https://ubuntu.com/azure/pro")
		case "AWS":
			fmt.Println("Learn more about Ubuntu Pro on AWS at https://ubuntu.com/aws/pro")
		case "GCP":
			fmt.Println("Learn more about Ubuntu Pro on GCP at https://ubuntu.com/gcp/pro")
		default:
			fmt.Println("Learn more about Ubuntu Pro at https://ubuntu.com/pro")
		}
	}
}

// CountSecurityUpdates counts security packages from apt stats.
func CountSecurityUpdates(rpc *jsonRPC) *SecurityCounts {
	counts := &SecurityCounts{}
	for _, pkg := range rpc.Params.Packages {
		if pkg.Mode == "upgrade" {
			if verifyOriginAndArchive(pkg.Versions.Install, "UbuntuESMApps", "-apps-security") {
				counts.ESMApps++
			}
			if verifyOriginAndArchive(pkg.Versions.Install, "UbuntuESM", "-infra-security") {
				counts.ESMInfra++
			}
			if verifyOriginAndArchive(pkg.Versions.Install, "UbuntuStandard", "-security") {
				counts.Standard++
			}
		}
	}
	return counts
}

// GetCountMessage generates a formatted message describing security updates.
func GetCountMessage(counts *SecurityCounts) string {
	if counts.Standard == 0 && counts.ESMInfra == 0 && counts.ESMApps == 0 {
		return ""
	}

	if counts.ESMInfra == 0 && counts.ESMApps == 0 {
		if counts.Standard == 1 {
			return "1 standard LTS security update"
		}
		return fmt.Sprintf("%d standard LTS security updates", counts.Standard)
	}

	message := make([]string, 0, 3)

	if counts.Standard > 0 {
		if counts.Standard == 1 {
			message = append(message, "1 standard LTS security update")
		} else {
			message = append(message, fmt.Sprintf("%d standard LTS security updates", counts.Standard))
		}
	}

	if counts.ESMInfra > 0 {
		if counts.ESMInfra == 1 {
			message = append(message, "1 esm-infra security update")
		} else {
			message = append(message, fmt.Sprintf("%d esm-infra security updates", counts.ESMInfra))
		}
	}

	if counts.ESMApps > 0 {
		if counts.ESMApps == 1 {
			message = append(message, "1 esm-apps security update")
		} else {
			message = append(message, fmt.Sprintf("%d esm-apps security updates", counts.ESMApps))
		}
	}

	switch len(message) {
	case 1:
		return message[0]
	case 2:
		return fmt.Sprintf("%s and %s", message[0], message[1])
	case 3:
		return fmt.Sprintf("%s, %s and %s", message[0], message[1], message[2])
	}

	return ""
}

// CollectProPackagesFromRPC collects packages from RPC.
func CollectProPackagesFromRPC(rpc *jsonRPC) []string {
	var expiredPackages []string

	proOrigins := []string{
		"UbuntuESM",
		"UbuntuESMApps",
		"UbuntuCC",
		"UbuntuCIS",
		"UbuntuFIPS",
		"UbuntuFIPSUpdates",
		"UbuntuFIPSPreview",
		"UbuntuRealtimeKernel",
		"UbuntuROS",
		"UbuntuROSUpdates",
	}

	for _, pkg := range rpc.Params.Packages {
		if pkg.Mode == "upgrade" {
			for _, origin := range proOrigins {
				if verifyOrigin(pkg.Versions.Install, origin) {
					expiredPackages = append(expiredPackages, pkg.Name)
					break
				}
			}
		}
	}

	return expiredPackages
}

// PrintExpiredProPackages logs messages about expired pro package status.
func PrintExpiredProPackages(packageNames []string) {
	if len(packageNames) == 0 {
		return
	}
	fmt.Println("The following packages will fail to download because your Ubuntu Pro subscription has expired:")
	printPackageNames(packageNames)
	fmt.Println("Renew your subscription or run `sudo pro detach` to remove these errors")
}

// printESMPackages prints expired ESM packages.
func PrintESMPackages(esmType string, packageNames []string) {
	if esmType == "APPS" {
		if len(packageNames) == 1 {
			fmt.Println("Get another security update through Ubuntu Pro with 'esm-apps' enabled:")
		} else {
			fmt.Println("Get more security updates through Ubuntu Pro with 'esm-apps' enabled:")
		}
	} else if esmType == "INFRA" {
		if len(packageNames) == 1 {
			fmt.Println("The following security update requires Ubuntu Pro with 'esm-infra' enabled:")
		} else {
			fmt.Println("The following security updates require Ubuntu Pro with 'esm-infra' enabled:")
		}
	}

	printPackageNames(packageNames)
	printLearnMoreContent()
}
