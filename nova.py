# Import the modules
import subprocess
import whisper # type: ignore
from simple_ai import SimpleAi
import logging
import threading


class Nova:
    def __init__(self, ai: SimpleAi, voice: str):
        self.voice = voice
        self.ai: SimpleAi = ai
        self.whisper = whisper.load_model("base")
        self.listener: subprocess.Popen | None = None
        self.process_thread: threading.Thread | None = None
        self.speaker: subprocess.Popen | None = None
    

    def start(self, prompt: str, temp_file):
        subprocess.run(['say', '-v', self.voice, prompt])
        self.listener = subprocess.Popen(['/opt/homebrew/bin/ffmpeg', '-y', '-f', 'avfoundation', '-i', ':default', '-t', '60', temp_file], stderr=subprocess.PIPE, text=True)
        logging.info("Listener started")
    

    def stop_listening(self):
        if not self.listener:
            return
        self.listener.terminate()
        _, stderr = self.listener.communicate()
        if self.listener.returncode != 255:
            logging.error(f"ffmpeg ERROR (code {self.listener.returncode}): {stderr}")
        self.listener = None
        logging.info("Listening completed")
    
    
    def process(self, nova_prime: bool, temp_file, callback):
        logging.info("Starting a processing thread")
        self.process_thread = threading.Thread(target=self._process, args=(nova_prime, temp_file, callback))
        self.process_thread.start()

    def _process(self, nova_prime: bool, temp_file, callback):
        logging.info(f"Transcribing file `{temp_file}`")
        result = self.whisper.transcribe(temp_file, fp16=False)
        if not self.process_thread:
            return

        # Log transcription
        logging.info(f"You said: {result["text"]}")

        answer = self.ai.chat(result["text"]) # pyright: ignore[reportArgumentType]
        if not self.process_thread:
            return

        if nova_prime:
            answer += ". Slay. Burn."

        logging.info(f"cybernetic intelligence response: {answer}")

        # Play the answer out of the speaker
        self.speaker = subprocess.Popen(['say', '-v', self.voice, answer])
        self.speaker.wait()
        callback()


    def stop_processing(self):
        logging.info("No longer processing")
        self.process_thread = None
        if self.speaker:
            self.speaker.terminate()


    def _wait_and_callback(self, callback):
        self.speaker.wait() # pyright: ignore[reportOptionalMemberAccess]
        callback()