# Digital Life Command Center :: real Coral setup (Windows / PowerShell)
# Run after installing coral.exe (see README). Connects the 3 sources and
# bridges Coral to your agent over MCP. Requires your account logins.

Write-Host "1) Checking coral CLI..." -ForegroundColor Cyan
if (-not (Get-Command coral -ErrorAction SilentlyContinue)) {
  Write-Host "coral.exe not on PATH. Download the Windows zip from" -ForegroundColor Yellow
  Write-Host "https://github.com/withcoral/coral/releases and add it to PATH." -ForegroundColor Yellow
  exit 1
}
coral --version

Write-Host "2) Connecting bundled sources (browser OAuth opens)..." -ForegroundColor Cyan
coral source add --interactive notion
coral source add --interactive google-calendar

Write-Host "3) Adding Todoist (community spec)..." -ForegroundColor Cyan
if (-not (Test-Path ".\coral")) { git clone https://github.com/withcoral/coral }
coral source add --file .\coral\sources\community\todoist\manifest.yaml --interactive

Write-Host "4) Verifying schema..." -ForegroundColor Cyan
coral sql "SELECT schema_name, table_name FROM coral.tables ORDER BY 1,2"

Write-Host "5) Bridging Coral to Claude Code over MCP..." -ForegroundColor Cyan
claude mcp add --scope user coral -- coral mcp-stdio

Write-Host "6) Installing discovery-first skills..." -ForegroundColor Cyan
npx skills add withcoral/skills

Write-Host "Done. Ask your agent: 'list the tables available in Coral'." -ForegroundColor Green
