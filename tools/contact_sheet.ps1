# Put several frame PNGs into one labelled grid image (for looking at a view switch frame by frame).
# Usage: powershell -File tools\contact_sheet.ps1 -Dir <frames dir> -From <idx> -To <idx> [-Step 1] [-Cols 6] -Out <png>
param([Parameter(Mandatory = $true)][string]$Dir, [Parameter(Mandatory = $true)][int]$From,
      [Parameter(Mandatory = $true)][int]$To, [int]$Step = 1, [int]$Cols = 6, [Parameter(Mandatory = $true)][string]$Out)
Add-Type -AssemblyName System.Drawing
$files = @()
for ($i = $From; $i -le $To; $i += $Step) {
  $f = Join-Path $Dir ("f{0:D5}.png" -f $i)
  if (Test-Path $f) { $files += , @($i, $f) }
}
if ($files.Count -eq 0) { throw "no frames in range" }
$first = [System.Drawing.Image]::FromFile($files[0][1]); $w = $first.Width; $h = $first.Height; $first.Dispose()
$rows = [math]::Ceiling($files.Count / $Cols)
$sheet = New-Object System.Drawing.Bitmap ($Cols * $w), ($rows * $h)
$g = [System.Drawing.Graphics]::FromImage($sheet)
$g.Clear([System.Drawing.Color]::Black)
$font = New-Object System.Drawing.Font "Arial", 9
for ($k = 0; $k -lt $files.Count; $k++) {
  $img = [System.Drawing.Image]::FromFile($files[$k][1])
  $x = ($k % $Cols) * $w; $y = [math]::Floor($k / $Cols) * $h
  $g.DrawImage($img, $x, $y, $w, $h); $img.Dispose()
  $g.FillRectangle([System.Drawing.Brushes]::Black, $x, $y, 34, 13)
  $g.DrawString([string]$files[$k][0], $font, [System.Drawing.Brushes]::Yellow, $x + 1, $y)
  $g.DrawRectangle([System.Drawing.Pens]::Gray, $x, $y, $w - 1, $h - 1)
}
$sheet.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $sheet.Dispose()
"$Out $($files.Count) frames"
