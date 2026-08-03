import pyttsx3

engine = pyttsx3.init("sapi5")
engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)

voices = engine.getProperty("voices")

print("Available voices:")
for i, voice in enumerate(voices):
    print(i, voice.name)

if voices:
    engine.setProperty("voice", voices[0].id)

print("Speaking now...")
engine.say("Aurix voice test is working.")
engine.runAndWait()
print("Done.")