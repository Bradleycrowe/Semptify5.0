@echo off
:: =============================================================================
:: Semptify 5.0 - Production Server Launcher (Batch wrapper)
:: =============================================================================
:: Double-click this to start Semptify 5.0 with enforced security
:: =============================================================================

title Semptify 5.0 - Production Server

cd /d "C:\Semptify\Semptify-FastAPI"
powershell -ExecutionPolicy Bypass -File "start_semptify_production.ps1"

pause
