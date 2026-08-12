# One-paste installer for second-brain-mcp (Windows).
# Usage: irm https://raw.githubusercontent.com/larkkkz/Agent-Second-Brain/main/install.ps1 | iex
param(
    [string]$ConfigPath = "$HOME\.claude.json",
    [string]$Vault = $(if ($env:SECOND_BRAIN_VAULT) { $env:SECOND_BRAIN_VAULT } else { "$HOME\SecondBrain" })
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/larkkkz/Agent-Second-Brain"

Write-Output "second-brain-mcp installer"
Write-Output "Config file: $ConfigPath"
Write-Output "Vault location: $Vault"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Output "uv not found - installing..."
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
}

if (Test-Path $ConfigPath) {
    $backup = "$ConfigPath.bak-secondbrain-$(Get-Date -Format yyyyMMddHHmmss)"
    Copy-Item $ConfigPath $backup -Force
    Write-Output "Backed up existing config to $backup"
    $json = Get-Content $ConfigPath -Raw | ConvertFrom-Json
} else {
    $dir = Split-Path $ConfigPath -Parent
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $json = [PSCustomObject]@{}
}

$mcpServers = @{
    "second-brain" = @{
        type    = "stdio"
        command = "uvx"
        args    = @("--from", "git+$RepoUrl", "second-brain-mcp")
        env     = @{ "SECOND_BRAIN_VAULT" = $Vault }
    }
}

if ($json.PSObject.Properties.Name -contains "mcpServers") {
    $json.PSObject.Properties.Remove("mcpServers")
}
$json | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue $mcpServers -Force

$json | ConvertTo-Json -Depth 20 | Set-Content -Encoding utf8 $ConfigPath

Write-Output ""
Write-Output "Registered 'second-brain' MCP server in $ConfigPath"
Write-Output "Restart your MCP client (e.g. Claude Code), then approve the 'second-brain' server"
Write-Output "the first time it's used (run /mcp in Claude Code to approve it)."
