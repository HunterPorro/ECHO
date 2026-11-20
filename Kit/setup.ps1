<#
.SYNOPSIS
  ECHO - one-shot Unreal Engine 5.5+ project builder for the Prologue gala ("The Unveiling").

.DESCRIPTION
  1. Finds an Unreal Engine 5.5+ install (Epic launcher registry / LauncherInstalled.dat / default paths).
  2. Creates the ECHO Blueprint-only project from this kit (uproject + Config + Content/Python).
  3. Copies Epic's Third Person template content (Manny/Quinn, BP_ThirdPersonCharacter/GameMode, input)
     from the engine install so the level is walkable and the crowd uses real mannequins.
  4. Tunes the editor's scalability for the Radeon 880M (backs up the old file).
  5. Runs the Python build headlessly: UnrealEditor-Cmd.exe -ExecutePythonScript=...echo_build_all.py
  6. Optional: renders the opening shot with Movie Render Queue (-Render) and encodes an MP4 if ffmpeg exists.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Render -Preset Draft
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipBuild -Render -Preset Final
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Stages "level,sequence" -Open

  Timeline Ripple tech demo (L_Riverside_Ripple + LS_Ripple_Demo; never touched by the default 'all'):
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -Stages ripple
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Render -Preset Draft -Target Ripple
  (-Target is inferred as Ripple when -Stages mentions ripple and -Target isn't given)

  Trial 1 vertical slice (L_Trial1_Riverside2008 + LS_Trial1_Flythrough + LS_Trial1_Shift; never part of 'all'):
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -Stages trial1
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Render -Preset Draft -Target Trial1
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -SkipTemplate -SkipBuild -Open -Target Trial1   (then Play)
  (-Target is inferred as Trial1 when -Stages mentions trial1 and -Target isn't given)
#>
[CmdletBinding()]
param(
    [string]$ProjectDir = "C:\UnrealProjects\ECHO",
    [string]$EngineDir = "",
    [string]$Stages = "all",
    [switch]$Render,
    [ValidateSet("Draft", "Final")][string]$Preset = "Draft",
    [ValidateSet("Gala", "Ripple", "Trial1")][string]$Target = "Gala",
    [switch]$RenderInEditor,
    [switch]$NullRHI,
    [switch]$SkipBuild,
    [switch]$SkipTemplate,
    [switch]$SkipEditorScalability,
    [switch]$Force,
    [switch]$Open,
    [int]$TimeoutMinutes = 240
)

$ErrorActionPreference = "Stop"
if (-not $PSBoundParameters.ContainsKey("Target") -and $Stages -match "ripple") { $Target = "Ripple" }
if (-not $PSBoundParameters.ContainsKey("Target") -and $Stages -match "trial1") { $Target = "Trial1" }
if ($Target -eq "Trial1") {
    $TMap = "/Game/ECHO/Maps/L_Trial1_Riverside2008"
    $TSeqName = "LS_Trial1_Flythrough"
    $TPresetPrefix = "MRQ_Trial1_1080p_"
    $TOutSub = "Trial1_Flythrough"
    $TRenderStage = "trial1_render"
} elseif ($Target -eq "Ripple") {
    $TMap = "/Game/ECHO/Maps/L_Riverside_Ripple"
    $TSeqName = "LS_Ripple_Demo"
    $TPresetPrefix = "MRQ_Ripple_1080p_"
    $TOutSub = "Ripple_Demo"
    $TRenderStage = "ripple_render"
} else {
    $TMap = "/Game/ECHO/Maps/L_Prologue_Gala"
    $TSeqName = "LS_Prologue_Unveiling"
    $TPresetPrefix = "MRQ_Gala_1080p_"
    $TOutSub = "Prologue_Unveiling"
    $TRenderStage = "render"
}
$KitDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KitProject = Join-Path $KitDir "ECHO"

function Say($msg, $color = "Cyan") { Write-Host "[ECHO] $msg" -ForegroundColor $color }
function Fail($msg) { Write-Host "[ECHO] ERROR: $msg" -ForegroundColor Red; exit 1 }

# ------------------------------------------------------------------ 1. find Unreal Engine
function Get-EngineVersion($dir) {
    $bv = Join-Path $dir "Engine\Build\Build.version"
    if (-not (Test-Path $bv)) { return $null }
    try { $j = Get-Content $bv -Raw | ConvertFrom-Json; return [version]("{0}.{1}.{2}" -f $j.MajorVersion, $j.MinorVersion, $j.PatchVersion) }
    catch { return $null }
}

function Find-Engine {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($EngineDir) { $candidates.Add($EngineDir) }
    foreach ($root in @("HKLM:\SOFTWARE\EpicGames\Unreal Engine", "HKLM:\SOFTWARE\WOW6432Node\EpicGames\Unreal Engine")) {
        if (Test-Path $root) {
            Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object {
                $p = (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).InstalledDirectory
                if ($p) { $candidates.Add($p) }
            }
        }
    }
    $dat = Join-Path $env:ProgramData "Epic\UnrealEngineLauncher\LauncherInstalled.dat"
    if (Test-Path $dat) {
        try {
            (Get-Content $dat -Raw | ConvertFrom-Json).InstallationList | Where-Object { $_.AppName -like "UE_*" } |
                ForEach-Object { $candidates.Add($_.InstallLocation) }
        } catch { }
    }
    foreach ($pf in @($env:ProgramFiles, "D:\Program Files", "D:\Epic Games", "E:\Epic Games")) {
        if ($pf -and (Test-Path $pf -ErrorAction SilentlyContinue) -and (Test-Path (Join-Path $pf "Epic Games"))) {
            Get-ChildItem (Join-Path $pf "Epic Games") -Directory -Filter "UE_5.*" -ErrorAction SilentlyContinue |
                ForEach-Object { $candidates.Add($_.FullName) }
        }
        if ($pf -and (Split-Path $pf -Leaf) -eq "Epic Games" -and (Test-Path $pf -ErrorAction SilentlyContinue)) {
            Get-ChildItem $pf -Directory -Filter "UE_5.*" -ErrorAction SilentlyContinue | ForEach-Object { $candidates.Add($_.FullName) }
        }
    }
    $best = $null; $bestVer = [version]"0.0.0"
    foreach ($c in ($candidates | Select-Object -Unique)) {
        $exe = Join-Path $c "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
        if (-not (Test-Path $exe)) { continue }
        $v = Get-EngineVersion $c
        if ($v -and $v -ge [version]"5.5.0" -and $v -gt $bestVer) { $best = $c; $bestVer = $v }
    }
    if (-not $best) { return $null }
    return @{ Dir = $best; Version = $bestVer }
}

$engine = Find-Engine
if (-not $engine) { Fail "No Unreal Engine 5.5+ found. Install it from the Epic Games Launcher (Unreal Engine tab > Library > +), or pass -EngineDir 'C:\Program Files\Epic Games\UE_5.5'." }
$UE = $engine.Dir
$UEVer = $engine.Version
$EditorCmd = Join-Path $UE "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$Editor = Join-Path $UE "Engine\Binaries\Win64\UnrealEditor.exe"
Say "Unreal Engine $UEVer at $UE" "Green"

# ------------------------------------------------------------------ 2. create / update the project
$UProject = Join-Path $ProjectDir "ECHO.uproject"
$fresh = -not (Test-Path $UProject)
if ($fresh -or $Force) {
    Say "creating project at $ProjectDir"
    New-Item -ItemType Directory -Force -Path $ProjectDir | Out-Null
    Copy-Item -Path (Join-Path $KitProject "*") -Destination $ProjectDir -Recurse -Force
} else {
    Say "project exists - refreshing Config and Content/Python from the kit (assets untouched)"
    Copy-Item -Path (Join-Path $KitProject "Config\*") -Destination (Join-Path $ProjectDir "Config") -Recurse -Force
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir "Content\Python") | Out-Null
    Copy-Item -Path (Join-Path $KitProject "Content\Python\*") -Destination (Join-Path $ProjectDir "Content\Python") -Recurse -Force
}
# point the project at the installed engine version (launcher builds use "5.5", "5.6", ...)
$assoc = "{0}.{1}" -f $UEVer.Major, $UEVer.Minor
$up = Get-Content $UProject -Raw | ConvertFrom-Json
$up.EngineAssociation = $assoc
($up | ConvertTo-Json -Depth 8) | Set-Content -Path $UProject -Encoding UTF8
Say "EngineAssociation = $assoc"

# ------------------------------------------------------------------ 3. Third Person template content
function Copy-Pack($src, $dst) {
    if (-not (Test-Path $src)) { return $false }
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    # /XC /XN /XO = keep files that already exist in the project
    $null = robocopy $src $dst /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP
    return $true
}
if (-not $SkipTemplate) {
    $tpl = Join-Path $UE "Templates\TP_ThirdPersonBP"
    $content = Join-Path $ProjectDir "Content"
    if (Copy-Pack (Join-Path $tpl "Content") $content) { Say "copied TP_ThirdPersonBP content" } else { Say "TP_ThirdPersonBP not found under $UE\Templates - crowd falls back to capsules" "Yellow" }
    $mounts = @()
    $defs = Join-Path $tpl "Config\TemplateDefs.ini"
    if (Test-Path $defs) {
        $mounts = Select-String -Path $defs -Pattern 'MountName="?([A-Za-z0-9_]+)"?' -AllMatches |
            ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique
    }
    if (-not $mounts -or $mounts.Count -eq 0) { $mounts = @("Characters", "Input", "LevelPrototyping") }
    foreach ($m in $mounts) {
        foreach ($detail in @("High", "Low")) {
            $src = Join-Path $UE ("Templates\TemplateResources\{0}\{1}\Content" -f $detail, $m)
            if (Copy-Pack $src (Join-Path $content $m)) { Say "copied shared pack $m ($detail)"; break }
        }
    }
    # wire the game mode path into DefaultEngine.ini wherever the template put it
    $gm = Get-ChildItem -Path $content -Recurse -Filter "BP_ThirdPersonGameMode.uasset" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gm) {
        $rel = $gm.FullName.Substring($content.Length).TrimStart('\').Replace('\', '/').Replace('.uasset', '')
        $name = [IO.Path]::GetFileNameWithoutExtension($gm.Name)
        $line = "GlobalDefaultGameMode=/Game/$rel.${name}_C"
        $ini = Join-Path $ProjectDir "Config\DefaultEngine.ini"
        (Get-Content $ini) -replace '^GlobalDefaultGameMode=.*$', $line | Set-Content $ini -Encoding UTF8
        Say "game mode: /Game/$rel"
    }
}

# ------------------------------------------------------------------ 4. editor scalability for the Radeon 880M
if (-not $SkipEditorScalability) {
    $cfgDir = Join-Path $env:LOCALAPPDATA ("UnrealEngine\{0}\Saved\Config\WindowsEditor" -f $assoc)
    New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
    $es = Join-Path $cfgDir "EditorSettings.ini"
    $groups = [ordered]@{
        "sg.ResolutionQuality" = "75"; "sg.ViewDistanceQuality" = "2"; "sg.AntiAliasingQuality" = "2";
        "sg.ShadowQuality" = "2"; "sg.GlobalIlluminationQuality" = "2"; "sg.ReflectionQuality" = "2";
        "sg.PostProcessQuality" = "2"; "sg.TextureQuality" = "2"; "sg.EffectsQuality" = "2";
        "sg.FoliageQuality" = "1"; "sg.ShadingQuality" = "2"; "sg.LandscapeQuality" = "2"
    }
    $lines = @()
    if (Test-Path $es) {
        Copy-Item $es "$es.echo-backup" -Force
        $lines = Get-Content $es
        # drop the old [ScalabilityGroups] block
        $out = @(); $skip = $false
        foreach ($l in $lines) {
            if ($l -match '^\[ScalabilityGroups\]') { $skip = $true; continue }
            if ($skip -and $l -match '^\[') { $skip = $false }
            if (-not $skip) { $out += $l }
        }
        $lines = $out
    }
    $lines += "[ScalabilityGroups]"
    foreach ($k in $groups.Keys) { $lines += "$k=$($groups[$k])" }
    $lines += ""
    $lines | Set-Content $es -Encoding UTF8
    Say "editor scalability set to High (75% res) for UE $assoc - backup at $es.echo-backup"
}

# ------------------------------------------------------------------ 5. run the Python build headlessly
function Invoke-UE($exe, $argString, $label) {
    Say "$label`n    $exe $argString" "Gray"
    $p = Start-Process -FilePath $exe -ArgumentList $argString -PassThru -NoNewWindow
    if (-not $p.WaitForExit($TimeoutMinutes * 60 * 1000)) {
        try { $p.Kill() } catch { }
        Fail "$label timed out after $TimeoutMinutes min (first launch compiles thousands of shaders; re-run with a bigger -TimeoutMinutes)"
    }
    return $p.ExitCode
}

$script = (Join-Path $ProjectDir "Content\Python\echo_build_all.py")
if ($script -match ' ') {
    # -ExecutePythonScript splits on spaces; stage a launcher on a space-free path (echo_kit is
    # still imported from the project's Content/Python, which Unreal adds to sys.path)
    $launchDir = Join-Path $env:SystemDrive "UnrealProjects\_echo_launch"
    New-Item -ItemType Directory -Force -Path $launchDir | Out-Null
    Copy-Item $script (Join-Path $launchDir "echo_build_all.py") -Force
    $script = Join-Path $launchDir "echo_build_all.py"
}
$scriptFwd = $script.Replace('\', '/')
$common = "-unattended -nosplash -nopause -stdout -FullStdOutLogOutput -NoSound"
if ($NullRHI) { $common += " -nullrhi" }

if (-not $SkipBuild) {
    $env:ECHO_STAGES = $Stages
    $env:ECHO_QUIT = "1"
    $env:ECHO_RENDER = ""
    Remove-Item (Join-Path $ProjectDir "Saved\ECHO_build_status.txt") -ErrorAction SilentlyContinue
    $code = Invoke-UE $EditorCmd ("`"$UProject`" -ExecutePythonScript=`"$scriptFwd`" $common") "building ECHO (stages: $Stages) - first run can take 30-90 min of shader compiling"
    $status = Join-Path $ProjectDir "Saved\ECHO_build_status.txt"
    if (Test-Path $status) {
        $s = Get-Content $status
        if ($s[0] -eq "OK") { Say "build OK" "Green" } else { Say "build finished with failures:`n$($s -join "`n")" "Yellow" }
    } else {
        Say "no status file - the Python build may not have run. Check $ProjectDir\Saved\Logs\ECHO.log and ECHO_build.log" "Yellow"
    }
    Say "editor exit code $code"
}

# ------------------------------------------------------------------ 6. render
if ($RenderInEditor) {
    $env:ECHO_STAGES = $TRenderStage
    $env:ECHO_QUIT = "1"
    $env:ECHO_RENDER = "editor"
    $env:ECHO_RENDER_TARGET = $Target.ToLower()
    $env:ECHO_RENDER_PRESET = "$TPresetPrefix$Preset"
    $code = Invoke-UE $EditorCmd ("`"$UProject`" -ExecutePythonScript=`"$scriptFwd`" -unattended -nosplash -nopause -stdout") "rendering in-editor (PIE executor, $Preset)"
    $env:ECHO_RENDER = ""
}
if ($Render) {
    $presetName = "$TPresetPrefix$Preset"
    $map = $TMap
    $seq = "/Game/ECHO/Cinematics/$TSeqName.$TSeqName"
    $cfg = "/Game/ECHO/Cinematics/$presetName.$presetName"
    $renderArgs = "`"$UProject`" $map -game -LevelSequence=`"$seq`" -MoviePipelineConfig=`"$cfg`" -windowed -resx=1280 -resy=720 -log -stdout -unattended -nosplash -NoLoadingScreen -NoTextureStreaming -NoSound"
    $code = Invoke-UE $Editor $renderArgs "rendering $presetName (1080p PNG frames)"
    $outDir = Join-Path $ProjectDir "Saved\MovieRenders\$TOutSub"
    $frames = @(Get-ChildItem $outDir -Filter "*.png" -ErrorAction SilentlyContinue)
    Say ("render exit code {0}; {1} frames in {2}" -f $code, $frames.Count, $outDir)
    $ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ff -and $frames.Count -gt 0) {
        $mp4 = Join-Path $outDir ("ECHO_{0}_{1}.mp4" -f $TOutSub, $Preset)
        & $ff.Source -y -framerate 24 -i (Join-Path $outDir "$TSeqName.%04d.png") -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow $mp4
        Say "MP4: $mp4" "Green"
    } elseif ($frames.Count -gt 0) {
        Say "ffmpeg not on PATH - frames left as PNG (winget install Gyan.FFmpeg to get MP4s)" "Yellow"
    }
}

if ($Open) {
    Say "opening the editor"
    if ($Target -eq "Ripple" -or $Target -eq "Trial1") { Start-Process -FilePath $Editor -ArgumentList "`"$UProject`" $TMap" }
    else { Start-Process -FilePath $Editor -ArgumentList "`"$UProject`"" }
}
Say "done. Project: $UProject" "Green"
