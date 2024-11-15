package apthook

import (
	"fmt"
	"os"
	"strconv"
)

const (
	methodStats = "org.debian.apt.hooks.install.statistics"
	methodPrePrompt = "org.debian.apt.hooks.install.pre-prompt"
	aptNewsFile = "/var/lib/ubuntu-advantage/messages/apt-news"
	expiredNotice = "/var/lib/ubuntu-advantage/notices/5-contract_expired"
)

func main() error {
	sockFd := os.Getenv("APT_HOOK_SOCKET")
	if sockFd == "" {
		return fmt.Errorf("pro-apt-hook: missing socket fd")
	}

	fd, err := strconv.Atoi(sockFd)
	if err != nil {
		return fmt.Errorf("pro-apt-hook: invalid socket fd: %w", err)
	}

	file := os.NewFile(uintptr(fd), "apt-hook-socket")
	if file == nil {
		return fmt.Errorf("pro-apt-hook: cannot open file descriptor %d", fd)
	}
	defer file.Close()

	conn, err := NewConnection(file)
	if err != nil {
		return fmt.Errorf("pro-apt-hook: failed to create connection: %w", err)
	}
	defer conn.Close()

	if err := conn.Handshake(); err != nil {
		return fmt.Errorf("pro-apt-hook: handshake failed: %w", err)
	}

	msg, err := conn.ReadMessage()
	if err != nil {
		return fmt.Errorf("pro-apt-hook: reading message: %w", err)
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

		if news, err := os.ReadFile(aptNewsFile); err == nil {
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
		return fmt.Errorf("pro-apt-hook: bye failed: %w", err)
	}

	return nil
}
