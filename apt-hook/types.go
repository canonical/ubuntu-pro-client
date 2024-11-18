package apthook

type jsonRPC struct {
	JsonRPC string `json:"jsonrpc"`
	Method  string `json:"method"`
	Params  struct {
		Command         string    `json:"command"`
		UnknownPackages []string  `json:"unknown-packages"`
		Packages        []Package `json:"packages"`
	} `json:"params"`
}

type Package struct {
	ID           int      `json:"id"`
	Name         string   `json:"name"`
	Architecture string   `json:"architecture"`
	Mode         string   `json:"mode"`
	Versions     Versions `json:"versions,omitempty"`  // Optional
	Automatic    bool     `json:"automatic,omitempty"` // Optional
	Current      string   `json:"current,omitempty"`   // Optional
}

type Versions struct {
	Candidate jsonRPCPackageVersion `json:"candidate"`
	Install   jsonRPCPackageVersion  `json:"install"`
	Current   jsonRPCPackageVersion  `json:"current"`
}

type jsonRPCPackageVersion struct {
	ID           int      `json:"id"`
	Version      string   `json:"version"`
	Architecture string   `json:"architecture"`
	Pin          int      `json:"pin"`
	Origins      []Origin `json:"origins"`
}

type Origin struct {
	Archive  string `json:"archive"`
	Codename string `json:"codename"`
	Version  string `json:"version"`
	Origin   string `json:"origin"`
	Label    string `json:"label"`
	Site     string `json:"site"`
}

type OSRelease struct {
	Name            string `json:"name"`
	VersionID       string `json:"version_id"`
	Version         string `json:"version"`
	VersionCodename string `json:"version_codename"`
	ID              string `json:"id"`
}
