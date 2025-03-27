# Nagusa Bot
-   开发中

## 现有功能

-   入群欢迎
-   吃饭功能
-   jm 下载（？）
-   还有不少 但是我还没写

## 部署方法

1. 安装 `pipx`

    > python -m pip install --user pipx  
    > python -m pipx ensurepath

    如果在此步骤的输出中出现了“open a new terminal”或者“re-login”字样，那么请关闭当前终端并重新打开一个新的终端。

2. 安装脚手架

    > pipx install nb-cli

    安装完成后，你可以在命令行使用 `nb` 命令来使用脚手架。如果出现无法找到命令的情况（例如出现“Command not found”字样），请参考 [pipx 文档](https://pypa.github.io/pipx/) 检查你的环境变量。

3. 克隆项目到本地

    > git clone https://github.com/Momoria233/NagusaBot.git  
    > cd NagusaBot

4. 配置 `.venv`

    > python3 -m venv .venv  
    > source .venv/bin/activate  
    > python -m pip install -r requirements.txt

5. 运行
    > nb run

## tbd

-   [ ] 更多的有趣功能
