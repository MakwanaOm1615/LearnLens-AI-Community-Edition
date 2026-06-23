import os
from huggingface_hub import HfApi

print("===========================================")
print("🚀 Hugging Face Space Auto-Deployer 🚀")
print("===========================================\n")

# 1. Get Token
print("To upload your files, you need your Hugging Face Access Token.")
print("You can create one here: https://huggingface.co/settings/tokens (Make sure it has 'Write' permissions!)")
token = input("\nPaste your HF Token here: ").strip()

if not token.startswith("hf_"):
    print("Error: Invalid token. It should start with 'hf_'")
    exit(1)

# 2. Upload Files
print("\nUploading files to Omverse/rag-ai-assistant...")
api = HfApi()

try:
    api.upload_folder(
        folder_path=".",
        repo_id="Omverse/rag-ai-assistant",
        repo_type="space",
        allow_patterns=[
            "app.py", 
            "requirements.txt", 
            "models/*", 
            "providers/*", 
            "processors/*", 
            "storage/*", 
            "ui/*"
        ],
        token=token,
        commit_message="V2 Architecture Deployment"
    )
    print("\n✅ SUCCESS! All files uploaded to your Space.")
    print("Check it out here: https://huggingface.co/spaces/Omverse/rag-ai-assistant")
    
    print("\n⚠️ IMPORTANT FINAL STEP:")
    print("Go to your Space Settings (https://huggingface.co/spaces/Omverse/rag-ai-assistant/settings)")
    print("Scroll down to 'Variables and secrets', click 'New secret'")
    print("Name: HF_TOKEN")
    print("Value: (paste your token here again)")
    
except Exception as e:
    print(f"\n❌ Error uploading files: {e}")
