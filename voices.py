import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty("voices")

for i, voice in enumerate(voices):
    print(i, voice.name)
    engine.setProperty("voice", voice.id)
    engine.say(f"Hello, I am voice number {i}")
    engine.runAndWait()