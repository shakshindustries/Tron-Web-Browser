; ============================================================================
; INNO SETUP SCRIPT FOR TRON BROWSER
; Creates a standalone Windows Setup installer (TronBrowserSetup_v2.5.exe)
; ============================================================================

#define MyAppName "Tron Browser"
#define MyAppVersion "2.5.0"
#define MyAppPublisher "Tron Software"
#define MyAppURL "https://tronbrowse.netlify.app/"
#define MyAppExeName "TronBrowser.exe"
#define MyAppID "{{D9A2F891-6E3C-4F91-A8B2-192847561029}"
#define MyAppModelID "Tron.Browser.App.v2"

[Setup]
AppId={#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=TronBrowserSetup_v2.5
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\assets\app_icon.ico,0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "Create a Quick Launch shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\TronBrowser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\_internal\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{app}\_internal'))
Source: "assets\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_icon.ico"; IconIndex: 0; AppUserModelID: "{#MyAppModelID}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_icon.ico"; IconIndex: 0; Tasks: desktopicon; AppUserModelID: "{#MyAppModelID}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_icon.ico"; IconIndex: 0; Tasks: quicklaunchicon; AppUserModelID: "{#MyAppModelID}"

[Registry]
; Register AppUserModelID for Windows Taskbar & Start Menu Icon Grouping
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\{#MyAppModelID}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\{#MyAppModelID}"; ValueType: string; ValueName: "IconUri"; ValueData: "{app}\assets\app_icon.ico"; Flags: uninsdeletekey

; Register Application Capabilities for Windows Default Browser & Shell Integration
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\app_icon.ico,0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"""
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Tron Modern High-Performance Browser"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\assets\app_icon.ico,0"
Root: HKCU; Subkey: "Software\Clients\StartMenuInternet\{#MyAppName}\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#MyAppName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    try
      // Notify Windows Shell to refresh icon cache and associations immediately
      SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
    except
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    try
      SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
    except
    end;
  end;
end;
