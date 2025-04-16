import os
from huggingface_hub import snapshot_download

def download_model():
    try:
        # Create models directory if it doesn't exist
        models_dir = os.path.join(os.path.dirname(__file__), "models")
        os.makedirs(models_dir, exist_ok=True)
        
        # Download the phi2-sqlcoder model
        local_dir = snapshot_download(
            repo_id="pavankumarbalijepalli/phi2-sqlcoder",
            local_dir=os.path.join(models_dir, "sql-model"),
            local_dir_use_symlinks=False
        )
        
        print(f"Model successfully downloaded to: {local_dir}")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    download_model()