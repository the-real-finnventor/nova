# Import the modules
import subprocess
import whisper
from simple_ai import SimpleAi
import logging


class Nova:
    def __init__(self, ai):
        self.ai: SimpleAi = ai
        self.whisper = whisper.load_model("base")
        self.listener = None
    
    def start(self, prompt: str, temp_file):
        subprocess.run(['say', prompt])

        logging.info("about to run popen")
        self.listener = subprocess.Popen(['/opt/homebrew/bin/ffmpeg', '-y', '-f', 'avfoundation', '-i', ':default', '-t', '60', temp_file], stderr=subprocess.PIPE, text=True)
        logging.info("listening (hopefully)")
        print("listening")
    
    def stop(self):
        if not self.listener:
            return
        self.listener.terminate()
        _, stderr = self.listener.communicate()
        if self.listener.returncode != 0:
            logging.error(f"ffmpeg ERROR (code {self.listener.returncode}): {stderr}")
        self.listener = None
        logging.info("done listening")
    
    def process(self, nova_prime: bool, temp_file):
        logging.info("transcribing", temp_file)
        result = self.whisper.transcribe(temp_file, fp16=False)
        # Print out what they said
        logging.info("you:", result["text"])

        answer = self.ai.chat(result["text"]) # pyright: ignore[reportArgumentType]

        if nova_prime:
            answer += ". Slay. Burn."

        # Print out the answer
        logging.info(answer)
        # Play the answer out of the speaker
        subprocess.run(['say', answer])