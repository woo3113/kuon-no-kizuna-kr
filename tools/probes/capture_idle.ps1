param([string]$Iso, [string]$OutDir, [int]$NCap = 14, [int]$EverySec = 5)
$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W6 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
}
"@
Get-Process PPSSPPWindows64 | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process 'C:\Program Files\PPSSPP\PPSSPPWindows64.exe' -ArgumentList "`"$Iso`""
Start-Sleep -Seconds 24
New-Item -ItemType Directory -Force $OutDir | Out-Null
Get-ChildItem $OutDir -Filter *.png | Remove-Item -Force
function Cap([string]$path) {
  $p = Get-Process PPSSPPWindows64 | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if (-not $p) { return "NO_WINDOW" }
  $h = $p.MainWindowHandle
  [W6]::ShowWindow($h, 9) | Out-Null; [W6]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Milliseconds 300
  $cr = New-Object W6+RECT; [W6]::GetClientRect($h, [ref]$cr) | Out-Null
  $pt = New-Object W6+POINT; $pt.X = 0; $pt.Y = 0
  [W6]::ClientToScreen($h, [ref]$pt) | Out-Null
  $w = $cr.Right-$cr.Left; $hh = $cr.Bottom-$cr.Top
  if ($w -le 0 -or $hh -le 0) { return "BAD_RECT" }
  $bmp = New-Object System.Drawing.Bitmap $w, $hh
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($pt.X, $pt.Y, 0, 0, (New-Object System.Drawing.Size $w, $hh))
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
  return ("OK")
}
# press Space once to pick 'Start'
[System.Windows.Forms.SendKeys]::SendWait(" ")
$n = 0
for ($i = 0; $i -lt $NCap; $i++) {
  Start-Sleep -Seconds $EverySec
  $f = Join-Path $OutDir ("s_{0:d2}.png" -f $n)
  $r = Cap $f
  Write-Output ("[{0}] {1} {2}" -f $i, $r, $f)
  $n++
}
Write-Output "done"
