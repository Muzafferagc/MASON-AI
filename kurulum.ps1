# kurulum.ps1 - MASON'u bir kez kurar:
#   * Masaustune "MASON Ac" ve "MASON Kapat" simgeleri ekler
#   * Windows acilisina (Startup) MASON'u ekler (gizli, arka planda)
#   * MASON'u hemen arka planda baslatir ("hey mason" hazir)
# Gercek Python'u bulur; Microsoft Store yer tutucusunu (stub) atlar.

$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms | Out-Null

$proj = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Msg($text, $title) {
    [System.Windows.Forms.MessageBox]::Show($text, $title) | Out-Null
}

# --- Gercek pythonw.exe'yi bul (WindowsApps stub'larini ele) ---
function Find-Pythonw {
    # 1) PATH'teki pythonw.exe adaylari (WindowsApps haric)
    foreach ($c in (Get-Command pythonw.exe -All -ErrorAction SilentlyContinue)) {
        if ($c.Source -and $c.Source -notlike '*WindowsApps*') { return $c.Source }
    }
    # 2) py launcher ile gercek yorumlayici
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $exe = & $py.Source -3 -c "import sys;print(sys.executable)" 2>$null
        if ($exe) {
            $pw = Join-Path (Split-Path $exe) 'pythonw.exe'
            if (Test-Path $pw) { return $pw }
        }
    }
    # 3) yaygin kurulum konumlari
    $globs = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python*\pythonw.exe'),
        (Join-Path $env:ProgramFiles 'Python*\pythonw.exe'),
        'C:\Python*\pythonw.exe'
    )
    foreach ($g in $globs) {
        $f = Get-ChildItem $g -ErrorAction SilentlyContinue |
             Sort-Object FullName -Descending | Select-Object -First 1
        if ($f) { return $f.FullName }
    }
    return $null
}

$pyw = Find-Pythonw
if (-not $pyw) {
    Show-Msg "Gercek Python bulunamadi. Lutfen python.org'dan Python kurun (kurulumda 'Add to PATH' isaretli) ve tekrar deneyin." "MASON Kurulum - HATA"
    exit 1
}

$runpy  = Join-Path $proj 'run.py'
$stoppy = Join-Path $proj 'mason_kapat.py'

$w = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$startup = [Environment]::GetFolderPath('Startup')

function New-Shortcut($linkPath, $target, $arguments, $workdir) {
    $s = $w.CreateShortcut($linkPath)
    $s.TargetPath = $target
    $s.Arguments = $arguments
    $s.WorkingDirectory = $workdir
    $s.WindowStyle = 7   # simge durumunda (goze batmasin)
    $s.Save()
}

# Masaustu: MASON Ac (pencereyi getirir; calisiyorsa one alir)
New-Shortcut (Join-Path $desktop 'MASON Ac.lnk')    $pyw ('"' + $runpy  + '" --show') $proj
# Masaustu: MASON Kapat (tamamen kapatir)
New-Shortcut (Join-Path $desktop 'MASON Kapat.lnk') $pyw ('"' + $stoppy + '"')        $proj
# Windows acilisi: gizli, arka planda dinleme
New-Shortcut (Join-Path $startup 'MASON.lnk')       $pyw ('"' + $runpy  + '"')        $proj

# Simdi hemen baslat (arka planda, gizli)
Start-Process -FilePath $pyw -ArgumentList ('"' + $runpy + '"') -WorkingDirectory $proj

Show-Msg ("Kurulum tamamlandi." + [Environment]::NewLine +
          "Kullanilan Python: " + $pyw + [Environment]::NewLine + [Environment]::NewLine +
          "MASON arka planda calisiyor. Artik 'hey mason' diyebilirsiniz." + [Environment]::NewLine +
          "Masaustunde 'MASON Ac' ve 'MASON Kapat' simgeleri olusturuldu.") "MASON Kurulum"
