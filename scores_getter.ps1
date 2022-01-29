$scores = (Get-Content -Path .\game.log) -match "Game Score" | ForEach-Object {[int]($_ -split ":")[-1]}
$scores | Measure-Object  -AllStats