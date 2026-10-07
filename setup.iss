; ============================================================
;  Instalador de Optimización — Axiios_HTs
;  Compilar: ISCC.exe setup.iss
; ============================================================

#define AppVersion "1.5"

[Setup]
AppName=Optimización
AppVersion={#AppVersion}
AppVerName=Optimización v{#AppVersion}
AppPublisher=Axiios_HTs
AppPublisherURL=https://github.com/SaeHTs/Optimizacion-de-windows
AppSupportURL=https://github.com/SaeHTs/Optimizacion-de-windows
DefaultDirName={autopf}\Optimizacion
DefaultGroupName=Optimización
AllowNoIcons=yes
; Licencia
LicenseFile=LICENSE.txt
OutputDir=installer
OutputBaseFilename=Optimizacion-Setup
SetupIconFile=icono.ico
UninstallDisplayIcon={app}\Optimizacion-GUI.exe
Compression=lzma2/max
SolidCompression=yes
; Requerir administrador y 64 bits
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
; Tema moderno del asistente
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\Optimizacion-GUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Optimizacion.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Optimización (GUI)"; Filename: "{app}\Optimizacion-GUI.exe"
Name: "{group}\Optimización (Consola)"; Filename: "{app}\Optimizacion.exe"
Name: "{group}\Desinstalar Optimización"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Optimización"; Filename: "{app}\Optimizacion-GUI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Run]
Filename: "{app}\Optimizacion-GUI.exe"; Description: "Ejecutar Optimización ahora"; Flags: nowait postinstall skipifsilent

[Code]
// Pedir UAC al ejecutar los programas instalados (ya son admin por el instalador)
