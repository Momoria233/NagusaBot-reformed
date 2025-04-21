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
        "content": "你是一个群聊助手，需要读取提供的提供的聊天记录，并从以下列表中选择一个最合适的回复对应的文件名返回。不需要解释，只能返回文件名。返回的时候请有一点创意和恶趣味。文件名列表：" + ", ".join(yulu_data)
    }
    messages = [{"role": "user", "content": chat_history}]
    messages.insert(0, init_msg)
    response = client.chat.completions.create(
        model="qwen-turbo",
        messages=messages
    )
    llm_resp = response.choices[0].message.content
    if llm_resp in yulu_data:
        return True, llm_resp
    else:
        return False, llm_resp

async def get_yulu_reason(chat_history,respFile):
    init_msg = {
        "role": "system",
        "content": "你是一个群聊助手，需要读取提供的P回复，然后阅读提供的聊天记录。最后以简短有逻辑性的语言输出P回复和聊天记录之间的关系。你的输出要以“笑点解析：”为开头，随后直接输出理由。注意，输出理由的时候不能带有“P回复”这个词。"
    }
    msgContent = "P回复：" + respFile + "\n聊天记录：" + chat_history
    messages = [{"role": "user", "content": msgContent}]
    messages.insert(0, init_msg)
    response = client.chat.completions.create(
        model="qwen-turbo",
        messages=messages
    )
    llm_resp = response.choices[0].message.content
    return llm_resp

if __name__ == "__main__":
    chat_history = input()
    response = get_yulu_response(chat_history)
    print(response)
