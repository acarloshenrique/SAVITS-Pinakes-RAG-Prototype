@echo off
setlocal
set PYTHONIOENCODING=utf-8
if not exist reports mkdir reports
python build_graph.py || goto :error
python -m src.governance.fair_validator pinakes_graph.ttl > reports\governance_report.json || goto :error
pytest || goto :error
echo Build pipeline finalizado com sucesso.
exit /b 0
:error
echo Build pipeline falhou com erro %errorlevel%.
exit /b %errorlevel%

