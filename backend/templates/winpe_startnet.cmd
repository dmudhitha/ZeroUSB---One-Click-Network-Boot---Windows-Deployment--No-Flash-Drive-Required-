@echo off
title ZeroUSB - __OS_NAME__ Network Deployment
cls
echo =================================================================
echo   ZeroUSB - Starting Network Deployment Subsystem
echo =================================================================
echo.
echo [1/4] Initializing Windows PE Environment...
wpeinit

rem Load injected network and chipset drivers for modern laptops (Asus, Lenovo, Dell, HP)
if exist X:\Drivers (
    echo       [*] Detecting and loading network drivers...
    for /r X:\Drivers %%i in (*.inf) do drvload "%%i" > nul 2>&1
)

wpeutil InitializeNetwork > nul 2>&1
net start lanmanworkstation > nul 2>&1
echo       [OK] WinPE network subsystem started.

rem Auto-bypass Windows 11 Hardware Restrictions (TPM 2.0, SecureBoot, RAM, Storage, CPU)
reg add "HKLM\SYSTEM\Setup\LabConfig" /v "BypassTPMCheck" /t REG_DWORD /d 1 /f > nul 2>&1
reg add "HKLM\SYSTEM\Setup\LabConfig" /v "BypassSecureBootCheck" /t REG_DWORD /d 1 /f > nul 2>&1
reg add "HKLM\SYSTEM\Setup\LabConfig" /v "BypassRAMCheck" /t REG_DWORD /d 1 /f > nul 2>&1
reg add "HKLM\SYSTEM\Setup\LabConfig" /v "BypassStorageCheck" /t REG_DWORD /d 1 /f > nul 2>&1
reg add "HKLM\SYSTEM\Setup\LabConfig" /v "BypassCPUCheck" /t REG_DWORD /d 1 /f > nul 2>&1

set SERVER_IP=__SERVER_IP__
set SHARE_NAME=__OS_SLUG__
set RETRY=0

echo.
echo [2/4] Verifying network connection and DHCP lease...
:retry_loop
set /a RETRY=RETRY+1
echo       [Attempt %RETRY%/20] Connecting to ZeroUSB Host (%SERVER_IP%)...
ping -n 1 -w 1000 %SERVER_IP% > nul
if not errorlevel 1 goto link_ok
ipconfig /renew > nul 2>&1
ping -n 3 127.0.0.1 > nul
if %RETRY% LSS 20 goto retry_loop

:link_ok
echo       [OK] Network link established!
echo.
echo   Current IP Configuration:
echo   ---------------------------------------------------------------
ipconfig
echo   ---------------------------------------------------------------

echo.
echo [3/4] Mounting Installation Media Share...
net use Z: \\%SERVER_IP%\%SHARE_NAME% "" > nul 2>&1
if errorlevel 1 net use Z: \\%SERVER_IP%\%SHARE_NAME% /user:guest "" > nul 2>&1
if errorlevel 1 net use Z: \\%SERVER_IP%\%SHARE_NAME% /user:mudhitha "" > nul 2>&1
if errorlevel 1 net use Z: \\%SERVER_IP%\%SHARE_NAME% /user:nobody "" > nul 2>&1

:check_media
set WIM_FILE=
if exist Z:\sources\install.wim set WIM_FILE=Z:\sources\install.wim
if not defined WIM_FILE if exist Z:\sources\install.esd set WIM_FILE=Z:\sources\install.esd
if not defined WIM_FILE if exist Z:\install.wim set WIM_FILE=Z:\install.wim
if not defined WIM_FILE if exist Z:\install.esd set WIM_FILE=Z:\install.esd

if defined WIM_FILE (
    echo       [OK] Successfully mounted \\%SERVER_IP%\%SHARE_NAME% on Drive Z:!
    echo.
    echo [4/4] Loading Deployment Menu...
    ping -n 2 127.0.0.1 > nul
    goto menu
)

echo       [!] Warning: Installation media not found on Z:. Retrying...
ping -n 3 127.0.0.1 > nul
if %RETRY% LSS 20 goto retry_loop
goto manual_cli

:menu
cls
echo =================================================================
echo   ZeroUSB Multi-OS Fast Network Installer
echo   Target:      __OS_NAME__
echo   Server:      \\%SERVER_IP%\%SHARE_NAME%
echo   Image File:  %WIM_FILE%
echo =================================================================
echo.
echo   [1] Full Clean Install          - Wipes Disk 0 (Fresh Drive)
echo   [2] Format C: and Install OS    - Keeps Other Drives and Data Safe
echo   [3] Graphical Setup             - Launches Standard Windows Setup Wizard
echo   [4] Custom Edition              - Select Edition (Pro / Core / Enterprise)
echo   [5] Command Prompt              - Manual Diskpart and Diagnostic Tools
echo   [6] Reboot Computer
echo.
echo =================================================================
set OPT=
set /p OPT="Enter your choice (1-6) [Default=2]: "
if "%OPT%"=="" set OPT=2
if "%OPT%"=="1" goto confirm_clean
if "%OPT%"=="2" goto select_safe_deploy
if "%OPT%"=="3" goto run_setup_gui
if "%OPT%"=="4" goto ask_index
if "%OPT%"=="5" goto manual_cli
if "%OPT%"=="6" wpeutil reboot
goto menu

:select_safe_deploy
set INDEX=1
goto do_safe_deploy

:run_setup_gui
cls
echo =================================================================
echo   Launching Graphical Windows Setup Wizard...
echo   Source: %WIM_FILE%
echo =================================================================
echo.
cd /d Z:\sources 2>nul
if exist Z:\sources\setup.exe (
    start "" /wait Z:\sources\setup.exe /installfrom:%WIM_FILE%
) else if exist X:\sources\setup.exe (
    start "" /wait X:\sources\setup.exe /installfrom:%WIM_FILE%
) else (
    start "" /wait setup.exe /installfrom:%WIM_FILE%
)
goto menu

:confirm_clean
cls
echo =================================================================
echo   WARNING: FULL DISK WIPE SELECTED
echo =================================================================
echo   This will erase ALL partitions on Disk 0!
echo   Other physical hard drives (Disk 1, Disk 2, USBs) are NOT touched.
echo.
set CONFIRM=
set /p CONFIRM="Are you sure you want to wipe Disk 0? (Y/N): "
if /i "%CONFIRM%"=="Y" set INDEX=1 & goto do_clean_deploy
goto menu

:ask_index
cls
if exist Z:\sources\editions.txt (
    type Z:\sources\editions.txt
) else if exist Z:\editions.txt (
    type Z:\editions.txt
) else (
    echo Available Editions in Image:
    dism /get-wiminfo /wimfile:%WIM_FILE%
)
echo.
set INDEX=
set /p INDEX="Enter Edition Index to install (or 0 / B to Go Back): "
if "%INDEX%"=="" goto menu
if "%INDEX%"=="0" goto menu
if /i "%INDEX%"=="B" goto menu
if /i "%INDEX%"=="BACK" goto menu
echo.
echo [1] Full Clean Install (Wipe entire Disk 0)
echo [2] Format Target OS Drive and Install (Keep other drives safe)
set MODE=
set /p MODE="Choose disk mode (1 or 2) [Default=2]: "
if "%MODE%"=="1" goto do_clean_deploy
goto do_safe_deploy

:do_clean_deploy
cls
if not defined INDEX set INDEX=1
set TARGET_DRIVE=C:
echo =================================================================
echo   Full Disk Deploy: __OS_NAME__ (Index %INDEX%) to Disk 0
echo =================================================================
echo.
echo [1/3] Partitioning and formatting Disk 0 (Drive C:)...
(
echo select disk 0
echo clean
echo convert mbr
echo create partition primary
echo format fs=ntfs quick label="Windows"
echo assign letter=C
echo active
) | diskpart > nul
echo     [OK] Disk 0 wiped, Drive C: partitioned and activated.
goto apply_payload

:do_safe_deploy
cls
if not defined INDEX set INDEX=1
echo =================================================================
echo   Scanning Disks for Existing Windows Installation...
echo =================================================================
echo.
set TARGET_DRIVE=C:
if exist D:\Windows\System32\ntoskrnl.exe set TARGET_DRIVE=D:
if exist E:\Windows\System32\ntoskrnl.exe set TARGET_DRIVE=E:
if exist C:\Windows\System32\ntoskrnl.exe set TARGET_DRIVE=C:

echo   [OK] Target Windows Drive: %TARGET_DRIVE%
echo   All other drives, partitions, and files will remain untouched.
echo.
set CONFIRM=
set /p CONFIRM="Format %TARGET_DRIVE% and install new OS? (Y/N) [Default=Y]: "
if /i "%CONFIRM%"=="N" goto menu

echo.
echo [1/3] Formatting only Drive %TARGET_DRIVE% (NTFS)...
echo Y | format %TARGET_DRIVE% /fs:ntfs /q /v:Windows /x > nul 2>&1
echo     [OK] Drive %TARGET_DRIVE% formatted. Other partitions are safe!
goto apply_payload

:apply_payload
echo.
echo [2/3] Applying Windows Image directly at Gigabit Wire Speed...
echo     [*] Image:  %WIM_FILE% (Index %INDEX%)
echo     [*] Target: %TARGET_DRIVE%\
echo     [*] Please wait approximately 90 seconds...
echo.
dism /apply-image /imagefile:%WIM_FILE% /index:%INDEX% /applydir:%TARGET_DRIVE%\

echo.
echo [3/3] Installing Bootloader to Drive %TARGET_DRIVE%...
if exist X:\Drivers (
    dism /image:%TARGET_DRIVE%\ /add-driver /driver:X:\Drivers /recurse > nul 2>&1
    echo     [OK] Injected network and storage drivers into %TARGET_DRIVE%\Windows.
)
bcdboot %TARGET_DRIVE%\Windows /s %TARGET_DRIVE% /f ALL
echo     [OK] System bootloader installed.

rem Inject Windows 11 BypassNRO for offline local account creation (skip MSA requirement)
if exist %TARGET_DRIVE%\Windows\System32\config\SOFTWARE (
    reg load HKLM\OFFLINE_SOFT %TARGET_DRIVE%\Windows\System32\config\SOFTWARE > nul 2>&1
    reg add "HKLM\OFFLINE_SOFT\Microsoft\Windows\CurrentVersion\OOBE" /v "BypassNRO" /t REG_DWORD /d 1 /f > nul 2>&1
    reg unload HKLM\OFFLINE_SOFT > nul 2>&1
)

echo.
echo =================================================================
echo   Installation Successfully Completed!
echo   Rebooting into your new Windows in 10 seconds...
echo =================================================================
ping -n 11 127.0.0.1 > nul
wpeutil reboot

:manual_cli
cls
echo Type 'exit' to return to menu.
cmd.exe
goto menu
