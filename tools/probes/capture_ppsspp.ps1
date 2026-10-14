param(
  [string]$Iso = "F:\psptest\Kuon no Kizuna - Sairinshou Portable (K).iso",
  [string]$Exe = "C:\Program Files\PPSSPP\PPSSPPWindows64.exe",
  [string]$OutDir = "C:\Users\woo31\AppData\Local\Temp\opencode\ppshots"
)
$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
}
"@

New-Item -ItemType Directory -Force $OutDir | Out-Null
Get-Process PPSSPPWindows64 | Stop-Process -Force
Start-Sleep -Seconds 2
Get-ChildItem $OutDir -Filter *.png | Remove-Item -Force

Start-Process $Exe -ArgumentList "`"$Iso`""
Start-Sleep -Seconds 18

function Cap([string]$path) {
  $p = Get-Process PPSSPPWindows64 | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if (-not $p) { return "NO_WINDOW" }
  $h = $p.MainWindowHandle
  [W]::ShowWindow($h, 9) | Out-Null
  [W]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Milliseconds 700
  $cr = New-Object W+RECT
  [W]::GetClientRect($h, [ref]$cr) | Out-Null
  $pt = New-Object W+POINT; $pt.X = 0; $pt.Y = 0
  [W]::ClientToScreen($h, [ref]$pt) | Out-Null
  $w = $cr.Right - $cr.Left; $hh = $cr.Bottom - $cr.Top
  if ($w -le 0 -or $hh -le 0) { return "BAD_RECT" }
  $bmp = New-Object System.Drawing.Bitmap $w, $hh
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($pt.X, $pt.Y, 0, 0, (New-Object System.Drawing.Size $w, $hh))
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  return ("OK {0}x{1}" -f $w, $hh)
}

for ($i = 0; $i -lt 14; $i++) {
  $f = Join-Path $OutDir ("pp_{0:d2}.png" -f $i)
  $r = Cap $f
  Write-Output ("[{0}] {1} {2}" -f $i, $r, $f)
  # advance: tap X (confirm) and Space
  if ($i -ge 1) {
    [System.Windows.Forms.SendKeys]::SendWait(" ")
  }
  Start-Sleep -Seconds 3
}
Write-Output "done"
