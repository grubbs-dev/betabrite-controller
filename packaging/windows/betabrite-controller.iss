#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

#ifndef AppExe
  #error AppExe must point to the built BetaBriteController.exe
#endif

#ifndef OutputDir
  #define OutputDir "."
#endif

#ifndef AppIcon
  #error AppIcon must point to the BetaBrite Controller .ico file
#endif

#ifndef ArtifactSuffix
  #define ArtifactSuffix "-unsigned"
#endif

[Setup]
AppId={{66EFC08D-B164-4D29-A9F8-A9A5C40910F9}
AppName=BetaBrite Controller
AppVersion={#AppVersion}
AppPublisher=Grubbs
AppPublisherURL=https://github.com/grubbs-dev/betabrite-controller
AppSupportURL=https://github.com/grubbs-dev/betabrite-controller/issues
DefaultDirName={localappdata}\Programs\BetaBrite Controller
DefaultGroupName=BetaBrite Controller
OutputDir={#OutputDir}
OutputBaseFilename=betabrite-controller-{#AppVersion}-windows-x86_64{#ArtifactSuffix}-setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\BetaBriteController.exe
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#AppExe}"; DestDir: "{app}"; DestName: "BetaBriteController.exe"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\BetaBrite Controller"; Filename: "{app}\BetaBriteController.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\BetaBrite Controller"; Filename: "{app}\BetaBriteController.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\BetaBriteController.exe"; Description: "Launch BetaBrite Controller"; Flags: nowait postinstall skipifsilent
