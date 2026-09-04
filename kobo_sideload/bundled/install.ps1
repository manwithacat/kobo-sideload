# Copy this release onto a USB-mounted Kobo. No Python required.
# Right-click → Run with PowerShell. If blocked: Set-ExecutionPolicy -Scope Process Bypass
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Label = "KOBOeReader"
$ExcludeLine = 'ExcludeSyncFolders=((KOReader)|\\.(?!kobo|adobe).+|([^.][^/]*/)+\\..+)'

function Die($msg) {
    Write-Host "error: $msg"
    Read-Host "Press Enter to exit"
    exit 1
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
if (Test-Path $destKo) { Remove-Item $destKo -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $Mount ".adds") | Out-Null
Copy-Item -Recurse -Force (Join-Path $Here ".adds\koreader") $destKo

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

if (-not (Test-Path (Join-Path $destKo "koreader.sh"))) { Die "Copy failed: koreader.sh missing on device." }
if (-not (Test-Path (Join-Path $KoboDir "KoboRoot.tgz"))) { Die "Copy failed: KoboRoot.tgz missing on device." }

Write-Host ""
Write-Host "Install complete."
Write-Host "Put FB2 and other sideloads in the KOReader folder on the USB volume."
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
