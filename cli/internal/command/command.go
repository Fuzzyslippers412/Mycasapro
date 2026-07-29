package command

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const startupTimeout = 3 * time.Minute

func Run(args []string, buildVersion, buildCommit string) int {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()
	if err := run(ctx, args, buildVersion, buildCommit); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		return 1
	}
	return 0
}

func run(ctx context.Context, args []string, buildVersion, buildCommit string) error {
	if len(args) == 0 {
		return runDefault(ctx)
	}
	switch args[0] {
	case "setup":
		return runSetup(ctx, args[1:])
	case "start":
		return runStart(ctx, false)
	case "stop":
		return runStop(ctx)
	case "status":
		return runStatus(ctx, args[1:])
	case "logs":
		return runLogs(ctx, args[1:])
	case "open":
		return runOpen(ctx)
	case "update":
		return runUpdate(ctx, args[1:])
	case "doctor":
		return runDoctor(ctx)
	case "backup":
		return runBackup(ctx, args[1:])
	case "restore":
		return runRestore(ctx, args[1:])
	case "uninstall":
		return runUninstall(ctx, args[1:])
	case "version", "--version", "-v":
		fmt.Printf("mycasapro %s (%s)\n", buildVersion, buildCommit)
		return nil
	case "help", "--help", "-h":
		printHelp()
		return nil
	default:
		return fmt.Errorf("unknown command %q; run mycasapro help", args[0])
	}
}

func runDefault(ctx context.Context) error {
	if !configExists() {
		return runSetup(ctx, nil)
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if healthy(ctx, cfg) {
		return openBrowser(cfg.URL())
	}
	return runStart(ctx, true)
}

func runSetup(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("setup", flag.ContinueOnError)
	port := flags.Int("port", defaultPort, "localhost port")
	version := flags.String("version", defaultVersion, "image version")
	noStart := flags.Bool("no-start", false, "configure without starting")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("usage: mycasapro setup [--port 3210] [--no-start]")
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}

	var cfg config
	var err error
	if configExists() {
		cfg, err = loadConfig()
		if err != nil {
			return err
		}
		if wasSet(args, "port") {
			cfg.Port = *port
		}
		if wasSet(args, "version") {
			cfg.Version = *version
		}
	} else {
		cfg, err = newConfig(*port, *version)
		if err != nil {
			return err
		}
	}
	if !healthy(ctx, cfg) {
		if err := ensurePortAvailable(cfg.Port); err != nil {
			return err
		}
	}
	if err := saveConfig(cfg); err != nil {
		return err
	}
	fmt.Printf("MyCasaPro configured in %s\n", cfg.Home)
	if *noStart {
		fmt.Println("Run `mycasapro start` when you are ready.")
		return nil
	}
	if err := runCompose(ctx, cfg, "pull"); err != nil {
		return err
	}
	return startAndWait(ctx, cfg, true)
}

func runStart(ctx context.Context, shouldOpen bool) error {
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}
	return startAndWait(ctx, cfg, shouldOpen)
}

func startAndWait(ctx context.Context, cfg config, shouldOpen bool) error {
	if err := runCompose(ctx, cfg, "up", "-d", "--remove-orphans"); err != nil {
		return err
	}
	fmt.Print("Waiting for MyCasaPro")
	if err := waitForHealthy(ctx, cfg, startupTimeout); err != nil {
		fmt.Println()
		return err
	}
	fmt.Printf(" ready.\n%s\n", cfg.URL())
	if shouldOpen {
		if err := openBrowser(cfg.URL()); err != nil {
			fmt.Printf("Open %s in your browser.\n", cfg.URL())
		}
	}
	return nil
}

func runStop(ctx context.Context) error {
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}
	if err := runCompose(ctx, cfg, "stop"); err != nil {
		return err
	}
	fmt.Println("MyCasaPro stopped. Your data is preserved.")
	return nil
}

func runStatus(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("status", flag.ContinueOnError)
	jsonOutput := flags.Bool("json", false, "print JSON")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("usage: mycasapro status [--json]")
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	isHealthy := healthy(ctx, cfg)
	if *jsonOutput {
		return json.NewEncoder(os.Stdout).Encode(map[string]any{
			"configured": true,
			"healthy":    isHealthy,
			"url":        cfg.URL(),
			"version":    cfg.Version,
			"state_dir":  cfg.Home,
		})
	}
	state := "stopped or unhealthy"
	if isHealthy {
		state = "running"
	}
	fmt.Printf("MyCasaPro: %s\nURL: %s\nVersion: %s\nData: %s\n", state, cfg.URL(), cfg.Version, cfg.Home)
	if _, err := exec.LookPath("docker"); err == nil {
		_ = runCompose(ctx, cfg, "ps")
	}
	return nil
}

func runLogs(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("logs", flag.ContinueOnError)
	tail := flags.Int("tail", 200, "number of lines")
	follow := flags.Bool("follow", false, "follow logs")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *tail < 0 || flags.NArg() != 0 {
		return errors.New("usage: mycasapro logs [--tail 200] [--follow]")
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	composeArgs := []string{"logs", "--tail", strconv.Itoa(*tail)}
	if *follow {
		composeArgs = append(composeArgs, "--follow")
	}
	return runCompose(ctx, cfg, composeArgs...)
}

func runOpen(ctx context.Context) error {
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if !healthy(ctx, cfg) {
		return errors.New("MyCasaPro is not running; run mycasapro start")
	}
	return openBrowser(cfg.URL())
}

func runUpdate(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("update", flag.ContinueOnError)
	version := flags.String("version", defaultVersion, "image version")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("usage: mycasapro update [--version v0.2.0]")
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}
	cfg.Version = *version
	if err := saveConfig(cfg); err != nil {
		return err
	}
	if err := runCompose(ctx, cfg, "pull"); err != nil {
		return err
	}
	if err := startAndWait(ctx, cfg, false); err != nil {
		return err
	}
	fmt.Printf("MyCasaPro updated to %s.\n", cfg.Version)
	return nil
}

func runDoctor(ctx context.Context) error {
	failed := false
	check := func(label string, err error) {
		if err != nil {
			failed = true
			fmt.Printf("[fail] %s: %v\n", label, err)
			return
		}
		fmt.Printf("[ok]   %s\n", label)
	}
	_, err := exec.LookPath("docker")
	check("Docker installed", err)
	if err == nil {
		check("Docker Compose available", exec.CommandContext(ctx, "docker", "compose", "version").Run())
		check("Docker engine running", exec.CommandContext(ctx, "docker", "info").Run())
	}
	cfg, configErr := loadConfig()
	check("Local configuration", configErr)
	if configErr == nil {
		_, composeErr := os.Stat(filepath.Join(cfg.Home, "compose.yaml"))
		check("Runtime definition", composeErr)
		if healthy(ctx, cfg) {
			check("Application health", nil)
		} else {
			check("Application health", errors.New("not responding; run mycasapro start, then mycasapro logs if needed"))
		}
	}
	if failed {
		return errors.New("one or more checks failed")
	}
	return nil
}

func runBackup(ctx context.Context, args []string) error {
	if len(args) > 1 {
		return errors.New("usage: mycasapro backup [path]")
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}
	destination := ""
	if len(args) == 1 {
		destination = args[0]
	}
	return createBackup(ctx, cfg, destination)
}

func runRestore(ctx context.Context, args []string) error {
	if len(args) != 2 || (args[0] != "--yes" && args[1] != "--yes") {
		return errors.New("restore replaces current data; use: mycasapro restore <backup.tar.gz> --yes")
	}
	source := args[0]
	if source == "--yes" {
		source = args[1]
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}
	return restoreBackup(ctx, cfg, source)
}

func runUninstall(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("uninstall", flag.ContinueOnError)
	purge := flags.Bool("purge", false, "remove all MyCasaPro data")
	yes := flags.Bool("yes", false, "confirm data removal")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("usage: mycasapro uninstall [--purge --yes]")
	}
	cfg, err := loadConfig()
	if err != nil {
		return err
	}
	if err := requireDocker(ctx); err != nil {
		return err
	}
	if !*purge {
		if err := runCompose(ctx, cfg, "down"); err != nil {
			return err
		}
		fmt.Printf("MyCasaPro containers removed. Data remains in Docker volumes and %s.\n", cfg.Home)
		fmt.Println("Run `mycasapro uninstall --purge --yes` only if you want to permanently delete it.")
		return nil
	}
	if !*yes {
		return errors.New("purge permanently deletes all homes, projects, accounts, and uploads; add --yes to confirm")
	}
	if err := safeManagedHome(cfg.Home); err != nil {
		return err
	}
	if err := runCompose(ctx, cfg, "down", "--volumes", "--remove-orphans"); err != nil {
		return err
	}
	if err := os.RemoveAll(cfg.Home); err != nil {
		return fmt.Errorf("remove local state: %w", err)
	}
	fmt.Println("MyCasaPro data and containers were permanently removed.")
	return nil
}

func safeManagedHome(home string) error {
	clean := filepath.Clean(home)
	userHome, _ := os.UserHomeDir()
	if clean == "." || clean == string(os.PathSeparator) || clean == filepath.Clean(userHome) {
		return errors.New("refusing to remove an unsafe state directory")
	}
	if _, err := os.Stat(filepath.Join(clean, markerName)); err != nil {
		return errors.New("refusing to remove an unrecognized state directory")
	}
	return nil
}

func ensurePortAvailable(port int) error {
	listener, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
	if err != nil {
		return fmt.Errorf("port %d is already in use; choose another with --port", port)
	}
	return listener.Close()
}

func wasSet(args []string, name string) bool {
	prefix := "--" + name
	for _, arg := range args {
		if arg == prefix || strings.HasPrefix(arg, prefix+"=") {
			return true
		}
	}
	return false
}

func printHelp() {
	fmt.Print(`MyCasaPro runs a private home-maintenance workspace on this computer.

Usage:
  mycasapro                         Set up, start, or open MyCasaPro
  mycasapro setup [--port 3210]    Install the local runtime
  mycasapro start                  Start MyCasaPro
  mycasapro stop                   Stop MyCasaPro without deleting data
  mycasapro status [--json]        Show runtime status
  mycasapro logs [--follow]        Show service logs
  mycasapro open                   Open the app in a browser
  mycasapro update [--version vX]  Update local containers
  mycasapro doctor                 Diagnose the local installation
  mycasapro backup [path]          Back up database and uploads
  mycasapro restore <path> --yes   Restore a backup
  mycasapro uninstall              Remove containers but preserve data
  mycasapro uninstall --purge --yes
                                    Permanently remove all local data
  mycasapro version                Print CLI version
`)
}
