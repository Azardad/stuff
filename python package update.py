import subprocess
import sys

def get_installed_packages():
    """Get a list of installed packages using pip."""
    result = subprocess.run([sys.executable, "-m", "pip", "list", "--format", "freeze"], capture_output=True, text=True)
    packages = result.stdout.splitlines()
    return {pkg.split("==")[0]: pkg.split("==")[1] if "==" in pkg else "unknown" for pkg in packages}

def update_packages():
    """Update all installed packages using pip."""
    installed_packages = get_installed_packages()
    
    for package, version in installed_packages.items():
        print(f"Updating {package} (current version: {version})...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
            print(f"{package} updated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to update {package}. Error: {e}")

if __name__ == "__main__":
    update_packages()
