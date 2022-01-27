$python = $env:CONDA_PYTHON_EXE
$epochs = 3

for ($i = 0; $i -lt $epochs; $i++) {
    Start-Process -FilePath $python -ArgumentList "server.py"

    Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot0"
    Start-Process -FilePath $python -ArgumentList "client.py", "--bot", "Poirot", "--player_name", "Bot1" -Wait

    Get-Content "Bot0.log" -Tail 1 | Out-File -FilePath "Scores.txt" -Append
}