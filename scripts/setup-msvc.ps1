param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x86', 'amd64')]
    [string]$Arch
)

$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$installation = & $vswhere -latest -version '[17.0,18.0)' -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($installation)) {
    throw 'Visual Studio 2022 with MSVC x86/x64 tools was not found'
}

$before = @{}
Get-ChildItem Env: | ForEach-Object { $before[$_.Name] = $_.Value }
$devShell = Join-Path $installation 'Common7/Tools/Launch-VsDevShell.ps1'
& $devShell -Arch $Arch -HostArch amd64 -SkipAutomaticLocation

# Preserve the developer shell's environment, including PATH order, in later CI steps.
Get-ChildItem Env: |
    Where-Object { $before[$_.Name] -cne $_.Value } |
    ForEach-Object { "$($_.Name)=$($_.Value)" } |
    Add-Content -LiteralPath $env:GITHUB_ENV -Encoding utf8
