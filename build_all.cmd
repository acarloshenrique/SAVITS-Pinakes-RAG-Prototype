@echo off
setlocal
set PYTHONIOENCODING=utf-8
python build_graph.py %*
endlocal
