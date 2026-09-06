#define MyAppName "Canine Impaction Analyzer"
#define MyAppVersion "1.1.2"
#define MyAppPublisher "Samer Mheissen"
#define MyAppExeName "Canine Impaction Analyzer.exe"

[Setup]
AppId={{E25A3DF7-149A-4B74-9F08-CA3A78C5E14B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Canine Impaction Analyzer
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=CanineImpactionAnalyzer_Setup_v1.1.2
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\Canine Impaction Analyzer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
