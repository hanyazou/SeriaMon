@@echo "Setup Windows Python Embeddable..."

@@findstr /v "^@@.*" "%~f0" | findstr /v "^:.*" | powershell - & goto :end_of_ps
<#
  PowerShell
#>
wget https://www.python.org/ftp/python/3.8.7/python-3.8.7-embed-amd64.zip -O python.zip
Expand-Archive -Path python.zip -DestinationPath .python

echo "import site" | Out-File -Append -Encoding ascii  .python/python*._pth
echo "../" | Out-File -Append -Encoding ascii  .python/python*._pth

wget "https://bootstrap.pypa.io/get-pip.py" -O ".python/get-pip.py"
:end_of_ps

@@set PATH="%~dp0.python";

@@rem Add this without the double quotes to suppress warnings like the following
@@rem   "WARNING: The script wheel.exe is installed in '...python\Scripts' which is not on PATH."
@@set PATH=%PATH%;%~dp0.python\Scripts

@@rem 
@@rem Install packages
@@rem 
@@python .python/get-pip.py
@@python -m pip install PyQt5
@@python -m pip install pyserial
@@python -m pip install PythonQwt
@@python -m pip install guidata
@@python -m pip install Cython
@@python -m pip install guiqwt
@@python -m pip install bleak
@@python -m pip install asyncssh

@@echo.
@@echo "Setup Windows Python Embeddable...done"
@@echo.

@@pause
