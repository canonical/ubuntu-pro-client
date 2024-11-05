package apthook

import (
	"encoding/json"
)

type jsonRPC struct {
	JsonRPC	string	`json:"jsonrpc"`
	Method	string	`json:"method"`
	Params	struct {
		Command	        string   `json:"command"`
		UnknownPackages	[]string `json:"unknown-packages"`
		Packages		[]Package `json:"packages"`
	} `json:"params"`
}

type Package struct {
	ID           int    `json:"id"`
	Name         string `json:"name"`
	Architecture string `json:"architecture"`
	Mode         string `json:"mode"`
	Versions     Versions `json:"versions,omitempty"` // optional
	Automatic    bool `json:"automatic,omitempty"`	// optional
	Current	     string `json:"current,omitempty"`	// optional
}

type Versions struct {
	Candidate	jsonRPCPackageVersion	`json:"candidate"`
	Install		jsonRPCPPackageVersion	`json:"install"`
	Current		jsonRPCPackageVersion	`json:"current"`
}

type jsonRPCPackageVersion struct {
	ID           int    `json:"id"`
	Version      string `json:"version"`
	Architecture string `json:"architecture"`
	Pin          int    `json:"pin"`
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
	Name             string
	VersionID        string
	Version          string
	VersionCodename  string
	ID               string
}
