package apthook

import (
	"fmt"
	"io/ioutil"
	"os"
	"strconv"
)

const (
	methodStats = "org.debian.apt.hooks.install.statistics"
	methodPrePrompt = "org.debian.apt.hooks.install.pre-prompt"
	aptNewsFile = "/var/lib/ubuntu-advantage/messages/apt-news"
	expiredNotice = "/var/lib/ubuntu-advantage/notices/5-contract_expired"
)

func main() {
	sockFd := os.Getenv("APT_HOOK_SOCKET")
	if sockFd == "" {
		fmt.Println("NO APT SOCKET")
		fmt.Fprintf(os.Stderr, "pro-apt-hook: missing socket fd\n")
		os.Exit(1)
	}

	fd, err := strconv.Atoi(sockFd)
	if err != nil {
		fmt.Fprintf(os.Stderr, "pro-apt-hook: invalid socket fd: %v\n", err)
		os.Exit(1)
	}

	file := os.NewFile(uintptr(fd), "apt-hook-socket")
	if file == nil {
		fmt.Fprintf(os.Stderr, "pro-apt-hook: cannot open file descriptor %d\n", fd)
		os.Exit(1)
	}
	defer file.Close()

	conn, err := NewConnection(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "pro-apt-hook: failed to create connection: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()

	if err := conn.Handshake(); err != nil {
		fmt.Fprintf(os.Stderr, "pro-apt-hook: handshake failed: %v\n", err)
		os.Exit(1)
	}

	msg, err := conn.ReadMessage()
	if err != nil {
		fmt.Fprintf(os.Stderr, "pro-apt-hook: reading message: %v\n", err)
		os.Exit(1)
	}

	switch msg.Method {

	case methodStats:
		counts := CountSecurityUpdates(msg)
		if message := GetCountMessage(counts); message != "" {
			fmt.Println(message)
		}

	case methodPrePrompt:
		// Get ESM updates
		if updates, err := GetPotentialESMUpdates(); err == nil {
			if len(updates.InfraPackages) > 0 {
				PrintESMPackages("INFRA", updates.InfraPackages)
			} else if len(updates.AppsPackages) > 0 {
				PrintESMPackages("APPS", updates.AppsPackages)
			}
		}

		if news, err := ioutil.ReadFile(aptNewsFile); err == nil {
			fmt.Print(string(news))
		}

		if _, err := os.Stat(expiredNotice); err == nil {
			expiredPkgs := CollectProPackagesFromRPC(msg)
			if len(expiredPkgs) > 0 {
				PrintExpiredProPackages(expiredPkgs)
			}
		}
	}

	if err := conn.Bye(); err != nil {
		fmt.Fprintf(os.Stderr, "pro-apt-hook: bye failed: %v\n", err)
		os.Exit(1)
	}
}
