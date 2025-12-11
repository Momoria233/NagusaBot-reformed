from pathlib import Path
import os

class ResourceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
            # 项目根目录 (假设 src/common/resource.py 向上两级是根目录)
            current_file = Path(__file__).resolve()
            cls._instance.project_root = current_file.parents[2]
            
            # 统一的数据存储目录 (用于存放运行时产生的数据，如 sqlite, logs, caches)
            cls._instance.data_root = cls._instance.project_root / "data"
            cls._instance.data_root.mkdir(parents=True, exist_ok=True)

        return cls._instance

    def get_data_dir(self, plugin_name: str) -> Path:
        """
        获取指定插件的运行时数据目录 (data/plugins/<plugin_name>)
        如果目录不存在，会自动创建
        """
        path = self.data_root / "plugins" / plugin_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_bundled_asset_dir(plugin_file: str, asset_dir_name: str = "assets") -> Path:
        """
        获取插件自带的静态资源目录
        用法: assets_path = ResourceManager.get_bundled_asset_dir(__file__)
        """
        return Path(plugin_file).resolve().parent / asset_dir_name

resource_manager = ResourceManager()
