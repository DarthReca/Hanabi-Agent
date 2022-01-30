$python = $env:CONDA_PYTHON_EXE
$epochs = "10"

Start-Process -FilePath $python -ArgumentList "server.py"

Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot0", "--epochs", $epochs
Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot1", "--epochs", $epochs -Wait

# Get-Content "Bot0.log" -Tail 1 | Out-File -FilePath "Scores.txt" -Append
