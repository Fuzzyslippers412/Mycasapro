#!/bin/sh
set -eu

REPOSITORY="Fuzzyslippers412/Mycasapro"
INSTALL_DIR="${MYCASAPRO_INSTALL_DIR:-$HOME/.local/bin}"
NO_SETUP="${MYCASAPRO_NO_SETUP:-0}"

if [ "${1:-}" = "--no-setup" ]; then
  NO_SETUP=1
fi

command -v curl >/dev/null 2>&1 || {
  echo "curl is required to install MyCasaPro." >&2
  exit 1
}

case "$(uname -s)" in
  Darwin) os="darwin" ;;
  Linux) os="linux" ;;
  *) echo "MyCasaPro supports macOS, Linux, and Windows." >&2; exit 1 ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) echo "Unsupported processor architecture: $(uname -m)" >&2; exit 1 ;;
esac

latest_url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPOSITORY/releases/latest")"
tag="${latest_url##*/}"
if [ -z "$tag" ] || [ "$tag" = "latest" ]; then
  echo "No MyCasaPro release is available yet." >&2
  exit 1
fi

version="${tag#v}"
asset="mycasapro_${version}_${os}_${arch}.tar.gz"
base_url="https://github.com/$REPOSITORY/releases/download/$tag"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT HUP INT TERM

echo "Downloading MyCasaPro $tag for $os/$arch..."
curl -fsSL "$base_url/$asset" -o "$temp_dir/$asset"
curl -fsSL "$base_url/checksums.txt" -o "$temp_dir/checksums.txt"

expected="$(awk -v asset="$asset" '$2 == asset { print $1 }' "$temp_dir/checksums.txt")"
if [ -z "$expected" ]; then
  echo "Release checksum is missing for $asset." >&2
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$temp_dir/$asset" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$temp_dir/$asset" | awk '{print $1}')"
fi
if [ "$actual" != "$expected" ]; then
  echo "Checksum verification failed. Nothing was installed." >&2
  exit 1
fi

tar -xzf "$temp_dir/$asset" -C "$temp_dir"
mkdir -p "$INSTALL_DIR"
install -m 0755 "$temp_dir/mycasapro" "$INSTALL_DIR/mycasapro"

echo "Installed MyCasaPro to $INSTALL_DIR/mycasapro"
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Add this directory to PATH:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    ;;
esac

if [ "$NO_SETUP" != "1" ]; then
  "$INSTALL_DIR/mycasapro" setup
fi
