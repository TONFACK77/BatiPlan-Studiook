; Inno Setup script - produces Output\BatiPlanStudio_Setup.exe   (https://jrsoftware.org/isinfo.php)
#define AppName "BatiPlan Studio"
#define AppVersion "1.0.0"
[Setup]
AppId={{B2D7F0A1-5C3E-4C7B-9E10-BA71F1A4D001}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\BatiPlanStudio
DefaultGroupName={#AppName}
OutputBaseFilename=BatiPlanStudio_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=EULA_FR_EN.txt
[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
[Files]
Source: "dist\BatiPlanStudio\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "samples\*"; DestDir: "{app}\Samples"; Flags: recursesubdirs ignoreversion
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\BatiPlanStudio.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\BatiPlanStudio.exe"
[Run]
Filename: "{app}\BatiPlanStudio.exe"; Description: "Lancer / Launch {#AppName}"; Flags: nowait postinstall skipifsilent
