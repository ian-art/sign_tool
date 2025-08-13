import subprocess
import platform
from pathlib import Path
import getpass
import sys
import tkinter as tk
from tkinter import filedialog

def is_64bit_windows():
    return platform.machine().endswith('64')

def select_exe_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select the .exe file to sign",
        filetypes=[("Executable files", "*.exe")]
    )
    return Path(file_path) if file_path else None

def run_command(command, error_message):
    try:
        print(f"\n💻 Running: {' '.join(str(x) for x in command)}")
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print(f"❌ {error_message}")
        sys.exit(1)

def generate_self_signed_pfx(pfx_path, password):
    print("🛠️ Generating a self-signed certificate and saving to:", pfx_path)
    cert_subject = "CN=ART"

    run_command([
        "powershell", "-Command",
        f'New-SelfSignedCertificate -Type CodeSigningCert -Subject "{cert_subject}" -CertStoreLocation "Cert:\\CurrentUser\\My"'
    ], "Failed to create self-signed certificate.")

    run_command([
        "powershell", "-Command",
        f'$pwd = ConvertTo-SecureString -String "{password}" -Force -AsPlainText; '
        f'$cert = Get-ChildItem Cert:\\CurrentUser\\My | Where-Object {{$_.Subject -eq "{cert_subject}"}} | Select-Object -First 1; '
        f'Export-PfxCertificate -Cert $cert -FilePath "{pfx_path.resolve()}" -Password $pwd'
    ], "Failed to export the certificate to .pfx")

def main():
    exe_path = select_exe_file()
    if not exe_path or not exe_path.exists():
        print("❌ No .exe file selected. Exiting.")
        return

    password = getpass.getpass("🔑 Enter password for the .pfx certificate: ")

    # Use bin/pfx/mycert.pfx
    pfx_dir = Path("bin/pfx")
    pfx_file = pfx_dir / "mycert.pfx"

    if not pfx_file.exists():
        print("⚠️ .pfx certificate not found. Creating new one...")
        pfx_dir.mkdir(parents=True, exist_ok=True)
        generate_self_signed_pfx(pfx_file, password)

    # Choose 64-bit or 32-bit signtool
    signtool_path = Path("bin/SignTool-10.0.22621.6-x64/signtool.exe") if is_64bit_windows() else Path("bin/SignTool-10.0.22621.6-x86/signtool.exe")
    if not signtool_path.exists():
        print(f"❌ Could not find SignTool at {signtool_path}")
        return

    print(f"🔏 Signing {exe_path.name}...")
    run_command([
        str(signtool_path),
        "sign",
        "/f", str(pfx_file),
        "/p", password,
        "/tr", "http://timestamp.digicert.com",
        "/td", "sha256",
        "/fd", "sha256",
        "/v", str(exe_path)
    ], "Failed to sign the executable.")

    print("\n🔍 Verifying the signature...")
    run_command([
        str(signtool_path),
        "verify",
        "/pa",
        "/v",
        str(exe_path)
    ], "Signature verification failed.")

    print("\n✅ Done! The .exe is signed and verified.")

if __name__ == "__main__":
    main()
