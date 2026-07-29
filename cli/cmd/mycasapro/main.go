package main

import (
	"os"

	"github.com/Fuzzyslippers412/Mycasapro/cli/internal/command"
)

var (
	version = "dev"
	commit  = "unknown"
)

func main() {
	os.Exit(command.Run(os.Args[1:], version, commit))
}
