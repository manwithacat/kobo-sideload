# Copy this release onto a USB-mounted Kobo. No Python required.
# Right-click → Run with PowerShell. If blocked: Set-ExecutionPolicy -Scope Process Bypass
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Label = "KOBOeReader"
$ExcludeLine = 'ExcludeSyncFolders=((KOReader)|\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)'
$StarDictMarker = "-- kobo-sideload dictionaries"
$StarDictLine = 'STARDICT_DATA_DIR = "/mnt/onboard/.adds/dictionaries"'

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

function Get-DictCatalog {
    $path = Join-Path $Here "dictionaries.tsv"
    $rows = @()
    if (-not (Test-Path $path)) { return $rows }
    Get-Content -Path $path -Encoding UTF8 | ForEach-Object {
        $line = $_.TrimEnd()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $p = $line -split "`t"
        if ($p.Count -lt 7) { return }
        $rows += @{
            Key = $p[0].Trim()
            Langs = @($p[1].Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
            Label = $p[2].Trim()
            Name = $p[3].Trim()
            License = $p[4].Trim()
            File = $p[5].Trim()
            Url = $p[6].Trim()
        }
    }
    return $rows
}

function CatalogLangs($catalog) {
    $seen = New-Object System.Collections.Generic.List[string]
    foreach ($spec in @($catalog)) {
        foreach ($lang in @($spec.Langs)) {
            $lang = "$lang".Trim()
            if ($lang -and -not $seen.Contains($lang)) { [void]$seen.Add($lang) }
        }
    }
    return $seen
}

function Normalize-DictLangs($value, $catalog) {
    $raw = ($value -replace '\s', '').ToLowerInvariant()
    $known = @(CatalogLangs $catalog)
    if ($raw -in @("", "skip", "none", "no", "n", "s")) { return @() }
    if ($raw -in @("both", "all", "a")) { return @($known) }
    $wanted = New-Object System.Collections.Generic.List[string]
    foreach ($part in @($raw.Split(",") | Where-Object { $_ })) {
        if ($part -match '^\d+$') {
            $idx = [int]$part
            if ($idx -lt 1 -or $idx -gt $known.Count) {
                Write-Host "choice $part is not on the list (use 1-$($known.Count), A, or S); skipping."
                return @()
            }
            $part = $known[$idx - 1]
        }
        if ($known -contains $part) {
            if (-not $wanted.Contains($part)) { [void]$wanted.Add($part) }
        } else {
            Write-Host "unknown dictionary choice: $part (use a list number, A, or S); skipping."
            return @()
        }
    }
    return @($wanted)
}

function Choose-DictLangs($catalog) {
    if ($env:KOBO_SIDELOAD_DICTS) {
        return Normalize-DictLangs $env:KOBO_SIDELOAD_DICTS $catalog
    }
    $known = @(CatalogLangs $catalog)
    Write-Host ""
    Write-Host "Dictionaries are optional (not in this zip). Long-press a word in KOReader to look it up."
    Write-Host ""
    $index = 0
    $seen = @{}
    foreach ($spec in @($catalog)) {
        foreach ($lang in @($spec.Langs)) {
            if ($lang -and -not $seen.ContainsKey($lang)) {
                $index += 1
                $seen[$lang] = $index
                Write-Host ("  {0}) {1}" -f $index, $spec.Label)
            }
            if ($lang -and $seen.ContainsKey($lang)) {
                Write-Host ("       {0}" -f $spec.Name)
            }
        }
    }
    if ($known.Count -gt 1) {
        Write-Host "  A) all of the above"
    }
    if ($known.Count -gt 0) {
        Write-Host "  S) skip — download later in KOReader over Wi-Fi"
    }
    $hint = "S"
    if ($known.Count -eq 1) { $hint = "1 or S" }
    elseif ($known.Count -gt 1) { $hint = "1-$($known.Count), A, or S" }
    $raw = Read-Host "Choose dictionaries [$hint]"
    if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
    return Normalize-DictLangs $raw $catalog
}

function Install-Dicts($langs, $dest, $catalog) {
    if ($null -eq $langs) { return }
    $langs = @($langs | Where-Object { $_ })
    if ($langs.Count -eq 0) { return }
    $cache = DictCacheDir
    New-Item -ItemType Directory -Force -Path $cache, $dest | Out-Null
    Write-Host ""
    Write-Host "Downloading dictionaries onto $dest ..."
    foreach ($spec in @($catalog)) {
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
    $dictCatalog = @(Get-DictCatalog)
    $dictLangs = Choose-DictLangs $dictCatalog
    Install-Dicts $dictLangs $destDicts $dictCatalog
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
