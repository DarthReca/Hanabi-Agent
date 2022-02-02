$python = $env:CONDA_PYTHON_EXE
$epochs = 100
$numberOfPlayers = 2

if (Test-Path -Path "game.log" -PathType Leaf) {
    Remove-Item -Path "game.log"
}

Start-Process -FilePath $python -ArgumentList "server.py", $numberOfPlayers
for ($i = 0; $i -lt $numberOfPlayers; $i++) {
    $evolve = ($i%2 -eq 0 ? "--evolve" : "")
    $type = "Canaan"
    Start-Process -FilePath $python -ArgumentList "client.py", "--bot", $type, "--player_name", "Bot$i", "--epochs", $epochs
    Start-Sleep -Seconds 0.5
}


# Get-Content "Bot0.log" -Tail 1 | Out-File -FilePath "Scores.txt" -Append
