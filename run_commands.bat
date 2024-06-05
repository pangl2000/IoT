:: Change to externalDB folder and run docker compose
cd externalDB
docker-compose up -d
timeout /t 2

:: Change to edgeController folder and run Python script
cd ..\edgeController
python run_scripts.py
timeout /t 2

:: Change to frontEnd-backEnd folder and run Node.js script
cd ..\frontEnd-backEnd
node start-scripts.js
timeout /t 2
