@echo off
cd /d "%~dp0"

echo Abriendo tu biblioteca...
echo.
echo Para cerrar la app, presiona Ctrl+C en esta ventana.
echo Si pregunta si deseas terminar, confirma con S o Y.
echo.

".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1

pause