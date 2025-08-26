if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit
@rem @setlocal EnableDelayedExpansion
@rem @cd /D %~dp0
@rem @for /R %%d in (.) do (
@rem @    set "dirs=!dirs!;%%d"
@rem @    set "mundirs=%%d"
@rem @    set "undirs=%mundirs~0,3%"
@rem @)
@rem @echo "Python path is %dirs%"
@rem @echo "Python path2 is %undirs%"
@rem @(endlocal
@rem @    @set "ret=%PATH%"
@rem @)
@set PYTHONPATH=%PYTHONPATH%;D:\Programming\Python\CommonModules
IF EXIST %LocalAppData%\Programs\Python\Python312\python.exe (
%LocalAppData%\Programs\Python\Python312\python.exe .\main.py)
@echo "Результат %errorlevel%"
@pause 
exit