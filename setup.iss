; ============================================================
;  Instalador de Optimización — Axiios_HTs
;  Compilar: ISCC.exe setup.iss
;
;  Instalación POR USUARIO (sin permisos de Administrador):
;  evita el error 740. Los ejecutables se elevan solos
;  con UAC cuando necesitan optimizar el sistema.
; ============================================================

#define AppVersion "1.5.2"

[Setup]
AppName=Optimización
AppVersion={#AppVersion}
AppVerName=Optimización v{#AppVersion}
AppPublisher=Axiios_HTs
AppPublisherURL=https://github.com/SaeHTs/Optimizacion-de-windows
AppSupportURL=https://github.com/SaeHTs/Optimizacion-de-windows
DefaultDirName={localappdata}\Programs\Optimizacion
DefaultGroupName=Optimización
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer
OutputBaseFilename=Optimizacion-Setup
SetupIconFile=icono.ico
UninstallDisplayIcon={app}\Optimizacion-GUI.exe
Compression=lzma2/max
SolidCompression=yes
; Por usuario: NO requiere elevación (soluciona error 740)
PrivilegesRequired=none
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupLogging=yes
; Metadatos del instalador
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Axiios_HTs
VersionInfoDescription=Instalador de Optimización v{#AppVersion}
VersionInfoCopyright=Axiios_HTs

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\Optimizacion-GUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Optimizacion.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Optimización (GUI)"; Filename: "{app}\Optimizacion-GUI.exe"
Name: "{group}\Optimización (Consola)"; Filename: "{app}\Optimizacion.exe"
Name: "{group}\Desinstalar Optimización"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Optimización"; Filename: "{app}\Optimizacion-GUI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Run]
Filename: "{app}\Optimizacion-GUI.exe"; Description: "Ejecutar Optimización ahora"; Flags: nowait postinstall skipifsilent
