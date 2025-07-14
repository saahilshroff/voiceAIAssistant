# 🗣️ Conversational Voice Assistant

A voice-based conversational assistant built with `OpenAI GPT`, `speech_recognition`, and `pyttsx3`. It listens to your voice, chats naturally, fetches weather info, performs web searches, and more.

---

## 🚀 Features

- 🎤 Voice input via Google Speech Recognition
- 🤖 Natural AI responses using OpenAI GPT (`gpt-4o-mini`)
- 🔊 Text-to-speech output with `pyttsx3`
- 🌦️ Weather updates via `OpenWeatherMap`
- 🌐 Web commands: `search`, `open Google/YouTube`
- 🧠 Maintains short-term memory of conversation
- ⏸️ Supports pause/resume and clear conversation

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/<yourusername>/voice-assistant.git
cd voice-assistant
```

---


### 2. Install Dependencies

```bash
pip install -r requirements.txt
```
---

### 3. Configure Environment Variables
Create a .env file in the project root:
```bash
OPENAI_API_KEY= <Openai_api_key_here>
WEATHER_API_KEY=<Openweathermap_api_key_here>
```
---

### 4. Usage
Start the assistant with:
```bash
python voiceAIAssistant.py
```
---

## 🎯 Supported Voice Commands
### General Chat
```bash
"Tell me a joke", "Who is Albert Einstein?", "How do black holes work?"
```

### Weather
```bash
"What's the weather in Seattle?", "Weather for New York today"
```

### Web Actions
```bash
"Open Google", "Open YouTube", "Search for climate change solutions"
```

### Assistant Controls
```bash
"Stop listening" → Pause  
"Start listening" → Resume  
"Clear conversation" → Reset memory  
"Goodbye" / "Exit" / "Quit" → End session
```

## 🔧 Next steps
#### Add Interruption Support
Allow the user to interrupt the assistant mid-response.
#### UI Integration
Build a simple UI for toggling controls
#### Bug fixes
Improve TTS delay handling, and reduce false positives.
#### Web search
Improve web searching feature