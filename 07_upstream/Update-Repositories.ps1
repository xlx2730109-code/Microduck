[CmdletBinding()]
param(
    [string]$Repository,
    [switch]$ListOnly
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$rootPath = [IO.Path]::GetFullPath($PSScriptRoot)
$found = @()
$failed = @()

Get-Command git -ErrorAction Stop | Out-Null

foreach ($owner in (Get-ChildItem -LiteralPath $rootPath -Directory | Sort-Object Name)) {
    if ($owner.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
    foreach ($repo in (Get-ChildItem -LiteralPath $owner.FullName -Directory | Sort-Object Name)) {
        if ($repo.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        if (-not (Test-Path -LiteralPath (Join-Path $repo.FullName '.git'))) { continue }
        $repoName = $owner.Name + '/' + $repo.Name
        if ($Repository -and $Repository -ne $repoName) { continue }
        $found += $repoName
        try {
            $gitRoot = @(git -C $repo.FullName rev-parse --show-toplevel)
            if ($LASTEXITCODE -ne 0 -or $gitRoot.Count -ne 1) { throw 'Cannot identify repository root.' }
            if ([IO.Path]::GetFullPath($gitRoot[0]) -ne $repo.FullName) { throw 'Repository root differs from selected directory.' }
            $remote = @(git -C $repo.FullName remote get-url origin)
            if ($LASTEXITCODE -ne 0 -or $remote.Count -ne 1) { throw 'Missing origin remote.' }
            $expectedRemote = 'https://github.com/' + $repoName
            $actualRemote = $remote[0].TrimEnd('/')
            if ($actualRemote -ne $expectedRemote -and $actualRemote -ne ($expectedRemote + '.git')) {
                throw 'Origin does not match the owner/repository directory name.'
            }
            $commit = @(git -C $repo.FullName rev-parse --short HEAD)
            if ($LASTEXITCODE -ne 0) { throw 'No checked-out commit. Finish repository setup first.' }
            if ($ListOnly) {
                Write-Output ($repoName + '  ' + $commit[0] + '  ' + $repo.FullName)
                continue
            }
            $changes = @(git -C $repo.FullName status --porcelain=v1 --untracked-files=normal)
            if ($LASTEXITCODE -ne 0) { throw 'Cannot read working-tree status.' }
            if ($changes.Count -gt 0) { throw 'Local changes found. Preserve and review them before updating.' }
            $tracking = @(git -C $repo.FullName rev-parse --abbrev-ref '@{upstream}')
            if ($LASTEXITCODE -ne 0 -or $tracking.Count -ne 1) { throw 'No tracking branch configured.' }
            Write-Output ('Updating ' + $repoName + ' from ' + $commit[0])
            git -C $repo.FullName pull --ff-only
            if ($LASTEXITCODE -ne 0) { throw 'Pull failed. No reset, clean, stash, or merge was attempted by this script.' }
            git -C $repo.FullName log -1 --format='%h %cs %s'
            if ($LASTEXITCODE -ne 0) { throw 'Cannot read updated commit.' }
        }
        catch {
            $failed += $repoName
            Write-Warning ($repoName + ': ' + $_.Exception.Message)
        }
    }
}

if ($found.Count -eq 0) { throw 'No matching Git repository found under author/repository directories.' }
if ($failed.Count -gt 0) { throw ('Unfinished repositories: ' + ($failed -join ', ')) }
