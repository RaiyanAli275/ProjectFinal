import gdown
import zipfile
from pathlib import Path

# Get the current script's directory (e.g., backend/)
backend_path = Path(__file__).resolve().parent

# Download FAISS.zip into the same directory
file_id = "1ZOnG8SffQpuLpwNOKaR8c5JtMt0LJBMN"
url = f"https://drive.google.com/uc?id={file_id}"
output_zip = backend_path / "FAISS.zip"

gdown.download(url, output=str(output_zip), quiet=False)

# Extract contents into the backend directory
with zipfile.ZipFile(output_zip, 'r') as zip_ref:
    zip_ref.extractall(backend_path)
