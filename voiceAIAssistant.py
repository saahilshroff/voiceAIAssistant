import speech_recognition as sr
import pyttsx3
from openai import OpenAI
import requests
import logging
import os
import time
import webbrowser
from dotenv import load_dotenv

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# OpenAI configuration
GPT_MODEL = 'gpt-4o-mini'
MAX_TOKENS = 500
TEMPERATURE = 0.15

# Initialize OpenAI client
if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

client = OpenAI(api_key=OPENAI_KEY)

# Conversation memory for context continuity
conversation_history = []

# Command lists for easier maintenance
END_CONVERSATION_COMMANDS = ["exit", "quit", "goodbye", "stop assistant", "shut down"]
SPECIAL_COMMANDS = ["pause", "resume", "clear", "web", "search"]


class TTSEngine:
    """
    Text-to-Speech engine class.
    """
    
    def __init__(self):
        """Initialize the TTS engine."""
        self.engine = pyttsx3.init()
        self._configure_voice()
    
    def _configure_voice(self):
        """Configure voice properties for better speech quality."""
        voices = self.engine.getProperty('voices')
        if voices:
            # Use first available voice (can be customized)
            self.engine.setProperty('voice', voices[0].id)
        
        # Set speech rate (words per minute)
        self.engine.setProperty('rate', 180)
        
        # Set volume (0.0 to 1.0)
        self.engine.setProperty('volume', 0.9)
    
    def speak(self, text):
        """
        Convert text to speech with bug mitigation.
        
        Args:
            text (str): Text to be spoken
        """
        try:
            self.engine.say(text)
            
            # Sleep for xx seconds post response. else AI does not respond (pyaudio didn't help either)
            # (reference: https://stackoverflow.com/questions/56032027/pyttsx3-runandwait-method-gets-stuck/57181260#57181260)
            if "Hello!" not in text:
                time.sleep(25)
            
            self.engine.runAndWait()
            logging.info("✅ Text-to-speech completed successfully")
            
        except Exception as e:
            logging.error(f"❌ TTS error: {e}")


class ConversationalAssistant:
    """
    Main voice assistant class that handles speech recognition, conversation management, and response generation.
    """
    
    def __init__(self):
        """Initialize the voice assistant components."""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = True
        self.tts = TTSEngine()
        
        # Configure speech recognition sensitivity
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        
        # Calibrate microphone for ambient noise
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise on startup."""
        try:
            with self.microphone as source:
                logging.info("🎤 Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                logging.info("✅ Microphone calibrated successfully")
        except Exception as e:
            logging.error(f"❌ Microphone calibration failed: {e}")
    
    def listen_for_speech(self):
        """
        Listen for voice input from the user.
        
        Returns:
            str or None: Recognized speech text, or None if no speech detected
        """
        try:
            with self.microphone as source:
                logging.info("🎧 Listening for speech...")
                
                # Listen with timeout to prevent hanging
                audio = self.recognizer.listen(
                    source, 
                    timeout=7,  # Stop listening after x seconds of silence
                    phrase_time_limit=45  # Maximum phrase duration
                )
                
                # Convert audio to text using Google Speech Recognition
                try:
                    command = self.recognizer.recognize_google(audio)
                    logging.info(f"👤 User said: {command}")
                    return command.lower()
                    
                except sr.UnknownValueError:
                    logging.warning("⚠️ Could not understand audio")
                    return None
                    
                except sr.RequestError as e:
                    logging.error(f"❌ Speech recognition service error: {e}")
                    return None
                    
        except sr.WaitTimeoutError:
            # Normal timeout - no speech detected
            return None
            
        except Exception as e:
            logging.error(f"❌ Microphone error: {e}")
            return None
    
    def get_weather_info(self, city):
        """
        Fetch weather information for a given city.
        
        Args:
            city (str): City name for weather query
            
        Returns:
            str: Weather information or error message
        """
        if not WEATHER_API_KEY:
            return ("I'd love to help with weather, but I need a weather API key. "
                   "For now, I can help with many other topics!")
        
        try:
            base_url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'imperial'  # Use Fahrenheit
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            
            if 200 == response.status_code:
                weather_data = response.json()
                main = weather_data['main']
                weather = weather_data['weather'][0]
                
                temperature = main['temp']
                description = weather['description']
                feels_like = main['feels_like']
                humidity = main['humidity']
                
                return (f"The weather in {city} is {description} with a temperature "
                       f"of {temperature:.1f}°F, feels like {feels_like:.1f}°F. "
                       f"Humidity is {humidity}%.")
            else:
                return f"I couldn't get weather information for {city}. Please try another city."
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Weather API request failed: {e}")
            return "I'm having trouble getting weather info right now, but I'm here to chat about anything else!"
        
        except Exception as e:
            logging.error(f"Weather function error: {e}")
            return "Weather service is temporarily unavailable, but I can help with other topics!"
    
    def generate_ai_response(self, user_input):
        """
        Generate a conversational response using OpenAI's GPT.
        
        Args:
            user_input (str): User's message
            
        Returns:
            str: AI-generated response
        """
        try:
            # Add user input to conversation history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Maintain conversation history size (keep last 20 messages)
            if len(conversation_history) > 20:
                conversation_history.pop(0)
            
            # System message to define AI personality and behavior
            system_message = {
                "role": "system", 
                "content": """You are a friendly, helpful, and conversational voice assistant. 
                
                Key traits:
                - Be natural and conversational, like talking to a friend
                - Keep responses concise but informative (1-3 sentences usually)
                - Show personality and enthusiasm when appropriate
                - Ask follow-up questions to keep conversation flowing
                - Be helpful with any topic: science, history, math, advice, entertainment, etc.
                - If you don't know something recent, acknowledge it but still try to help
                - Remember the conversation context from previous messages
                - Be encouraging and positive
                - Always provide a meaningful response
                - Respond naturally as if you're having a real conversation
                - Avoid overly long responses since this is voice-based interaction"""
            }
            
            # Create messages array with system message and conversation history
            messages = [system_message] + conversation_history
            
            # Generate response using OpenAI API
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to conversation history
            conversation_history.append({"role": "assistant", "content": ai_response})
            
            logging.info(f"🤖 AI Response: {ai_response}")
            return ai_response
            
        except Exception as e:
            logging.error(f"❌ Error getting AI response: {e}")
            return ("I'm having a little trouble right now, but I'm still here to chat! "
                   "Try asking me something else.")
    
    def handle_special_commands(self, command):
        """
        Process special voice commands that aren't general conversation.
        
        Args:
            command (str): User's voice command
            
        Returns:
            str or None: Command result ("exit", "pause", etc.) or None if not a special command
        """
        # Exit commands
        if any(word in command for word in END_CONVERSATION_COMMANDS):
            self.tts.speak("It was great talking with you! Goodbye!")
            return "exit"
        
        # Pause listening
        elif any(phrase in command for phrase in ["stop listening", "pause"]):
            self.tts.speak("I'll pause for a moment. Say 'start listening' when you're ready to chat again.")
            self.is_listening = False
            return "pause"
        
        # Resume listening  
        elif any(phrase in command for phrase in ["start listening", "resume"]):
            self.tts.speak("I'm back! What would you like to talk about?")
            self.is_listening = True
            return "resume"
        
        # Clear conversation history
        elif any(phrase in command for phrase in ["clear conversation", "forget conversation", "start over"]):
            conversation_history.clear()
            self.tts.speak("Fresh start! I've cleared our conversation. What's on your mind?")
            return "clear"
        
        # Web browsing commands
        elif any(phrase in command for phrase in ["open google", "open chrome"]):
            self.tts.speak("Opening Google for you!")
            webbrowser.open('https://google.com')
            return "web"
        
        elif "open youtube" in command:
            self.tts.speak("Opening YouTube! Enjoy!")
            webbrowser.open('https://youtube.com')
            return "web"
        
        # Search commands
        elif any(phrase in command for phrase in ["search for", "google"]):
            # Extract search query
            query = command.replace("search for", "").replace("google", "").strip()
            if query:
                search_url = f"https://google.com/search?q={query.replace(' ', '+')}"
                self.tts.speak(f"Searching for {query}! Here you go.")
                webbrowser.open(search_url)
                return "search"
        
        return None  # Not a special command
    
    def process_weather_command(self, command):
        """
        Process weather-related commands and extract city if mentioned.
        
        Args:
            command (str): User's weather command
            
        Returns:
            str: Weather information
        """
        city = "New York"  # Default city
        
        # Try to extract city from command
        if " in " in command:
            try:
                city = command.split(" in ")[1].strip()
                # Remove common trailing words
                city = city.replace(" please", "").replace(" today", "")
            except IndexError:
                pass
        elif " for " in command:
            try:
                city = command.split(" for ")[1].strip()
                city = city.replace(" please", "").replace(" today", "")
            except IndexError:
                pass
        
        return self.get_weather_info(city)
    
    def run(self):
        """Main assistant loop that handles voice interaction."""
        
        # Startup message
        greeting_message = ("Hello! I'm your conversational assistant. "
                           "I love to chat about anything and everything! "
                           "What's on your mind today?")
        
        # Display startup information
        logging.info("🚀 Conversational Voice Assistant Starting...")
        logging.info("💬 Ready to chat about ANY topic!")
        logging.info("🎯 Special commands available:")
        logging.info("  • 'Clear conversation' - Start fresh")
        logging.info("  • 'Stop listening' - Pause assistant")
        logging.info("  • 'Start listening' - Resume assistant")
        logging.info("  • 'Open Google/YouTube' - Web browsing")
        logging.info("  • 'Search for [query]' - Google search")
        logging.info("  • 'Weather in [city]' - Weather info")
        logging.info("  • 'Exit/Quit/Goodbye' - End session")
        logging.info("-" * 60)
        
        # Initial greeting
        self.tts.speak(greeting_message)
        
        # Main conversation loop
        while True:
            if self.is_listening:
                # Listen for user input
                command = self.listen_for_speech()
                
                if command:
                    logging.info(f"🎤 Processing: {command}")
                    
                    # Check for special commands first
                    special_result = self.handle_special_commands(command)
                    
                    if special_result == "exit":
                        break
                    elif special_result in SPECIAL_COMMANDS:
                        continue  # Special command was handled
                    
                    # Handle weather queries
                    elif "weather" in command:
                        weather_info = self.process_weather_command(command)
                        self.tts.speak(weather_info)
                    
                    # Handle general conversation
                    else:
                        logging.info("🤖 Generating AI response...")
                        response = self.generate_ai_response(command)
                        logging.info("🔊 Speaking response...")
                        self.tts.speak(response)
            
            else:
                # When paused, only listen for resume command
                command = self.listen_for_speech()
                if command and any(phrase in command for phrase in ["start listening", "resume"]):
                    self.handle_special_commands(command)


def main():
    """Main entry point for the voice assistant."""
    
    # Verify required environment variables
    if not OPENAI_KEY:
        logging.error("❌ OPENAI_API_KEY environment variable is required")
        print("Please set your OPENAI_API_KEY in your .env file")
        return
    
    # Initialize and run the assistant
    assistant = ConversationalAssistant()
    
    try:
        assistant.run()
        
    except KeyboardInterrupt:
        print("\n👋 Voice assistant ended by user")
        logging.info("Assistant stopped by user (Ctrl+C)")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        logging.error(f"Fatal error: {e}")


if __name__ == '__main__':
    main()