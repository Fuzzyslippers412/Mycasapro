param(
  [switch]$NoSetup
)

$ErrorActionPreference = "Stop"
$Repository = "Fuzzyslippers412/Mycasapro"
$InstallDir = if ($env:MYCASAPRO_INSTALL_DIR) { $env:MYCASAPRO_INSTALL_DIR } else { Join-Path $HOME ".mycasapro\bin" }

$architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
switch ($architecture) {
  "x64" { $arch = "amd64" }
  "arm64" { $arch = "arm64" }
  default { throw "Unsupported processor architecture: $architecture" }
}

$headers = @{ "User-Agent" = "MyCasaPro-Installer" }
$release = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repository/releases/latest"
$tag = $release.tag_name
if (-not $tag) { throw "No MyCasaPro release is available yet." }
$version = $tag.TrimStart("v")
$assetName = "mycasapro_${version}_windows_${arch}.zip"
$asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
$checksums = $release.assets | Where-Object { $_.name -eq "checksums.txt" } | Select-Object -First 1
if (-not $asset -or -not $checksums) { throw "This release does not include $assetName or checksums.txt." }

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("mycasapro-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tempDir | Out-Null
try {
  $archivePath = Join-Path $tempDir $assetName
  $checksumsPath = Join-Path $tempDir "checksums.txt"
  Write-Host "Downloading MyCasaPro $tag for Windows/$arch..."
  Invoke-WebRequest -Headers $headers -Uri $asset.browser_download_url -OutFile $archivePath
  Invoke-WebRequest -Headers $headers -Uri $checksums.browser_download_url -OutFile $checksumsPath

  $checksumLine = Get-Content $checksumsPath | Where-Object { $_ -match "\s+$([regex]::Escape($assetName))$" } | Select-Object -First 1
  if (-not $checksumLine) { throw "Release checksum is missing for $assetName." }
  $expected = ($checksumLine -split "\s+")[0].ToLowerInvariant()
  $actual = (Get-FileHash -Algorithm SHA256 $archivePath).Hash.ToLowerInvariant()
  if ($actual -ne $expected) { throw "Checksum verification failed. Nothing was installed." }

  Expand-Archive -Path $archivePath -DestinationPath $tempDir -Force
  New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
  $executable = Join-Path $InstallDir "mycasapro.exe"
  Copy-Item (Join-Path $tempDir "mycasapro.exe") $executable -Force

  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $pathParts = @($userPath -split ";" | Where-Object { $_ })
  if ($pathParts -notcontains $InstallDir) {
    $newPath = (($pathParts + $InstallDir) -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$env:Path;$InstallDir"
  }

  Write-Host "Installed MyCasaPro to $executable"
  if (-not $NoSetup) { & $executable setup }
}
finally {
  Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}
