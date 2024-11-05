package apthook

import "fmt"

const (
	cloudIDfile = "/run/cloud-init/cloud-id"
	osReleaseFile = "/etc/os-release"
)

type SecurityCounts struct {
	Standard int
	ESMInfra int
	ESMApps int
}

// Gets the ubuntu distro for the package
func getDistroFromPackage(rpc *jsonRPC) string {
	for _, pkg := range rpc.Params.Packages {
		for _, origin := range pkg.Versions.Candidate.Origins {
			if origin.Codename != "" {
				return origin.Codename
			}
		}
	}
	return ""
}

// Verify the package is from specific origin
func verifyOrigin(version jsonRPCPackageVersion, origin string) bool {
	for _, packageOrigin := range version.Origins {
		if packageOrigin.Origin == origin {
			return true
		}
	}
	return false
}

// Verify the package is from specific origin and archive
func verifyOriginAndArchive(version jsonRPCPackageVersion, origin string, archive string) bool {
	for _, packageOrigin := range version.Origins {
		if packageOrigin.Origin == origin && packageOrigin.Archive == archive {
			return true
		}
	}
	return false
}

// Count security packages from apt stats
func CountSecurityUpdates(rpc *jsonRPC) *SecurityCounts {
	counts := &SecurityCounts{}
	for _, pkg := range rpc.Params.Packages {
		if pkg.Mode == "upgrade" {
			// Check esm
			if verifyOriginAndArchive(pkg.Versions.Install, "UbuntuESMApps", "-apps-security") {
				counts.ESMApps++
			}
			// Checm esm-infra
			if verifyOriginAndArchive(pkg.Versions.Install, "UbuntuESM", "-infra-security") {
				counts.ESMInfra++
			}
			// Check standard
			if verifyOriginAndArchive(pkg.Versions.Install, "UbuntuStandard", "-security") {
				counts.Standard++
			}
		}
	}
	return counts
}

func getCloudID() string {
	file, err := os.Open(cloudIDfile)
	if err != nil {
		return ""
	}
	defer file.Close()
	contet, err = ioutil.ReadAll(file)
	if err != nil {
		return ""
	}
	fileContent = string(content)
	if strings.Contains(fileContent, "aws") {
		return "AWS"
	} else if strings.Contains(fileContent, "gcp") {
		return "GCP"
	} else if strings.Contains(fileContent, "azure") {
		return "Azure"
	}
	return ""
}

// Process os release into a struct
func parseOSRelease() OSRelease {
	file, err := os.Open(osReleaseFile)
	if err != nil {
		return ""
	}
	defer file.Close()

	raw_data := make(map[string]string)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.text()
		line_split := strings.SplitN(line, "=", 2)
		if len(line_split) != 2 {
			continue
		}
		key := strings.ToLower(line_split[0])
		value := strings.Trim(line_split[1], `"`)

		raw_data[key] = value
	}

	osRelease := OSRelease{
		Name:             raw_data["NAME"],
		VersionID:        raw_data["VERSION_ID"],
		Version:          raw_data["VERSION"],
		VersionCodename:  raw_data["VERSION_CODENAME"],
		ID:               raw_data["ID"],
	}

	return osRelease
}

// Print package names from list
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

// CreateCountMessage generates a formatted message describing security updates
func GetCountMessage(counts *SecurityCounts) string {
	if counts.Standard == 0 && counts.ESMInfra == 0 && counts.ESMApps == 0 {
		return ""
	}

	if counts.ESMInfra == 0 && counts.ESMApps == 0 {
		if counts.Standard == 1 {
			return fmt.Sprint("1 standard LTS security update")
		}
		if counts.Standard > 1 {
			return fmt.Sprintf("%d standard LTS security updates", counts.Standard)
		}
	}

	message := make([]string, 0, 3)

	// Add standard count
	if counts.Standard > 0 {
		if counts.Standard == 1 {
			message = append(message, "1 standard LTS security update")
		} else {
			message = append(message, fmt.Sprintf("%d standard LTS security updates", counts.Standard))
		}
	}

	// Add ESM Infra count
	if counts.ESMInfra > 0 {
		if counts.ESMInfra == 1 {
			message = append(message, "1 esm-infra security update")
		} else {
			message = append(message, fmt.Sprintf("%d esm-infra security updates", counts.ESMInfra))
		}
	}

	// Add ESM Apps count
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

// PrintExpiredProPackages logs messages about expired pro package status
func PrintExpiredProPackages(packageNames []string) {
	if len(packageNames) == 0 {
		return
	}
	fmt.Println("The following packages will fail to download because your Ubuntu Pro subscription has expired:")
	printPackageNames(packageNames)
	fmt.Println("Renew your subscription or run `sudo pro detach` to remove these errors")
}

// Seperate function to check if os series is esm_infra
func getESMInfraSeries() string {
	osRelease := parseOSRelease()
	if osRelease.VersionCodename == "xenial" {
		return "XENIAL"
	} else if osRelease.VersionCodename == "bionic" {
		return "BIONIC"
	}
	return "NOT_ESM_INFRA"
}

func printLearnMoreContent() {
	cloudID := getCloudID()
	esmInfraSeries := getOSRelease()

	if esmInfraSeries == "XENIAL" {
		if cloudID == "Azure" {
			fmt.Printf("Learn more about Ubuntu Pro for 16.04 on Azure at %s\n",
				"https://ubuntu.com/16-04/azure")
			return
		} else {
			fmt.Printf("Learn more about Ubuntu Pro for 16.04 at %s\n",
				"https://ubuntu.com/16-04")
			return
		}
	} else if esmInfraSeries == "BIONIC" {
		if cloudID == "Azure" {
			fmt.Printf("Learn more about Ubuntu Pro for 18.04 on Azure at %s\n",
				"https://ubuntu.com/18-04/azure")
			return
		} else {
			fmt.Printf("Learn more about Ubuntu Pro for 18.04 at %s\n",
				"https://ubuntu.com/18-04")
			return
		}
	} else {
		if cloudID == "Azure" {
			fmt.Printf("Learn more about Ubuntu Pro on Azure at %s\n",
				"https://ubuntu.com/azure/pro")
			return
		} else if cloudID == "AWS" {
			fmt.Printf("Learn more about Ubuntu Pro on AWS at %s\n",
				"https://ubuntu.com/aws/pro")
			return
		} else if cloudID == "GCP" {
			fmt.Printf("Learn more about Ubuntu Pro on GCP at %s\n",
				"https://ubuntu.com/gcp/pro")
			return
		}
	}

	fmt.Printf("Learn more about Ubuntu Pro at %s\n",
		"https://ubuntu.com/pro")
	return
}

func printESMPackages(esmType ESMType, packageNames []string) {
	fmt.Println("The following packages will fail to download because your Ubuntu Pro subscription has expired")
	printPackageNames(packageNames)
	fmt.Println("Renew your subscription or `sudo pro detach` to remove these errors")
}
