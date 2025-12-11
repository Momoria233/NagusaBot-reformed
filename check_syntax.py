import sys
import os

# Add src to path
sys.path.append(os.getcwd())

print("Checking syntax (compile only)...")

files_to_check = [
    "src/common/config.py",
    "src/common/resource.py",
    "src/common/feature_manager.py",
    "src/common/database.py",
    "src/common/models.py",
    "src/plugins/Legacy/totalReact-legacy/__init__.py",
    "src/plugins/Legacy/welcome/__init__.py",
    "src/plugins/Legacy/autoGroupAcception/__init__.py",
    "src/plugins/Legacy/birthday/__init__.py",
    "src/plugins/Legacy/jm/__init__.py",
    "src/plugins/Legacy/jm/jmdownload.py",
    "src/plugins/reform/manosoba-image-generator/__init__.py",
    "src/plugins/reform/manosoba-image-generator/Utils.py",
    "src/plugins/reform/uniRecall/__init__.py",
]

for p in files_to_check:
    if not os.path.exists(p):
        print(f"⚠️ File not found: {p}")
        continue
        
    try:
        with open(p, 'r', encoding='utf-8') as f:
            compile(f.read(), p, 'exec')
        print(f"✅ Syntax OK: {p}")
    except Exception as e:
        print(f"❌ Syntax Error in {p}: {e}")
