#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

#ifndef AppExe
  #error AppExe must point to the built BetaBriteController.exe
#endif

#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
AppId={{66EFC08D-B164-4D29-A9F8-A9A5C40910F9}
AppName=BetaBrite Controller
AppVersion={#AppVersion}
AppPublisher=Grubbs
AppPublisherURL=https://github.com/grubbs-dev/betabrite-controller
AppSupportURL=https://github.com/grubbs-dev/betabrite-controller/issues
DefaultDirName={autopf}\BetaBrite Controller
DefaultGroupName=BetaBrite Controller
OutputDir={#OutputDir}
OutputBaseFilename=betabrite-controller-{#AppVersion}-windows-x86_64-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\BetaBriteController.exe
WizardStyle=modern

[Files]
Source: "{#AppExe}"; DestDir: "{app}"; DestName: "BetaBriteController.exe"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BetaBrite Controller"; Filename: "{app}\BetaBriteController.exe"
Name: "{autodesktop}\BetaBrite Controller"; Filename: "{app}\BetaBriteController.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\BetaBriteController.exe"; Description: "Launch BetaBrite Controller"; Flags: nowait postinstall skipifsilent
