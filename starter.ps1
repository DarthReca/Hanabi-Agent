$python = $env:CONDA_PYTHON_EXE
$epochs = 100
$numeberOfPlayers = 2

Start-Process -FilePath $python -ArgumentList "server.py", $numeberOfPlayers
for ($i = 0; $i -lt $numeberOfPlayers; $i++) {
    Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot$i", "--epochs", $epochs
    Start-Sleep -Seconds 0.5
}


# Get-Content "Bot0.log" -Tail 1 | Out-File -FilePath "Scores.txt" -Append
