import pyttsx3
import threading
import time

class VoiceControl:
    def __init__(self):
        self.engine = None
        self.active = True  # Activado por defecto
        self.initialized = False
        self.lock = threading.Lock()
        self.initialize_engine()

    def initialize_engine(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            self.engine.setProperty('rate', 160)
            self.engine.setProperty('volume', 1.0)
            # Seleccionar voz en español si está disponible
            for voice in voices:
                if 'spanish' in voice.languages or 'es' in voice.languages:
                    self.engine.setProperty('voice', voice.id)
                    break
            self.initialized = True
        except Exception as e:
            print(f"Error al inicializar TTS: {e}")
            self.initialized = False

    def speak(self, text):
        if not self.active or not self.initialized:
            return
            
        def speak_thread():
            try:
                with self.lock:
                    self.engine.say(text)
                    self.engine.runAndWait()
            except Exception as e:
                print(f"Error al reproducir voz: {e}")
                # Reintentar inicialización
                time.sleep(1)
                self.initialize_engine()

        threading.Thread(target=speak_thread, daemon=True).start()

    def toggle(self):
        with self.lock:
            self.active = not self.active
            if self.active and not self.initialized:
                self.initialize_engine()
        return self.active

# Instancia global
voice_control = VoiceControl()