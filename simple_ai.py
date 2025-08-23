from ollama import chat
from typing import Literal


class SimpleAi:
  _messages: list[dict]
  _model:str

  def __init__(self, model: str, system_prompt: str|None = None):
    self._messages: list[dict] = list()
    if system_prompt:
      self._messages.append(
          {'role': 'system', 'content': system_prompt}
      )
    self._model = model
  
  def chat(self, message:str) -> str:
      self._messages.append(
          {'role': 'user', 'content': message}
      )
      response = chat(
            model=self._model,
            messages=self._messages,
            stream=False,
      ) # type: ignore
      self._messages.append(response["message"])
      return response["message"]["content"]