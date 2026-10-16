# Capture Flatten To XML output and Unflatten From XML readings from a real LabVIEW.
#
# Drives shipped VIs that flatten or unflatten a fixed data type through XML files, through
# LabVIEW's ActiveX VI Server. Jobs come from a JSON file (see scripts/make_labview_jobs.py):
#   save: set a control of a VI that writes an XML file, run it, copy the file LabVIEW wrote.
#   load: put an input file where a VI reads its XML, run it, record the indicator values.
# Every file a job touches is backed up first and restored (or removed) at the end, and every
# VI is hashed before and after: nothing is saved back.
#
#   pwsh scripts/capture-labview-xml.ps1 -Jobs jobs.json -OutDir tests/fixtures/labview2026
#
# The script starts its own LabVIEW and closes exactly that process afterwards, so it refuses
# to run while another LabVIEW is open.
param(
    [Parameter(Mandatory = $true)][string]$Jobs,
    [Parameter(Mandatory = $true)][string]$OutDir
)
$ErrorActionPreference = "Stop"
$BF = [System.Reflection.BindingFlags]
$CO = [System.__ComObject]
function Invoke-Com($obj, [string]$name, [object[]]$argv) {
    return $CO.InvokeMember($name, $BF::InvokeMethod, $null, $obj, $argv)
}
function Get-ComProperty($obj, [string]$name) {
    return $CO.InvokeMember($name, $BF::GetProperty, $null, $obj, $null)
}

# JSON values are tagged: {"t": "str"|"bool"|"u16"|"i32"|"cluster", "v": ...}.
function ConvertTo-Com($node) {
    switch ($node.t) {
        "str" { return [string]$node.v }
        "bool" { return [bool]$node.v }
        "u16" { return [uint16]$node.v }
        "i32" { return [int32]$node.v }
        # The leading comma stops PowerShell from unrolling the array into its caller.
        "cluster" { return , [object[]]@($node.v | ForEach-Object { , (ConvertTo-Com $_) }) }
    }
    throw "unknown value tag $($node.t)"
}

$list = Get-Content -Raw -Encoding utf8 $Jobs | ConvertFrom-Json
foreach ($job in $list) { $job.file = [Environment]::ExpandEnvironmentVariables($job.file) }
$OutDir = (Resolve-Path $OutDir).Path
$inputs = Split-Path -Parent (Resolve-Path $Jobs).Path
$backups = @{}
$hashes = @{}
foreach ($job in $list) {
    if (-not $hashes.ContainsKey($job.vi)) { $hashes[$job.vi] = (Get-FileHash $job.vi).Hash }
    if (-not $backups.ContainsKey($job.file)) {
        $backups[$job.file] = if (Test-Path $job.file) { [IO.File]::ReadAllBytes($job.file) } else { $null }
    }
}

if (Get-Process -Name "LabVIEW" -ErrorAction SilentlyContinue) {
    throw "LabVIEW is already running; close it first"
}
$app = [Activator]::CreateInstance([Type]::GetTypeFromProgID("LabVIEW.Application"))
$started = @(Get-Process -Name "LabVIEW" -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
try {
    "LabVIEW " + (Get-ComProperty $app "Version")
    foreach ($job in $list) {
        $vi = Invoke-Com $app "GetVIReference" @([string]$job.vi, "", $false, 0)
        if ($job.kind -eq "save") {
            Invoke-Com $vi "SetControlValue" @([string]$job.control, (ConvertTo-Com $job.value)) | Out-Null
        } else {
            Copy-Item -LiteralPath (Join-Path $inputs $job.input) -Destination $job.file -Force
        }
        Invoke-Com $vi "Run" @($true) | Out-Null
        $deadline = (Get-Date).AddSeconds(20)
        # ExecState 1 is idle: the run has finished.
        while ((Get-ComProperty $vi "ExecState") -ne 1 -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 200
        }
        $result = [ordered]@{ job = $job.name; finished = ((Get-ComProperty $vi "ExecState") -eq 1) }
        if (-not $result.finished) { Invoke-Com $vi "Abort" @() | Out-Null }
        $target = Join-Path $OutDir $job.out
        if ($job.kind -eq "save") {
            Copy-Item -LiteralPath $job.file -Destination $target -Force
            "saved $($job.name)"
            continue
        }
        foreach ($name in $job.outputs) {
            $result[$name] = Invoke-Com $vi "GetControlValue" @([string]$name)
        }
        $json = $result | ConvertTo-Json -Depth 8
        [IO.File]::WriteAllText($target, $json + "`n", [Text.UTF8Encoding]::new($false))
        "loaded $($job.name)"
    }
} finally {
    try { Invoke-Com $app "Quit" @() | Out-Null } catch { }
    # Quit does not always end the process; close the LabVIEW this script started, and only it.
    Start-Sleep -Seconds 5
    foreach ($id in $started) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    foreach ($file in $backups.Keys) {
        if ($null -eq $backups[$file]) { Remove-Item -LiteralPath $file -ErrorAction SilentlyContinue }
        else { [IO.File]::WriteAllBytes($file, $backups[$file]) }
    }
}
foreach ($vi in $hashes.Keys) {
    if ((Get-FileHash $vi).Hash -ne $hashes[$vi]) { throw "$vi changed on disk" }
}
"every VI is unchanged and every touched file is restored"
