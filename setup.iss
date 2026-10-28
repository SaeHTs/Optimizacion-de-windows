; ============================================================
;  Instalador de Optimización — Axiios_HTs
;  Compilar: ISCC.exe setup.iss
;
;  Instalación POR USUARIO (sin permisos de Administrador):
;  evita el error 740. Los ejecutables se elevan solos
;  con UAC cuando necesitan optimizar el sistema.
; ============================================================

#define AppVersion "2.1.0"

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
; Cierra la app si esta abierta al instalar (si no, los .exe estan en uso y
; la instalacion falla con "Omitir este archivo"). Inno 6.2+ lo hace solo.
CloseApplications=yes
RestartApplications=yes
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
; Instalador bilingue: los textos propios vienen de instalador\mensajes_*.isl
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl,instalador\mensajes_es.isl"
Name: "english"; MessagesFile: "compiler:Default.isl,instalador\mensajes_en.isl"

[Files]
Source: "dist\Optimizacion-GUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Optimizacion.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{cm:Icon_GUI}"; Filename: "{app}\Optimizacion-GUI.exe"
Name: "{group}\{cm:Icon_Consola}"; Filename: "{app}\Optimizacion.exe"
Name: "{group}\{cm:Icon_Desinstalar}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{cm:Icon_Acceso}"; Filename: "{app}\Optimizacion-GUI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:Tarea_Escritorio}"; GroupDescription: "{cm:Tarea_Grupo}"; Flags: unchecked

[Run]
; Los .exe van con --uac-admin (exigen elevacion), asi que hay que lanzarlos
; con ShellExecute ("shellexec"): con CreateProcess, Inno falla al final de la
; instalacion con "CreateProcess fallo; codigo 740" (la operacion solicitada
; requiere elevacion). ShellExecute si dispara el aviso de UAC.
Filename: "{app}\Optimizacion-GUI.exe"; Description: "{cm:EjecutarAhora}"; Flags: nowait postinstall skipifsilent shellexec

[Code]
// Los ejecutables van con --uac-admin: si la aplicacion esta abierta, sus
// ficheros estan en uso y la instalacion falla con "Omitir este archivo".
// Inno no puede cerrar una app elevada desde un instalador sin elevate,
// asi que se avisa antes de empezar.
function ProcesoCorriendo(Nombre: String): Boolean;
var
  Resultado: Integer;
  Comando: String;
begin
  Resultado := 1;
  Comando := '/C tasklist /FI "IMAGENAME eq ' + Nombre + '" /NH ' +
            '| find /I "' + Nombre + '" >NUL';
  Exec(ExpandConstant('{cmd}'), Comando, '', SW_HIDE, ewWaitUntilTerminated, Resultado);
  Result := Resultado = 0;
end;

function AppEstaAbierta: Boolean;
begin
  Result := ProcesoCorriendo('Optimizacion-GUI.exe') or
            ProcesoCorriendo('Optimizacion.exe');
end;

// La comprobacion va en PrepareToInstall, NO en InitializeSetup:
// InitializeSetup se ejecuta ANTES de la pagina de idioma, asi que el aviso
// saldria siempre en el idioma por defecto. En PrepareToInstall el usuario
// ya ha elegido el idioma y todavia no se ha copiado nada.
// Devolver un texto != '' cancela la instalacion con ese motivo.
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if AppEstaAbierta then
    Result := CustomMessage('AppEnUso');
end;
