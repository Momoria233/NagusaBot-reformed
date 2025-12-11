import sys
import os
import json
from pathlib import Path

# Adjust path to import src
current_file = Path(__file__).resolve()
# We are in src/plugins/Legacy/Help/getGroupConfig.py
# Root is ../../../../
project_root = current_file.parents[4]
sys.path.insert(0, str(project_root))

try:
    from src.common.feature_manager import feature_manager
except ImportError:
    # Fallback if run from different cwd
    sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
    from src.common.feature_manager import feature_manager

def main():
    print(f"Config Path: {feature_manager.config_path}")
    feature_manager.load_config()
    
    while True:
        print("\n=== Group Config Manager ===")
        print("1. List all features")
        print("2. List group features")
        print("3. Toggle feature for group")
        print("4. Exit")
        
        choice = input("Select option: ")
        
        if choice == "1":
            features = feature_manager.config.get("all_features", {})
            for f, d in features.items():
                # Truncate description for display
                desc = d.replace("\n", " ")
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                print(f"[{f}]: {desc}")
                
        elif choice == "2":
            group_id = input("Enter Group ID: ")
            enabled = feature_manager.get_group_features(group_id)
            print(f"Enabled features for {group_id}:")
            if not enabled:
                print(" - None (or all disabled)")
            for f in enabled:
                print(f" - {f}")
                
        elif choice == "3":
            group_id = input("Enter Group ID: ")
            feature = input("Enter Feature Name: ")
            action = input("Enable (y) or Disable (n)? ")
            if action.lower() == 'y':
                feature_manager.set_feature(group_id, feature, True)
                print("Enabled.")
            else:
                feature_manager.set_feature(group_id, feature, False)
                print("Disabled.")
                
        elif choice == "4":
            break

if __name__ == "__main__":
    main()
