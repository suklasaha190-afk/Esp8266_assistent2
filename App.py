from flask import Flask, request, send_file
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
import os

app = Flask(__name__)

# ওয়াইফাই মোড ট্র্যাক করার জন্য গ্লোবাল ভ্যারিয়েবল
# মোডগুলো হতে পারে: "NORMAL", "WIFI_NAME", "WIFI_PASS"
current_mode = "NORMAL"

@app.route('/process_audio', methods=['POST'])
def process_audio():
    global current_mode
    
    print("\n--- New Request Received from ESP8266 ---")
    
    # ESP8266 থেকে আসা র (Raw) অডিও ডেটা রিসিভ করা
    audio_data = request.data
    audio_path = "incoming.wav"
    
    # ডেটাটিকে একটি WAV ফাইল হিসেবে লোকালি সেভ করা
    with open(audio_path, "wb") as f:
        f.write(audio_data)
        
    recognizer = sr.Recognizer()
    try:
        # সেভ হওয়া অডিও ফাইলটি স্পিচ রিকগনিশন ইঞ্জিনে পাঠানো
        with sr.AudioFile(audio_path) as source:
            audio_file_data = recognizer.record(source)
            
        # গুগলের ফ্রি এপিআই ব্যবহার করে কথাকে টেক্সটে রূপান্তর করা
        text_response = recognizer.recognize_google(audio_file_data).lower()
        print(f"User Spoke: {text_response}")
        
        # ----------------------------------------------------
        # ১. ওয়েক ওয়ার্ড এবং মোড পরিবর্তনের লজিক (NORMAL MODE)
        # ----------------------------------------------------
        if current_mode == "NORMAL":
            if "hey esp" in text_response:
                return generate_audio_response("Yes, I am listening. Tell me.")
                
            elif "wifi name" in text_response:
                current_mode = "WIFI_NAME"
                print("Status: Switched to WIFI_NAME mode.")
                return generate_audio_response("WiFi Name mode activated. Please spell the name.")
                
            elif "wifi password" in text_response:
                current_mode = "WIFI_PASS"
                print("Status: Switched to WIFI_PASS mode.")
                return generate_audio_response("WiFi Password mode activated. Please spell the password.")
            
            # সাধারণ কিছু কথোপকথন (উদাহরণস্বরূপ)
            elif "how are you" in text_response:
                return generate_audio_response("I am doing great, thank you.")
            else:
                return generate_audio_response("I processed your request, but please repeat clearly.")

        # ----------------------------------------------------
        # ২. লেটার বাই লেটার ওয়াইফাই নাম প্রসেস করা
        # ----------------------------------------------------
        elif current_mode == "WIFI_NAME":
            # "s o h a m" বা "s, o, h, a, m" থেকে স্পেস ও কমা মুছে "soham" বানানো
            clean_ssid = text_response.replace(" ", "").replace(",", "").strip()
            print(f"Success: Parsed WiFi SSID -> {clean_ssid}")
            
            # মোড আবার নরমালে ফেরত নিয়ে যাওয়া
            current_mode = "NORMAL"
            
            # আরডুইনো কোড অনুযায়ী HTTP 201 পাঠালে ESP8266 এটিকে নতুন SSID হিসেবে সেভ করবে
            return clean_ssid, 201

        # ----------------------------------------------------
        # ৩. লেটার বাই লেটার ওয়াইফাই পাসওয়ার্ড প্রসেস করা
        # ----------------------------------------------------
        elif current_mode == "WIFI_PASS":
            # স্পেস ও কমা ট্রিম করে পাসওয়ার্ড জোড়া লাগানো
            clean_pass = text_response.replace(" ", "").replace(",", "").strip()
            print(f"Success: Parsed WiFi Password -> {clean_pass}")
            
            # মোড নরমালে ফেরত নিয়ে যাওয়া
            current_mode = "NORMAL"
            
            # আরডুইনো কোড অনুযায়ী HTTP 202 পাঠালে ESP8266 এটিকে নতুন Password হিসেবে সেভ করবে
            return clean_pass, 202

    except Exception as e:
        print(f"Error Processing Audio: {e}")
        # কোনো কারণে গুগল কথা না বুঝতে পারলে নরমাল মোডেই ফেরত যাবে
        current_mode = "NORMAL" 
        return generate_audio_response("Sorry, I could not hear properly. Please try again.")

# টেক্সট থেকে MCP4725 DAC-এর উপযোগী WAV অডিও ফাইল বানানোর ফাংশন
def generate_audio_response(text):
    # gTTS দিয়ে ফ্রি mp3 জেনারেট করা (কোনো টোকেন লাগবে না)
    tts = gTTS(text=text, lang='en')
    tts.save("response.mp3")
    
    # mp3 ফাইলকে কনভার্ট করে 16kHz, Single Channel (Mono) WAV ফাইলে রূপান্তর
    # এটি না করলে MCP4725 স্পিকারে নয়েজ আসবে বা প্লে হবে না
    sound = AudioSegment.from_mp3("response.mp3")
    sound = sound.set_frame_rate(16000).set_channels(1)
    sound.export("response.wav", format="wav")
    
    return send_file("response.wav", mimetype="audio/wav")

if __name__ == '__main__':
    # সার্ভারটি তোমার লোকাল নেটওয়ার্কের ৫০০০ পোর্টে রান হবে
    # host='0.0.0.0' দেওয়ার কারণে একই ওয়াইফাইয়ে থাকা ESP8266 এটিকে খুঁজে পাবে
    app.run(host='0.0.0.0', port=5000, debug=True)
