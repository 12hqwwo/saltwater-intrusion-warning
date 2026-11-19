param([Parameter(Mandatory=$true)][string]$InputPath,[Parameter(Mandatory=$true)][string]$PdfPath)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($InputPath, $false, $false)
  try {
    $null = $doc.Fields.Update()
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $null = $doc.Fields.Update()
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)
    $doc.Save()
    $doc.ExportAsFixedFormat($PdfPath,17)
    Write-Output "PAGES=$pages"
  } finally { $doc.Close(0) }
} finally { $word.Quit() }
