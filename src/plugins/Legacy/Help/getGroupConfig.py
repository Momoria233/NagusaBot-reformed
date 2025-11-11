#Unfinished
#临时使用config.py记录现有whitelist 后续群增加之后再完善这个文件


import os
import importlib
import sys

def load_group_configs(plugins_path):
    configs = {}
    for plugin_dir in os.listdir(plugins_path):
        plugin_path = os.path.join(plugins_path, plugin_dir)
        if os.path.isdir(plugin_path):
            config_file = os.path.join(plugin_path, "config.py")
            if os.path.exists(config_file):
                try:
                    # Dynamically import the config.py file as a module
                    module_name = f".{plugin_dir}.config"  # Construct module name
                    if hasattr(importlib, 'whitelist'):
                        spec = importlib.util.spec_from_file_location(module_name, config_file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                    else:
                        # Fallback for older Python versions
                        module = importlib.import_module(f".{plugin_dir}.config", "Config")


                    configs[plugin_dir] = module  # Store the module itself
                except Exception as e:
                    print(f"Error loading config for plugin {plugin_dir}: {e}")
    return configs

if __name__ == '__main__':
    # Example usage:
    plugins_directory = os.path.join(os.path.dirname(__file__), "..")  # Assuming this script is in src/plugins/help
    all_configs = load_group_configs(plugins_directory)

    if all_configs:
        for plugin_name, config_module in all_configs.items():
            print(f"Loaded config for plugin: {plugin_name}")
            # Access configuration variables from the config_module
            # Example: print(config_module.YOUR_VARIABLE)
    else:
        print("No plugin configurations found.")