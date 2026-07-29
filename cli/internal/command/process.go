package command

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"time"
)

func requireDocker(ctx context.Context) error {
	if _, err := exec.LookPath("docker"); err != nil {
		return errors.New("Docker is required. Install Docker Desktop or Docker Engine, then try again")
	}
	if err := exec.CommandContext(ctx, "docker", "compose", "version").Run(); err != nil {
		return errors.New("Docker Compose is unavailable. Install a current Docker release, then try again")
	}
	if err := exec.CommandContext(ctx, "docker", "info").Run(); err != nil {
		return errors.New("Docker is installed but not running. Start Docker, then try again")
	}
	return nil
}

func composeCommand(ctx context.Context, cfg config, args ...string) *exec.Cmd {
	base := []string{
		"compose",
		"--project-name", "mycasapro",
		"--project-directory", cfg.Home,
		"--env-file", cfg.Home + string(os.PathSeparator) + ".env",
		"-f", cfg.Home + string(os.PathSeparator) + "compose.yaml",
	}
	cmd := exec.CommandContext(ctx, "docker", append(base, args...)...)
	cmd.Dir = cfg.Home
	return cmd
}

func runCompose(ctx context.Context, cfg config, args ...string) error {
	cmd := composeCommand(ctx, cfg, args...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("docker compose %s: %w", args[0], err)
	}
	return nil
}

func runComposeIO(ctx context.Context, cfg config, stdin io.Reader, stdout io.Writer, args ...string) error {
	cmd := composeCommand(ctx, cfg, args...)
	cmd.Stdin = stdin
	cmd.Stdout = stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("docker compose %s: %w", args[0], err)
	}
	return nil
}

func healthy(ctx context.Context, cfg config) bool {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, cfg.URL()+"/healthz", nil)
	if err != nil {
		return false
	}
	client := &http.Client{Timeout: 3 * time.Second}
	response, err := client.Do(request)
	if err != nil {
		return false
	}
	defer response.Body.Close()
	return response.StatusCode == http.StatusOK
}

func waitForHealthy(ctx context.Context, cfg config, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if healthy(ctx, cfg) {
			return nil
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(time.Second):
		}
	}
	return fmt.Errorf("MyCasaPro did not become healthy within %s; run mycasapro logs", timeout.Round(time.Second))
}

func openBrowser(url string) error {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("open", url)
	case "windows":
		cmd = exec.Command("cmd", "/c", "start", "", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("open browser: %w", err)
	}
	return nil
}
