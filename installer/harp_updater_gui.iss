; Inno Setup script for Harp Updater GUI
; Compile with ISCC and optional defines:
;   /DAppVersion=0.1.0
;   /DInstallerOutputBaseFilename=harp_updater_gui-installer-v0.1.0

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef InstallerOutputBaseFilename
  #define InstallerOutputBaseFilename "harp_updater_gui-installer"
#endif

#define DotNetDesktopRuntimeFile "windowsdesktop-runtime-8.0-x64.exe"
#define DotNetDesktopRuntimeUrl "https://aka.ms/dotnet/8.0/windowsdesktop-runtime-win-x64.exe"

[Setup]
AppId=HarpUpdaterGUI
AppName=Harp Updater GUI
AppVersion={#AppVersion}
AppPublisher=Allen Institute
AppPublisherURL=https://www.alleninstitute.org/
DefaultDirName={autopf}\AllenInstitute\Harp Updater GUI
DefaultGroupName=Harp Updater GUI
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename={#InstallerOutputBaseFilename}
SolidCompression=yes
WizardStyle=modern dynamic
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=src\harp_updater_gui\static\app_icon_color.ico
UninstallDisplayIcon={app}\harp_updater_gui.exe

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\harp_updater_gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Harp Updater GUI"; Filename: "{app}\harp_updater_gui.exe"
Name: "{autodesktop}\Harp Updater GUI"; Filename: "{app}\harp_updater_gui.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\{#DotNetDesktopRuntimeFile}"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing .NET 8 Desktop Runtime..."; Flags: waituntilterminated runhidden; Check: (not IsDotNetDesktopRuntime8Installed) and FileExists(ExpandConstant('{tmp}\{#DotNetDesktopRuntimeFile}'))
Filename: "{app}\harp_updater_gui.exe"; Description: "Launch Harp Updater GUI"; Flags: nowait postinstall skipifsilent

[Code]
var
  DotNetRuntimeDownloadPage: TDownloadWizardPage;

function IsDotNetDesktopRuntime8Installed: Boolean;
var
  DotnetPath: String;
  ResultCode: Integer;
  Output: TExecOutput;
  I: Integer;
  Line: String;
begin
  Result := False;

  if not RegQueryStringValue(HKLM64, 'SOFTWARE\dotnet\Setup\InstalledVersions\x64', 'InstallLocation', DotnetPath) then
    DotnetPath := ExpandConstant('{commonpf64}\dotnet\');

  DotnetPath := AddBackslash(DotnetPath) + 'dotnet.exe';
  if not FileExists(DotnetPath) then
    exit;

  if ExecAndCaptureOutput(DotnetPath, '--list-runtimes', '', SW_HIDE, ewWaitUntilTerminated, ResultCode, Output) and (ResultCode = 0) then
  begin
    for I := 0 to GetArrayLength(Output.StdOut) - 1 do
    begin
      Line := Trim(Output.StdOut[I]);
      if Pos('Microsoft.WindowsDesktop.App 8.', Line) = 1 then
      begin
        Result := True;
        exit;
      end;
    end;
  end;
end;

procedure InitializeWizard;
begin
  if not IsDotNetDesktopRuntime8Installed then
  begin
    DotNetRuntimeDownloadPage := CreateDownloadPage(
      SetupMessage(msgWizardPreparing),
      'Downloading Microsoft .NET 8 Desktop Runtime',
      nil
    );
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';

  if IsDotNetDesktopRuntime8Installed then
    exit;

  if DotNetRuntimeDownloadPage = nil then
    exit;

  if FileExists(ExpandConstant('{tmp}\{#DotNetDesktopRuntimeFile}')) then
    exit;

  DotNetRuntimeDownloadPage.Clear;
  DotNetRuntimeDownloadPage.Add(
    '{#DotNetDesktopRuntimeUrl}',
    '{#DotNetDesktopRuntimeFile}',
    ''
  );

  try
    DotNetRuntimeDownloadPage.Show;
    DotNetRuntimeDownloadPage.Download;
  except
    if DotNetRuntimeDownloadPage.AbortedByUser then
      Result := '.NET 8 Desktop Runtime download was canceled by the user.'
    else
      Result := 'Failed to download .NET 8 Desktop Runtime: ' + GetExceptionMessage;
  end;

  DotNetRuntimeDownloadPage.Hide;
end;
