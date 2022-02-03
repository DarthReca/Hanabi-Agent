$file = ".\game.log"
$discards = (Select-String -Pattern "discarded" -Path $file).Length 
$plays = (Select-String -Pattern "played" -Path $file).Length
$hints = (Select-String -Pattern "hint" -Path $file).Length
$total = $discards + $hints + $plays

Write-Output "Discards:" ($discards/$total)
Write-Output "Plays:" ($plays/$total)
Write-Output "Hints:" ($hints/$total)
