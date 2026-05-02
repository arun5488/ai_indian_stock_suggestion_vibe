import os

def create_app_structure(app_name: str):
    # Define the folder structure relative to app_name
    folders = [
        f"{app_name}/backend/app/models",
        f"{app_name}/backend/app/routes",
        f"{app_name}/backend/app/services",
        f"{app_name}/backend/app/services/agents",   # AI agents folder
        f"{app_name}/backend/app/utils",
        f"{app_name}/backend/app/db",
        f"{app_name}/backend/tests",
        f"{app_name}/frontend/src/components",
        f"{app_name}/frontend/src/pages",
        f"{app_name}/frontend/src/services",
        f"{app_name}/frontend/src/store",
        f"{app_name}/frontend/src/utils",
        f"{app_name}/frontend/public",
        f"{app_name}/data/raw",
        f"{app_name}/data/processed",
        f"{app_name}/data/scripts",
        f"{app_name}/docs"
    ]

    # Create folders
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        # Add __init__.py for Python packages inside backend/app
        if "backend/app" in folder:
            init_file = os.path.join(folder, "__init__.py")
            with open(init_file, "w") as f:
                f.write("# Package initializer\n")

    # Create placeholder files at root level
    files = {
        f"{app_name}/backend/app/main.py": "",
        f"{app_name}/backend/app/config.py": "",
        f"{app_name}/requirements.txt": "",          # moved to root
        f"{app_name}/frontend/package.json": "",
        f"{app_name}/docker-compose.yml": "",
        f"{app_name}/README.md": ""
    }

    for filepath, content in files.items():
        with open(filepath, "w") as f:
            f.write(content)

    print(f"✅ Folder structure for '{app_name}' created successfully with __init__.py files and root-level requirements.txt!")

# Example usage
if __name__ == "__main__":
    create_app_structure("ai_indian_stock_suggestion")
