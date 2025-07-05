"""
Quick installer for Continue Reading feature dependencies
Run this script to install the openai package
"""

import subprocess
import sys


def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False


def main():

    # Install modern openai package
    install_package("openai>=1.0.0")


if __name__ == "__main__":
    main()
