<#
Gera o boxplot ILS/VNS/SA-PD sem dependencias Python externas. Os RPDs ja
foram calculados de forma pareada pelo consolidate_sa_pd_final.py.
#>
param(
    [string]$InputCsv = "new_experiments/final_tables_20261108/sa_pd_table6_paired_seed_results.csv",
    [string]$OutputPng = "new_experiments/final_tables_20261108/figures/rpd_boxplot_ils_vns_sa_pd_sop_grande_t100.png"
)

Add-Type -AssemblyName System.Drawing
$rows = Import-Csv $InputCsv
$groups = @(
    @{ Name = "ILS"; Column = "ils_rpd_percent"; Color = "#287D3C" },
    @{ Name = "VNS adaptado"; Column = "vns_rpd_percent"; Color = "#BE3F3F" },
    @{ Name = "SA-PD"; Column = "sa_pd_rpd_percent"; Color = "#396EAA" }
)

function Quantile([double[]]$Values, [double]$P) {
    $sorted = @($Values | Sort-Object)
    $position = ($sorted.Count - 1) * $P
    $left = [math]::Floor($position); $right = [math]::Ceiling($position)
    if ($left -eq $right) { return $sorted[$left] }
    return $sorted[$left] + ($position - $left) * ($sorted[$right] - $sorted[$left])
}

$stats = foreach ($group in $groups) {
    [double[]]$values = @($rows | ForEach-Object { [double]$_.$($group.Column) })
    $q1 = Quantile $values 0.25; $median = Quantile $values 0.50; $q3 = Quantile $values 0.75
    $lower = $q1 - 1.5 * ($q3 - $q1); $upper = $q3 + 1.5 * ($q3 - $q1)
    $inliers = @($values | Where-Object { $_ -ge $lower -and $_ -le $upper })
    [pscustomobject]@{ Group = $group; Q1 = $q1; Median = $median; Q3 = $q3;
        Low = ($inliers | Measure-Object -Minimum).Minimum; High = ($inliers | Measure-Object -Maximum).Maximum;
        Outliers = @($values | Where-Object { $_ -lt $lower -or $_ -gt $upper }) }
}

$maxValue = [math]::Ceiling((($stats | ForEach-Object { [math]::Max($_.High, ($_.Outliers | Measure-Object -Maximum).Maximum) } | Measure-Object -Maximum).Maximum + 2) / 5) * 5
$width = 1600; $height = 1050; $left = 170; $right = 90; $top = 155; $bottom = 175
$plotWidth = $width - $left - $right; $plotHeight = $height - $top - $bottom
$mapY = { param([double]$v) $top + $plotHeight - ($v / $maxValue * $plotHeight) }

$bitmap = [System.Drawing.Bitmap]::new($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::White)
$titleFont = [System.Drawing.Font]::new("Arial", 25, [System.Drawing.FontStyle]::Bold)
$labelFont = [System.Drawing.Font]::new("Arial", 20)
$smallFont = [System.Drawing.Font]::new("Arial", 17)
$black = [System.Drawing.Brushes]::Black; $axisPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(80,80,80), 2)
$gridPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(220,225,232), 1)

$graphics.DrawString("SOP grande (T100): RPD por 280 execucoes pareadas", $titleFont, $black, 300, 45)
for ($tick = 0; $tick -le $maxValue; $tick += 5) {
    $y = & $mapY $tick
    $graphics.DrawLine($gridPen, $left, $y, $width - $right, $y)
    $graphics.DrawString("$tick", $smallFont, $black, 105, $y - 12)
}
$graphics.DrawLine($axisPen, $left, $top, $left, $height - $bottom)
$graphics.DrawLine($axisPen, $left, $height - $bottom, $width - $right, $height - $bottom)

for ($index = 0; $index -lt $stats.Count; $index++) {
    $stat = $stats[$index]; $x = $left + $plotWidth * (($index + 1) / 4); $half = 105
    $color = [System.Drawing.ColorTranslator]::FromHtml($stat.Group.Color)
    $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(195, $color))
    $boxTop = & $mapY $stat.Q3; $boxBottom = & $mapY $stat.Q1
    $graphics.DrawLine($axisPen, $x, (& $mapY $stat.High), $x, $boxTop)
    $graphics.DrawLine($axisPen, $x, $boxBottom, $x, (& $mapY $stat.Low))
    $graphics.DrawLine($axisPen, $x - 45, (& $mapY $stat.High), $x + 45, (& $mapY $stat.High))
    $graphics.DrawLine($axisPen, $x - 45, (& $mapY $stat.Low), $x + 45, (& $mapY $stat.Low))
    $graphics.FillRectangle($brush, $x - $half, $boxTop, 2 * $half, $boxBottom - $boxTop)
    $graphics.DrawRectangle($axisPen, $x - $half, $boxTop, 2 * $half, $boxBottom - $boxTop)
    $graphics.DrawLine([System.Drawing.Pens]::Black, $x - $half, (& $mapY $stat.Median), $x + $half, (& $mapY $stat.Median))
    foreach ($outlier in $stat.Outliers) { $y = & $mapY $outlier; $graphics.FillEllipse([System.Drawing.Brushes]::DimGray, $x - 5, $y - 5, 10, 10) }
    $size = $graphics.MeasureString($stat.Group.Name, $labelFont)
    $graphics.DrawString($stat.Group.Name, $labelFont, $black, $x - $size.Width / 2, $height - $bottom + 28)
    $brush.Dispose()
}
$graphics.TranslateTransform(43, $top + $plotHeight / 2); $graphics.RotateTransform(-90)
$graphics.DrawString("RPD em relacao ao melhor valor entre os tres (%)", $labelFont, $black, -285, 0)
$graphics.ResetTransform()

$outputDir = Split-Path -Parent $OutputPng
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$bitmap.Save((Resolve-Path $outputDir).Path + "\\" + (Split-Path -Leaf $OutputPng), [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bitmap.Dispose(); $titleFont.Dispose(); $labelFont.Dispose(); $smallFont.Dispose(); $axisPen.Dispose(); $gridPen.Dispose()
Write-Output "Boxplot gerado em: $OutputPng"
