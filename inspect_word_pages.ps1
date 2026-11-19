param([string]$InputPath)
$word=New-Object -ComObject Word.Application
$word.Visible=$false
$word.DisplayAlerts=0
try {
 $doc=$word.Documents.Open($InputPath,$false,$true)
 try {
  $doc.Repaginate()
  foreach($term in @('PHẦN MỞ ĐẦU','CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI','CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ','CHƯƠNG 3: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG','CHƯƠNG 4: XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG','CHƯƠNG 5: THỰC NGHIỆM VÀ ĐÁNH GIÁ','PHẦN KẾT LUẬN','TÀI LIỆU THAM KHẢO')) {
    $range=$doc.Content.Duplicate
    $find=$range.Find
    $find.Text=$term
    $find.MatchCase=$false
    if($find.Execute()) { Write-Output "$term=$($range.Information(3))" }
  }
  Write-Output "TOTAL=$($doc.ComputeStatistics(2))"
 } finally {$doc.Close(0)}
} finally {$word.Quit()}
