# LICS Windows Development Environment Setup Script
# This script sets up the development environment for LICS on Windows

#Requires -RunAsAdministrator

param(
    [switch]$UseScoop,
    [switch]$Help
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output (Windows PowerShell compatible)
function Write-ColorOutput([String]$ForegroundColor, [String]$Message) {
    $originalColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Message
    $Host.UI.RawUI.ForegroundColor = $originalColor
}

function Write-Info($Message) {
    Write-ColorOutput "Cyan" "[INFO] $Message"
}

function Write-Success($Message) {
    Write-ColorOutput "Green" "[SUCCESS] $Message"
}

function Write-Warning($Message) {
    Write-ColorOutput "Yellow" "[WARNING] $Message"
}

function Write-Error($Message) {
    Write-ColorOutput "Red" "[ERROR] $Message"
}

# Check if command exists
function Test-Command($Command) {
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Display help
function Show-Help {
    Write-Output @"
LICS Windows Development Environment Setup Script

Usage: .\setup-windows.ps1 [options]

Options:
    -UseScoop    Use Scoop package manager instead of Chocolatey
    -Help        Show this help message

Requirements:
    - Windows 10/11 or Windows Server 2019/2022
    - PowerShell 5.1 or later
    - Administrator privileges
    - Internet connection

This script will install:
    - Git
    - Docker Desktop
    - Node.js (LTS)
    - Python 3.11
    - mkcert
    - Visual Studio Code (optional)
    - Development tools and utilities

Examples:
    .\setup-windows.ps1              # Use Chocolatey (default)
    .\setup-windows.ps1 -UseScoop    # Use Scoop instead
"@
}

# Check Windows version
function Test-WindowsVersion {
    Write-Info "Checking Windows version..."

    $version = Get-WmiObject -Class Win32_OperatingSystem
    $osVersion = [System.Version]$version.Version
    $productName = $version.Caption

    Write-Info "Operating System: $productName"
    Write-Info "Version: $($version.Version)"

    # Check for Windows 10 (10.0.10240) or later
    if ($osVersion.Major -lt 10) {
        Write-Error "Windows 10 or later is required. You have $productName"
        exit 1
    }

    Write-Success "Windows version is compatible"
}

# Check PowerShell version
function Test-PowerShellVersion {
    Write-Info "Checking PowerShell version..."

    $version = $PSVersionTable.PSVersion
    Write-Info "PowerShell version: $version"

    if ($version.Major -lt 5) {
        Write-Error "PowerShell 5.1 or later is required. You have $version"
        exit 1
    }

    Write-Success "PowerShell version is compatible"
}

# Enable Windows features
function Enable-WindowsFeatures {
    Write-Info "Enabling required Windows features..."

    # Enable Windows Subsystem for Linux (optional but useful)
    $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
    if ($wslFeature.State -eq "Disabled") {
        Write-Info "Enabling Windows Subsystem for Linux..."
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart
    }

    # Enable Hyper-V (required for Docker Desktop)
    $hyperVFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All
    if ($hyperVFeature.State -eq "Disabled") {
        Write-Info "Enabling Hyper-V..."
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart
        Write-Warning "Hyper-V has been enabled. A restart will be required after setup."
    }

    Write-Success "Windows features configured"
}

# Install Chocolatey
function Install-Chocolatey {
    Write-Info "Checking for Chocolatey..."

    if (Test-Command "choco") {
        Write-Success "Chocolatey already installed"
        choco --version
    }
    else {
        Write-Info "Installing Chocolatey..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        Write-Success "Chocolatey installed"
    }
}

# Install Scoop
function Install-Scoop {
    Write-Info "Checking for Scoop..."

    if (Test-Command "scoop") {
        Write-Success "Scoop already installed"
        scoop --version
    }
    else {
        Write-Info "Installing Scoop..."
        Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Invoke-RestMethod get.scoop.sh | Invoke-Expression

        # Add extra buckets
        scoop bucket add extras
        scoop bucket add versions

        Write-Success "Scoop installed"
    }
}

# Install packages with Chocolatey
function Install-PackagesChocolatey {
    Write-Info "Installing packages with Chocolatey..."

    $packages = @(
        "git",
        "docker-desktop",
        "nodejs-lts",
        "python311",
        "mkcert",
        "curl",
        "wget",
        "jq",
        "7zip",
        "notepadplusplus",
        "postman"
    )

    foreach ($package in $packages) {
        Write-Info "Installing $package..."
        try {
            choco install $package -y --no-progress
            Write-Success "$package installed"
        }
        catch {
            Write-Warning "Failed to install $package : $_"
        }
    }
}

# Install packages with Scoop
function Install-PackagesScoop {
    Write-Info "Installing packages with Scoop..."

    $packages = @(
        "git",
        "nodejs-lts",
        "python",
        "mkcert",
        "curl",
        "wget",
        "jq",
        "7zip"
    )

    foreach ($package in $packages) {
        Write-Info "Installing $package..."
        try {
            scoop install $package
            Write-Success "$package installed"
        }
        catch {
            Write-Warning "Failed to install $package : $_"
        }
    }

    # Docker Desktop needs manual installation with Scoop
    Write-Info "Installing Docker Desktop..."
    try {
        scoop install extras/docker-desktop
        Write-Success "Docker Desktop installed"
    }
    catch {
        Write-Warning "Failed to install Docker Desktop with Scoop. Please install manually from https://www.docker.com/products/docker-desktop"
    }
}

# Install Docker Desktop manually
function Install-DockerDesktop {
    Write-Info "Checking for Docker Desktop..."

    if (Test-Command "docker") {
        Write-Success "Docker already installed"
        docker --version
    }
    else {
        Write-Info "Docker not found. Installing Docker Desktop..."

        $dockerUrl = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe"
        $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"

        Write-Info "Downloading Docker Desktop installer..."
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller

        Write-Info "Installing Docker Desktop..."
        Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait

        Remove-Item $dockerInstaller -Force

        Write-Success "Docker Desktop installed"
        Write-Warning "Please start Docker Desktop and complete the setup before continuing"
    }
}

# Install Visual Studio Code
function Install-VSCode {
    if (Test-Command "code") {
        Write-Success "Visual Studio Code already installed"
    }
    else {
        $choice = Read-Host "Would you like to install Visual Studio Code? (y/N)"
        if ($choice -match "^[Yy]$") {
            Write-Info "Installing Visual Studio Code..."

            if ($UseScoop) {
                scoop install extras/vscode
            }
            else {
                choco install vscode -y --no-progress
            }

            # Install useful extensions
            Write-Info "Installing useful VS Code extensions..."
            $extensions = @(
                "ms-python.python",
                "ms-vscode.vscode-typescript-next",
                "bradlc.vscode-tailwindcss",
                "ms-vscode.vscode-json",
                "redhat.vscode-yaml",
                "ms-vscode-remote.remote-containers"
            )

            foreach ($extension in $extensions) {
                try {
                    code --install-extension $extension
                }
                catch {
                    Write-Warning "Failed to install extension $extension"
                }
            }

            Write-Success "Visual Studio Code installed with extensions"
        }
    }
}

# Setup development environment
function Set-DevelopmentEnvironment {
    Write-Info "Setting up development environment..."

    # Create PowerShell profile if it doesn't exist
    if (!(Test-Path $PROFILE)) {
        New-Item -Path $PROFILE -Type File -Force | Out-Null
    }

    # Add LICS development environment variables to PowerShell profile
    $profileContent = @"

# LICS Development Environment
`$env:LICS_DEV_MODE = "true"
`$env:COMPOSE_PROJECT_NAME = "lics"
`$env:DOCKER_BUILDKIT = "1"
`$env:COMPOSE_DOCKER_CLI_BUILD = "1"
`$env:NODE_ENV = "development"

# Development aliases
function lics-start { docker-compose -f docker-compose.dev.yml up }
function lics-stop { docker-compose -f docker-compose.dev.yml down }
function lics-logs { docker-compose -f docker-compose.dev.yml logs -f }
function lics-clean { docker-compose -f docker-compose.dev.yml down -v --remove-orphans }

"@

    Add-Content -Path $PROFILE -Value $profileContent

    Write-Success "Development environment configured"
}

# Generate SSL certificates
function New-SSLCertificates {
    Write-Info "Generating SSL certificates for local development..."

    # Create SSL directory
    $sslDir = "infrastructure\nginx\ssl"
    if (!(Test-Path $sslDir)) {
        New-Item -ItemType Directory -Path $sslDir -Force | Out-Null
    }

    # Generate certificates for local development
    Push-Location $sslDir
    try {
        mkcert -key-file localhost-key.pem -cert-file localhost.pem localhost 127.0.0.1 ::1 *.localhost

        # Copy certificates with expected names
        Copy-Item localhost.pem server.crt
        Copy-Item localhost-key.pem server.key

        Write-Success "SSL certificates generated"
    }
    catch {
        Write-Error "Failed to generate SSL certificates: $_"
    }
    finally {
        Pop-Location
    }
}

# Configure Windows Defender exclusions
function Set-DefenderExclusions {
    Write-Info "Configuring Windows Defender exclusions for better performance..."

    try {
        # Exclude Docker directories
        Add-MpPreference -ExclusionPath "C:\ProgramData\DockerDesktop"
        Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\.docker"

        # Exclude project directory
        $projectPath = Get-Location
        Add-MpPreference -ExclusionPath $projectPath.Path

        # Exclude common development directories
        Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\AppData\Roaming\npm"
        Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\AppData\Local\pip"

        Write-Success "Windows Defender exclusions configured"
    }
    catch {
        Write-Warning "Failed to configure Windows Defender exclusions. You may want to add them manually for better performance."
    }
}

# Verify installation
function Test-Installation {
    Write-Info "Verifying installation..."

    $tools = @{
        "git" = "Git"
        "docker" = "Docker"
        "node" = "Node.js"
        "npm" = "npm"
        "python" = "Python"
        "pip" = "pip"
        "mkcert" = "mkcert"
        "curl" = "curl"
        "jq" = "jq"
    }

    $allGood = $true

    foreach ($tool in $tools.GetEnumerator()) {
        if (Test-Command $tool.Key) {
            try {
                $version = & $tool.Key --version 2>$null | Select-Object -First 1
                Write-Success "$($tool.Value): $version"
            }
            catch {
                Write-Success "$($tool.Value): installed"
            }
        }
        else {
            Write-Error "$($tool.Value) is not installed or not in PATH"
            $allGood = $false
        }
    }

    # Check Docker service
    try {
        docker system info | Out-Null
        Write-Success "Docker is running"
    }
    catch {
        Write-Warning "Docker is not running or not accessible"
        $allGood = $false
    }

    if ($allGood) {
        Write-Success "All tools are installed and working!"
        return $true
    }
    else {
        Write-Error "Some tools are missing or not working properly"
        return $false
    }
}

# Main setup function
function Start-Setup {
    Write-Output "=========================================="
    Write-Output "LICS Windows Development Setup"
    Write-Output "=========================================="
    Write-Output ""

    Write-Info "Starting Windows development environment setup..."

    # Check system requirements
    Test-WindowsVersion
    Test-PowerShellVersion

    # Enable Windows features
    Enable-WindowsFeatures

    # Install package manager
    if ($UseScoop) {
        Install-Scoop
        Install-PackagesScoop
    }
    else {
        Install-Chocolatey
        Install-PackagesChocolatey
    }

    # Refresh environment variables
    Write-Info "Refreshing environment variables..."
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    # Install additional tools
    Install-VSCode
    Set-DevelopmentEnvironment
    New-SSLCertificates
    Set-DefenderExclusions

    Write-Output ""
    Write-Output "=========================================="
    Write-Success "Windows setup completed!"
    Write-Output "=========================================="
    Write-Output ""

    # Verify installation
    if (Test-Installation) {
        Write-Output ""
        Write-Info "Next steps:"
        Write-Output "1. Restart PowerShell or reload profile: . `$PROFILE"
        Write-Output "2. Start Docker Desktop and complete setup"
        Write-Output "3. Navigate to your LICS project directory"
        Write-Output "4. Copy .env.example to .env and configure as needed"
        Write-Output "5. Run: make install (to install project dependencies)"
        Write-Output "6. Run: make dev (to start development environment)"
        Write-Output ""
        Write-Success "You're ready to start developing with LICS!"
    }
    else {
        Write-Warning "Setup completed with some issues. Please check the error messages above."
        exit 1
    }
}

# Handle script interruption
trap {
    Write-Error "Setup interrupted by user"
    exit 1
}

# Main execution
if ($Help) {
    Show-Help
    exit 0
}

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator. Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

# Run main setup
Start-Setup