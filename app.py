import os
from dotenv import load_dotenv
from openai import OpenAI

MODEL = "llama3.2"
openai = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

system_message = "You are a helful assistant"

message = "Tell me 5 question on the toic of 'Artificial Intelligence' and give me the answer to each question. "
messages = [{"role": "system", "content": system_message}]+ [{"role": "user", "content": message}]


print("And messages is:")
print(messages)

stream = openai.chat.completions.create(
    model=MODEL, 
    messages=messages, 
    stream=True
    )

response = ""
for chunk in stream:
    response += chunk.choices[0].delta.content or ''

print("Response is:")
print(response)