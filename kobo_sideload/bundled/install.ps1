# Copy this release onto a USB-mounted Kobo. No Python required.
# Right-click → Run with PowerShell. If blocked: Set-ExecutionPolicy -Scope Process Bypass
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Label = "KOBOeReader"
$ExcludeLine = 'ExcludeSyncFolders=((KOReader)|\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)'
$StarDictMarker = "-- kobo-sideload dictionaries"
$StarDictLine = 'STARDICT_DATA_DIR = "/mnt/onboard/.adds/dictionaries"'
# Keep URLs in sync with kobo_sideload/dicts.py
$DictCatalog = @(
    @{ Langs = @("en"); Url = "http://build.koreader.rocks/download/dict/gcide.tar.gz"; File = "gcide.tar.gz" },
    @{ Langs = @("ru"); Url = "https://gitlab.com/avsej/dicts-stardict-form-xdxf/raw/d636cc5e8d4a47e22ac7466f4af6d435a8a3f650/002c/stardict-comn_sdict05_rus_eng_short-2.4.2.tar.gz"; File = "stardict-rus-eng-short.tar.gz" },
    @{ Langs = @("ru"); Url = "https://gitlab.com/avsej/dicts-stardict-form-xdxf/raw/d636cc5e8d4a47e22ac7466f4af6d435a8a3f650/001/stardict-comn_dictd03_ushakov-2.4.2.tar.gz"; File = "stardict-ushakov.tar.gz" }
)

function Die($msg) {
    Write-Host "error: $msg"
    Read-Host "Press Enter to exit"
    exit 1
}

function DictCacheDir {
    if ($env:KOBO_SIDELOAD_HOME) { return (Join-Path $env:KOBO_SIDELOAD_HOME "cache") }
    $base = $env:LOCALAPPDATA
    if (-not $base) { $base = Join-Path $env:USERPROFILE "AppData\Local" }
    return (Join-Path $base "kobo-sideload\cache")
}

function Ensure-StarDictLua($lua) {
    $dir = Split-Path $lua
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $text = ""
    if (Test-Path $lua) { $text = Get-Content -Raw -ErrorAction SilentlyContinue $lua }
    if ($null -eq $text) { $text = "" }
    if ($text -like "*$StarDictMarker*") { return }
    Add-Content -Path $lua -Value "`n$StarDictMarker`n$StarDictLine`n"
}

function Ensure-DictionariesFolder($dest) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    @"
StarDict dictionaries for KOReader
==================================

Long-press a word in a book to look it up.

This folder is outside the KOReader app tree so reinstalling the app
does not delete dictionaries.

You can also download dictionaries on the device:
  KOReader -> Search (magnifying glass) -> Dictionary settings
           -> Download dictionaries
  (needs Wi-Fi; the Kobo cannot download while it is plugged in over USB)
"@ | Set-Content -Path (Join-Path $dest "README.txt")
}

function Migrate-LegacyDicts($koreader, $dest) {
    $old = Join-Path $koreader "data\dict"
    if (-not (Test-Path $old)) { return }
    Get-ChildItem $old | ForEach-Object {
        $target = Join-Path $dest $_.Name
        if (-not (Test-Path $target)) {
            Copy-Item $_.FullName $target -Recurse -Force
        }
    }
}

function Download-File($url, $dest) {
    if (Test-Path $dest) { return }
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    $partial = "$dest.partial"
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        & curl.exe -L --fail --retry 3 --connect-timeout 30 -o $partial $url
        if ($LASTEXITCODE -ne 0) { throw "download failed: $url" }
    } else {
        Invoke-WebRequest -Uri $url -OutFile $partial -UseBasicParsing
    }
    Move-Item -Force $partial $dest
}

function Unpack-StarDict($archive, $dest) {
    if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
        throw "Windows tar is required to unpack dictionaries."
    }
    $scratch = Join-Path $env:TEMP ("kobo-dict-" + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Force -Path $scratch | Out-Null
    try {
        & tar -xzf $archive -C $scratch
        if ($LASTEXITCODE -ne 0) { throw "tar failed: $archive" }
        $ifos = Get-ChildItem -Path $scratch -Recurse -Filter *.ifo
        if (-not $ifos) { throw "$archive contained no StarDict .ifo files" }
        foreach ($ifo in $ifos) {
            $stem = [System.IO.Path]::GetFileNameWithoutExtension($ifo.Name)
            $target = Join-Path $dest $stem
            New-Item -ItemType Directory -Force -Path $target | Out-Null
            Get-ChildItem $ifo.Directory | ForEach-Object {
                if (-not $_.PSIsContainer) {
                    Copy-Item $_.FullName (Join-Path $target $_.Name) -Force
                } elseif ($_.Name -eq "res") {
                    Copy-Item $_.FullName (Join-Path $target "res") -Recurse -Force
                }
            }
        }
    } finally {
        Remove-Item $scratch -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Normalize-DictLangs($value) {
    $raw = ($value -replace '\s', '').ToLowerInvariant()
    switch ($raw) {
        { $_ -in @("", "skip", "none", "no", "n") } { return @() }
        { $_ -in @("both", "all", "en,ru", "ru,en") } { return @("en", "ru") }
        "en" { return @("en") }
        "ru" { return @("ru") }
        default {
            Write-Host "unknown dictionary choice: $value (use skip, en, ru, or en,ru); skipping."
            return @()
        }
    }
}

function Choose-DictLangs {
    if ($env:KOBO_SIDELOAD_DICTS) {
        return Normalize-DictLangs $env:KOBO_SIDELOAD_DICTS
    }
    Write-Host ""
    Write-Host "Dictionaries are optional (not in this zip). Long-press a word in KOReader to look it up."
    Write-Host "  skip   none now — download later in KOReader over Wi-Fi"
    Write-Host "  en     English (GCIDE)"
    Write-Host "  ru     Russian (Ushakov + Russian-English)"
    Write-Host "  en,ru  both"
    $raw = Read-Host "Download dictionaries now? [skip/en/ru/en,ru]"
    if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
    return Normalize-DictLangs $raw
}

function Install-Dicts($langs, $dest) {
    if ($null -eq $langs) { return }
    $langs = @($langs | Where-Object { $_ })
    if ($langs.Count -eq 0) { return }
    $cache = DictCacheDir
    New-Item -ItemType Directory -Force -Path $cache, $dest | Out-Null
    Write-Host ""
    Write-Host "Downloading dictionaries onto $dest ..."
    foreach ($spec in $DictCatalog) {
        $match = $false
        foreach ($lang in $spec.Langs) {
            if ($langs -contains $lang) { $match = $true }
        }
        if (-not $match) { continue }
        Write-Host "  $($spec.File)"
        $archive = Join-Path $cache $spec.File
        Download-File $spec.Url $archive
        Unpack-StarDict $archive $dest
    }
}

foreach ($rel in @(".adds\koreader\koreader.sh", ".adds\nm\koreader", ".kobo\KoboRoot.tgz")) {
    if (-not (Test-Path (Join-Path $Here $rel))) {
        Die "This folder is not a complete release (missing $rel). Unzip the whole archive first."
    }
}

$vol = Get-Disk | Where-Object BusType -eq USB | Get-Partition | Get-Volume | Where-Object FileSystemLabel -eq $Label
if ($null -eq $vol) {
    Die "No Kobo volume is mounted. Plug it in, unlock it, and wait for `"$Label`"."
}
$Mount = $vol.DriveLetter + ":\"
$KoboDir = Join-Path $Mount ".kobo"
if (-not (Test-Path $KoboDir)) {
    Die "$Mount has no .kobo directory, so it is not a Kobo in USB mode."
}

Write-Host "Kobo mount: $Mount"
Write-Host "Copying KOReader..."

$destKo = Join-Path $Mount ".adds\koreader"
New-Item -ItemType Directory -Force -Path $destKo | Out-Null
Copy-Item -Path (Join-Path $Here ".adds\koreader\*") -Destination $destKo -Recurse -Force

$destNm = Join-Path $Mount ".adds\nm"
New-Item -ItemType Directory -Force -Path $destNm | Out-Null
Copy-Item -Force (Join-Path $Here ".adds\nm\koreader") (Join-Path $destNm "koreader")
Copy-Item -Force (Join-Path $Here ".kobo\KoboRoot.tgz") (Join-Path $KoboDir "KoboRoot.tgz")

$manifest = Join-Path $Here "MANIFEST.json"
if (Test-Path $manifest) {
    Copy-Item -Force $manifest (Join-Path $Mount ".adds\kobo-sideload-manifest.json")
}

$books = Join-Path $Mount "KOReader"
New-Item -ItemType Directory -Force -Path $books | Out-Null
$booksReadme = Join-Path $Here "KOReader\README.txt"
if (Test-Path $booksReadme) {
    Copy-Item -Force $booksReadme (Join-Path $books "README.txt")
}

$confDir = Join-Path $KoboDir "Kobo"
$conf = Join-Path $confDir "Kobo eReader.conf"
New-Item -ItemType Directory -Force -Path $confDir | Out-Null
if (-not (Test-Path $conf)) { New-Item -ItemType File -Path $conf | Out-Null }
$text = Get-Content -Raw -ErrorAction SilentlyContinue $conf
if ($null -eq $text) { $text = "" }
if ($text -notlike "*$ExcludeLine*") {
    if ($text -match '(?m)^ExcludeSyncFolders=.*$') {
        $text = [regex]::Replace($text, '(?m)^ExcludeSyncFolders=.*$', $ExcludeLine)
        Set-Content -Path $conf -Value $text -NoNewline
    } else {
        Add-Content -Path $conf -Value "`r`n[FeatureSettings]`r`n$ExcludeLine`r`n"
    }
}

$destDicts = Join-Path $Mount ".adds\dictionaries"
Ensure-DictionariesFolder $destDicts
Migrate-LegacyDicts $destKo $destDicts
Ensure-StarDictLua (Join-Path $destKo "defaults.custom.lua")

if (-not (Test-Path (Join-Path $destKo "koreader.sh"))) { Die "Copy failed: koreader.sh missing on device." }
if (-not (Test-Path (Join-Path $KoboDir "KoboRoot.tgz"))) { Die "Copy failed: KoboRoot.tgz missing on device." }

Write-Host ""
Write-Host "Install complete."
Write-Host "Put FB2 and other sideloads in the KOReader folder on the USB volume."
$dictOk = $true
try {
    $dictLangs = Choose-DictLangs
    Install-Dicts $dictLangs $destDicts
} catch {
    $dictOk = $false
    Write-Host "Dictionary download failed. KOReader is installed; download later in KOReader over Wi-Fi."
    Write-Host $_
}
$ans = Read-Host "Eject the Kobo now so it can install NickelMenu? [Y/n]"
if ([string]::IsNullOrWhiteSpace($ans) -or $ans -match '^[Yy]') {
    try {
        $shell = New-Object -ComObject Shell.Application
        $item = $shell.NameSpace(17).ParseName($vol.DriveLetter + ":")
        if ($null -eq $item) { throw "volume not found" }
        $item.InvokeVerb("Eject")
        Write-Host "Ejected. Leave the cable until it reboots (it looks like a firmware update)."
    } catch {
        Write-Host "Could not eject automatically. Eject KOBOeReader in Explorer yourself."
        Write-Host $_
    }
} else {
    Write-Host "Eject KOBOeReader in Explorer when you are ready."
}
Write-Host "Then open NickelMenu on the Home screen and tap KOReader."
Read-Host "Press Enter to exit"
if (-not $dictOk) { exit 1 }
