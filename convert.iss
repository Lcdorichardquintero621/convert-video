[Setup]
AppId={{B7E2C4A1-3D58-4F6A-9C21-6A0E5D7F1B34}
AppName=Convert
AppVersion=1.0
AppPublisher=Convert
DefaultDirName={autopf}\Convert
DefaultGroupName=Convert
OutputDir=installer
OutputBaseFilename=Convert-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\Convert.exe
WizardStyle=modern
WizardImageFile=wizard_large.bmp
WizardSmallImageFile=wizard_small.bmp
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un icono en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\Convert.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Convert"; Filename: "{app}\Convert.exe"
Name: "{autodesktop}\Convert"; Filename: "{app}\Convert.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Convert.exe"; Description: "Abrir Convert"; Flags: nowait postinstall skipifsilent
