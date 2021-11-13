%~dp0\python\bin\python %~dp0\python\venv_from_pip.py
set CCIBIN=%userprofile%\.cumulusci\cci_python_env\bin
%CCIBIN%\python %CCIBIN%\ensure_dir_in_path.py %CCIBIN%\..\run
pause "Done installing"
