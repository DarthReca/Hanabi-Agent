$python = $env:CONDA_PYTHON_EXE
$epochs = "10"

Start-Process -FilePath $python -ArgumentList "server.py"
Start-Sleep -Seconds 1
Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot0", "--epochs", $epochs
Start-Sleep -Seconds 1
Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot1", "--epochs", $epochs

# Get-Content "Bot0.log" -Tail 1 | Out-File -FilePath "Scores.txt" -Append
