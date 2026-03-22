$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $PSScriptRoot "generate-plugin-index.mjs"
node $scriptPath
