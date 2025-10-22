@echo off
echo Starting ADVOICE... > log.txt
echo Timestamp: %date% %time% >> log.txt
ADVOICE.exe >> log.txt 2>&1
