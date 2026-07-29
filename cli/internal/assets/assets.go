package assets

import _ "embed"

// ComposeYAML is the self-hosted MyCasaPro appliance definition.
//
//go:embed compose.yaml
var ComposeYAML []byte
