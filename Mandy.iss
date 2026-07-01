[Setup]
AppName=Mandy
AppVersion=1.0.0
AppPublisher=Manav Patil
AppPublisherURL=https://github.com/Manav-Patil-10/personal-ai-os
AppSupportURL=https://github.com/Manav-Patil-10/personal-ai-os
AppUpdatesURL=https://github.com/Manav-Patil-10/personal-ai-os
DefaultDirName={autopf}\Mandy
DefaultGroupName=Mandy
OutputDir=installer
OutputBaseFilename=Mandy-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Mandy.exe
LicenseFile=LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Mandy.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Mandy"; Filename: "{app}\Mandy.exe"; IconIndex: 0; Comment: "Your Personal AI Assistant"
Name: "{group}\Uninstall Mandy"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Mandy"; Filename: "{app}\Mandy.exe"; Tasks: desktopicon; IconIndex: 0; Comment: "Your Personal AI Assistant"

[Run]
Filename: "{app}\Mandy.exe"; Flags: nowait postinstall skipifsilent; Description: "Launch Mandy"