# Generates plugin-src\icon.png (1024x1024 square PNG): a document with the Hebrew letter Lamed (ל) on a blue rounded square.
Add-Type -AssemblyName System.Drawing
$size = 1024
$bmp = New-Object System.Drawing.Bitmap $size, $size
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAliasGridFit'; $g.Clear([System.Drawing.Color]::Transparent)
function RoundRect($x, $y, $w, $h, $r) {
  $p = New-Object System.Drawing.Drawing2D.GraphicsPath
  $p.AddArc($x, $y, $r * 2, $r * 2, 180, 90); $p.AddArc($x + $w - $r * 2, $y, $r * 2, $r * 2, 270, 90)
  $p.AddArc($x + $w - $r * 2, $y + $h - $r * 2, $r * 2, $r * 2, 0, 90); $p.AddArc($x, $y + $h - $r * 2, $r * 2, $r * 2, 90, 90); $p.CloseFigure(); $p
}
# background
$bgRect = New-Object System.Drawing.Rectangle 0, 0, $size, $size
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush $bgRect, ([System.Drawing.Color]::FromArgb(255, 44, 110, 166)), ([System.Drawing.Color]::FromArgb(255, 22, 59, 94)), 55
$g.FillPath($bg, (RoundRect 0 0 $size $size 200))
# page with folded corner
$px = 262; $py = 170; $pw = 500; $ph = 684; $fold = 140
$page = New-Object System.Drawing.Drawing2D.GraphicsPath
$page.AddPolygon([System.Drawing.Point[]]@(
  (New-Object System.Drawing.Point $px, $py), (New-Object System.Drawing.Point ($px + $pw - $fold), $py), (New-Object System.Drawing.Point ($px + $pw), ($py + $fold)),
  (New-Object System.Drawing.Point ($px + $pw), ($py + $ph)), (New-Object System.Drawing.Point $px, ($py + $ph))))
$g.FillPath([System.Drawing.Brushes]::White, $page)
$foldPts = [System.Drawing.Point[]]@((New-Object System.Drawing.Point ($px + $pw - $fold), $py), (New-Object System.Drawing.Point ($px + $pw - $fold), ($py + $fold)), (New-Object System.Drawing.Point ($px + $pw), ($py + $fold)))
$g.FillPolygon((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 205, 220, 235))), $foldPts)
# text lines
$line = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 200, 212, 226))
$g.FillPath($line, (RoundRect ($px + 60) ($py + 90) 250 26 13)); $g.FillPath($line, (RoundRect ($px + 60) ($py + 150) 330 26 13)); $g.FillPath($line, (RoundRect ($px + 60) ($py + 210) 290 26 13))
# the letter Lamed
$font = New-Object System.Drawing.Font 'Arial', 330, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fmt = New-Object System.Drawing.StringFormat; $fmt.Alignment = 'Center'; $fmt.LineAlignment = 'Center'
$g.DrawString([string][char]0x05DC, $font, (New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 31, 78, 121))), (New-Object System.Drawing.RectangleF $px, ($py + 250), $pw, 400), $fmt)
# gold "verified" badge
$cx = 760; $cy = 790; $r = 130
$g.FillEllipse((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 242, 169, 0))), ($cx - $r), ($cy - $r), ($r * 2), ($r * 2))
$pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 34; $pen.StartCap = 'Round'; $pen.EndCap = 'Round'; $pen.LineJoin = 'Round'
$g.DrawLines($pen, [System.Drawing.Point[]]@((New-Object System.Drawing.Point ($cx - 62), ($cy + 6)), (New-Object System.Drawing.Point ($cx - 14), ($cy + 56)), (New-Object System.Drawing.Point ($cx + 66), ($cy - 52))))
$out = Join-Path $PSScriptRoot 'icon.png'
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
"Saved $out ($([math]::Round((Get-Item $out).Length / 1KB)) KB, ${size}x${size})"
