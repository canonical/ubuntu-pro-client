package apthook

import (
	"fmt"
	"strings"
	"os"
	"os/exec"
)

const (
	methodStats = "org.debian.apt.hooks.install.statistics"
	methodPrePrompt = "org.debian.apt.hooks.install.pre-prompt"
	aptNewsFile = "/var/lib/ubuntu-advantage/messages/apt-news"
	expiredNotice = "/var/lib/ubuntu-advantage/notices/5-contract_expired"
)

func main() {
	// Get apt hook socker
	// Make sure socket in not empty and exists
	// jsonrpc handshake
	// jsonrpc read rpc message
	//
	// if method status
	// 	display security count message
	// if method pre-prompt
	//  get potential esm updates
	//  call display functions from counts file
	//
	// Display apt news
	// Display contract expiration notice
	//
	// jsonpc bye bye
}
