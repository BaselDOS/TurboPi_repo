from speech import speech, awake

class SpeechIO:
    def __init__(self):
        self.port = '/dev/ttyUSB0'

        self.kws = awake.WonderEchoPro(self.port)

        self.asr = speech.RealTimeOpenAIASR()
        self.asr.update_session(model='whisper-1')

        self.tts = speech.RealTimeOpenAITTS()

        speech.set_volume(80)

    def start(self):
        self.kws.start()

    def wait_wakeup(self):
        return self.kws.wakeup()

    def listen(self):
        print("Listening...")
        return self.asr.asr()

    def speak(self, text):
        print("Speaking:", text)
        self.tts.tts(text)
