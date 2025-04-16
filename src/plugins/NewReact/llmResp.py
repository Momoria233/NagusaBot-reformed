from openai import OpenAI
import json
import os
from nonebot.adapters.onebot.v11 import Bot

api_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apikey.json")
with open(api_key_path, 'r', encoding='utf-8') as f:
    api_key_data = json.load(f)
    api_key = api_key_data.get("api_key")

client = OpenAI(
    api_key = api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

async def get_yulu_response(chat_history):
    jsonPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets/yulu.json")
    with open(jsonPath, 'r', encoding='utf-8') as f:
        yulu_data = json.load(f)
    # 修改系统提示，要求大模型返回文件名和理由
    init_msg = {
        "role": "system",
        "content": "你是一个群聊助手，需要读取提供的聊天记录，并从以下列表中选择一个最合适的回复对应的文件名返回。同时，请附带选择该文件的理由。文件名和理由之间请输出一个空格用于连接。文件名列表：" + ", ".join(yulu_data)
    }
    messages = [{"role": "user", "content": chat_history}]
    messages.insert(0, init_msg)
    response = client.chat.completions.create(
        model="qwen-turbo",
        messages=messages
    )
    llm_resp = response.choices[0].message.content.strip()
    parts = llm_resp.split(" ", 1)
    file_name = parts[0].strip()
    reason = parts[1].strip() if len(parts) > 1 else "没有提供理由"

    if file_name in yulu_data:
        ifIncluded = True
        return ifIncluded, file_name,reason
    else:
        ifIncluded = False
        return ifIncluded,file_name,reason

if __name__ == "__main__":
    chat_history = input()
    response = get_yulu_response(chat_history)
    print(response)
