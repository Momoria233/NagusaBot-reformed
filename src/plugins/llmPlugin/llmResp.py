from openai import OpenAI
import json
import os

client = OpenAI(
    api_key = "sk-43fcfecd08834873a61970157d4103a4",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def get_yulu_response(chat_history):
    jsonPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yulu.json")
    with open(jsonPath, 'r', encoding='utf-8') as f:
        yulu_data = json.load(f)
    init_msg = {
        "role": "system",
        "content": "你是一个群聊助手，需要读取提供的提供的聊天记录，并从以下列表中选择一个最合适的回复对应的文件名返回。不需要解释，只能返回文件名。 文件名列表： " + ", ".join(yulu_data)
    }
    messages = [{"role": "user", "content": chat_history}]
    messages.insert(0, init_msg)
    print(messages)
    response = client.chat.completions.create(
        model="qwen-turbo",
        messages=messages
    )
    print(response)
    llm_resp = response.choices[0].message.content
    if llm_resp in yulu_data:
        return llm_resp
    else:
        return "没有找到合适的回复，这是大模型的回复：" + llm_resp

if __name__ == "__main__":
    chat_history = input()
    response = get_yulu_response(chat_history)
    print(response)
