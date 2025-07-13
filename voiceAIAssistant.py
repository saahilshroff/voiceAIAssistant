import speech_recognition as sr
import pyttsx3
from openai import OpenAI
import requests
import logging
import os
import time
import webbrowser
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")  # Optional for weather
GPT_MODEL = 'gpt-4o-mini'

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY)
MAX_TOKENS = 500
TEMPERATURE = 0.15

# Conversation memory - keeps the conversation flowing naturally
conversation_history = []

end_conversation_list = ["exit", "quit", "goodbye", "stop assistant", "shut down"]
special_command_list = ["pause", "resume", "clear", "web", "search"]

class _TTS:
    engine = None
    rate = None
    def __init__(self):
        self.engine = pyttsx3.init()

    def start(self,text_):
        self.engine.say(text_)
        # Sleep for 30 seconds post response. else AI does not respond 
        # (bug: https://stackoverflow.com/questions/56032027/pyttsx3-runandwait-method-gets-stuck/57181260#57181260)
        if "Hello!" not in text_:
            time.sleep(30)
            
        self.engine.runAndWait()
        

class ConversationalAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = True
        self.tts_engine = pyttsx3.init()
        
        # Adjust for ambient noise on startup
        with self.microphone as source:
            logging.info("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source)
            
    def listen_to_user(self):
        """Listen for voice commands"""
        try:
            with self.microphone as source:
                logging.info("Listening... (I'm ready to chat!)")
                
                # Use timeout to prevent hanging
                audio = self.recognizer.listen(source, timeout = 5, phrase_time_limit=30)
                
                try:
                    command = self.recognizer.recognize_google(audio)
                    logging.info(f"User: {command}")
                    return command.lower()
                except sr.UnknownValueError:
                    logging.warning("Could not understand audio")
                    return None
                except sr.RequestError as e:
                    logging.error(f"❌ Speech recognition error: {e}")
                    return None
                    
        except sr.WaitTimeoutError:
            logging.info("Listening timeout - no speech detected")
            return None
        except Exception as e:
            logging.error(f"❌ Microphone error: {e}")
            return None

    def text_to_speech(self, text):
        """Convert text to speech with enhanced error handling"""
        tts = _TTS()
        tts.start(text)
        del tts  # Delete the instance after use
        logging.info("✅ Audio reply played successfully")

    def get_weather(self, city):
        """Get weather information"""
        if not WEATHER_API_KEY:
            return "I'd love to help with weather, but I need a weather API key. For now, I can help with many other topics!"
        
        try:
            base_url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'imperial'
            }
            
            response = requests.get(base_url, params=params)
            weather_data = response.json()
            
            if response.status_code == 200:
                main = weather_data['main']
                weather = weather_data['weather'][0]
                
                temperature = main['temp']
                description = weather['description']
                
                return f"The weather in {city} is {description} with a temperature of {temperature:.1f}°F."
            else:
                return f"I couldn't get weather information for {city}, but I can help with many other things!"
                
        except Exception as e:
            return "I'm having trouble getting weather info right now, but I'm here to chat about anything else!"

    def get_conversational_response(self, user_input):
        """Get a natural, conversational response from AI"""
        try:
            # Add user input to conversation history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Keep conversation history manageable (last 30 messages)
            if len(conversation_history) > 30:
                conversation_history.pop(0)
            
            # Enhanced system message for better conversation
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
                - Remember the conversation context
                - Be encouraging and positive
                - Always provide a meaningful response
                - Respond naturally as if you're having a real conversation!"""
            }
            
            # Create messages array
            messages = [system_message] + conversation_history
            
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to conversation history
            conversation_history.append({"role": "assistant", "content": ai_response})
            
            logging.info(f"✅ AI Response generated: {ai_response}")
            
            return ai_response
            
        except Exception as e:
            logging.error(f"❌ Error getting AI response: {e}")
            return "I'm having a little trouble right now, but I'm still here to chat! Try asking me something else."

    def handle_special_commands(self, command):
        """Handle special commands that aren't general conversation"""
        
        # Exit commands
        if any(word in command for word in end_conversation_list):
            self.text_to_speech("It was great talking with you! Goodbye!")
            return "exit"
        
        # Pause listening
        elif "stop listening" in command or "pause" in command:
            self.text_to_speech("I'll pause for a moment. Say 'start listening' when you're ready to chat again.")
            self.is_listening = False
            return "pause"
        
        # Resume listening  
        elif "start listening" in command or "resume" in command:
            self.text_to_speech("I'm back! What would you like to talk about?")
            self.is_listening = True
            return "resume"
        
        # Clear conversation
        elif "clear conversation" in command or "forget conversation" in command or "start over" in command:
            conversation_history.clear()
            self.text_to_speech("Fresh start! I've cleared our conversation. What's on your mind?")
            return "clear"
        
        # Web browsing - but make it conversational
        elif "open google" in command or "open chrome" in command:
            self.text_to_speech("Opening Google for you!")
            webbrowser.open('https://google.com')
            return "web"
        
        elif "open youtube" in command:
            self.text_to_speech("Opening YouTube! Enjoy!")
            webbrowser.open('https://youtube.com')
            return "web"
        
        # Search commands
        elif "search for" in command or "google" in command:
            # Extract search query
            query = command.replace("search for", "").replace("google", "").strip()
            if query:
                search_url = f"https://google.com/search?q={query.replace(' ', '+')}"
                self.text_to_speech(f"Searching for {query}! Here you go.")
                webbrowser.open(search_url)
                return "search"
        
        return None  # Not a special command, handle as conversation

    def run(self):
        greeting_message = "Hello! I'm your conversational assistant. I love to chat about anything and everything! What's on your mind today?"
        """Main assistant loop"""
        logging.info("🚀 Conversational Voice Assistant Starting...")
        logging.info("💬 I'm here to chat about ANYTHING:")
        logging.info("🎯 Special commands:")
        logging.info("  • 'Clear conversation' - Start fresh")
        logging.info("  • 'Stop listening' - Pause")
        logging.info("  • 'Exit' - End conversation")
        logging.info("-" * 60)
        logging.info(f"✅ AI Response generated: {greeting_message}");
        
        # Initial greeting
        self.text_to_speech(greeting_message)
        
        while True:
            if self.is_listening:
                command = self.listen_to_user()
                if command:
                    logging.info(f"🎤 Processing command: {command}")
                    
                    # First check for special commands
                    special_result = self.handle_special_commands(command)
                    
                    if special_result == "exit":
                        break
                    elif special_result in special_command_list:
                        continue  # Special command handled
                    else:
                        # Handle as general conversation
                        if "weather" in command:
                            # Extract city if mentioned
                            if " in " in command:
                                try:
                                    city = command.split(" in ")[1].strip()
                                except:
                                    pass
                            
                            weather_info = self.get_weather(city)
                            self.text_to_speech(weather_info)
                        else:
                            logging.info("🤖 Getting AI response...")
                            response = self.get_conversational_response(command)
                            logging.info("🔊 Playing audio reply...")
                            self.text_to_speech(response)
            else:
                # When paused, only listen for resume command
                command = self.listen_to_user()
                if command and ("start listening" in command or "resume" in command):
                    self.handle_special_commands(command)

def main():
    assistant = ConversationalAssistant()
    
    try:
        assistant.run()
    except KeyboardInterrupt:
        print("\n👋 Chat ended by user")
        assistant.text_to_speech("Thanks for chatting! Goodbye!")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        logging.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()