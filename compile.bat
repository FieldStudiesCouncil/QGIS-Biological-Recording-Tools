@echo off

REM Windows batch file for compiling ui XML produced by QT designer to py object files
REM Replaces makefile in previous distributions which was overcomplicated and required
REM installation of third party software such as MinGW.
REM This batch file compares timestamp of ui and py files to see if the file
REM needs to be required. Code extended from:
REM https://stackoverflow.com/questions/1687014/how-do-i-compare-timestamps-of-files-in-a-batch-script

set "OSGEO4W_ROOT=C:\Program Files\QGIS 3.10"
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
call "%OSGEO4W_ROOT%\bin\qt5_env.bat"
call "%OSGEO4W_ROOT%\bin\py3_env.bat"

call :compile ui_osgr.ui ui_osgr.py
call :compile ui_nbn.ui ui_nbn.py
call :compile ui_mapmashup.ui ui_mapmashup.py
call :compile ui_biorec.ui ui_biorec.py
call :compile ui_env.ui ui_env.py
call :compile ui_file.ui ui_file.py
call :compile ui_R6.ui ui_R6.py
call :compile ui_R6Credentials.ui ui_R6Credentials.py
goto :eof

REM :compile uiFile pyFile
REM Will compile if UI file newer than PY file - by more than a minute
:compile
call :getfiledatestr %1 file1time
call :getfiledatestr %2 file2time
if "%file1time%" gtr "%file2time%" (
  echo compiling %1 to %2
  call pyuic5 -o %2 %1
)
goto :eof

REM :getfiledatestr file-path envvar
REM result returned in %envvar%
:getfiledatestr
for %%f in (%1) do set getfiledatestr=%%~tf
REM for MM/DD/YYYY HH:MM AMPM use call :appendpadded %2 %%c %%b %%a %%f %%d %%e
REM for DD/MM/YYYY HH:MM AMPM use call :appendpadded %2 %%c %%b %%a %%f %%d %%e
REM for YYYY/DD/MM HH:MM AMPM use call :appendpadded %2 %%a %%b %%c %%f %%d %%e
set %2=
for /f "tokens=1,2,3,4,5,6 delims=/: " %%a in ("%getfiledatestr%") do (
    call :appendpadded %2 %%c %%b %%a %%f %%d %%e
)
goto :eof

REM Takes an env var as the first parameter
REM and values to be appended as the remaining parameters,
REM right-padding all values with leading 0's to 4 places
:appendpadded
set temp_value=000%2
call :expand set %1=%%%1%%%%temp_value:~-4%%
shift /2
if "%2" neq "" goto appendpadded
set temp_value=
goto :eof

REM forces all variables to expand fully
:expand
%*
goto :eof

@echo on