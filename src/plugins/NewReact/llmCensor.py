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

def recentMsgCensor(chat_history,react):
    init_msg = {
        "role": "system",
        "content": "你是一个群聊助手，需要读取提供的提供的聊天记录，并判断是否适合此时说出相应的话语。注意：不适合返回的情况只有非常非常严重的情况，大部分聊天记录都是在开玩笑，都可以判断为适合。如果适合，请你只返回True,如果不适合，请你返回相应的理由。"
    }
    messages = [{"role": "user", "content": f"聊天记录是：{chat_history},要说出的话是：{react}。"}]
    messages.insert(0, init_msg)
    print(messages)
    response = client.chat.completions.create(
        model="qwen-turbo",
        messages=messages
    )
    print(response)
    llm_resp = response.choices[0].message.content
    if llm_resp == "True":
        return True , "适合"
    else:
        return False, llm_resp