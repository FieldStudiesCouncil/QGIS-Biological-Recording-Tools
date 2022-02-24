@echo off

set "OSGEO4W_ROOT=C:\OSGeo4W64"
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
call "%OSGEO4W_ROOT%\bin\qt5_env.bat"
call "%OSGEO4W_ROOT%\bin\py3_env.bat"

set GITPATH=C:\Program Files\Git\cmd
path %GITPATH%;%PATH%

@REM set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python;%OSGEO4W_ROOT%\apps\qgis\python\plugins
@REM path %PYTHONPATH%;%PATH%

start "VisualStudioCode for QGIS" /B "C:\Users\richb\AppData\Local\Programs\Microsoft VS Code\Code.exe" %*