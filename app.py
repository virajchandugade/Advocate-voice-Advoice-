from flask import Flask, request, jsonify, send_file, render_template, session
from datetime import datetime
from pymongo import MongoClient
import os
import threading
import whisper
import webview
from docx import Document
import re
import uuid
import sys
import locale

# Encoding Fix
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# Flask Setup
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

#--------------------whisperpath--------------------------------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # PyInstaller extracts files here
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Correctly reference assets like mel_filters.npz
MEL_FILTERS_PATH = os.path.join(BASE_DIR, "whisper", "assets", "mel_filters.npz")


# MongoDB Connection
MONGO_URI = "mongodb+srv://user:password.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["advoice"]
    access_key_collection = db["access_keys"]
    users_collection = db["users"]
    client.server_info()
    print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB Connection Failed: {str(e)}")
    exit(1)

# Load Whisper Model

os.environ["XDG_CACHE_HOME"] = "venv/.cache"

print("Loading Whisper Model...")
whisper_model = whisper.load_model("medium")
print("Whisper Model Loaded from:", os.path.join("venv/.cache", "whisper"))

# UPLOAD_FOLDER = "recordings"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Get MAC Address
def get_mac_address():
    try:
        mac_int = uuid.getnode()
        mac_address = ':'.join(['{:02x}'.format((mac_int >> elements) & 0xff) 
                              for elements in range(0, 8*6, 8)][::-1])
        return mac_address
    except Exception as e:
        return f"Error fetching MAC address: {e}"

@app.route('/get-mac', methods=['GET'])
def get_mac():
    return jsonify({'mac': get_mac_address()})

# Text Processing
def process_text(text):
    replacements = {
        "bracket open": "(", "bracket close": ")",
        "open bracket": "(", "close bracket": ")",
        "bracket opened": "(", "bracket closed": ")",
        "opened bracket": "(", "closed bracket": ")",
        "square bracket open": "[", "square bracket close": "]",
        "open square bracket": "[", "close square bracket": "]",
        "square bracket opened": "[", "square bracket closed": "]",
        "curly bracket open": "{", "curly bracket close": "}",
        "open curly bracket": "{", "close curly bracket": "}",
        "angle bracket open": "<", "angle bracket close": ">",
        "comma": ",", "full stop": ".", "fullstop": ".",
        "question mark": "?", "exclamation mark": "!",
        "colon": ":", "semicolon": ";", "hyphen": "-",
        "dash": "—", "double quote": "\"", "single quote": "'",
        "apostrophe": "’", "paragraph": "¶", "section": "§",
        "article": "Art.", "per cent": "%", "versus": "v.",
        "honourable": "Hon'ble", "his lordship": "His Lordship",
        "her ladyship": "Her Ladyship", "learned counsel": "Ld. Counsel",
        
    "first point": "1)", "second point": "2)", "third point": "3)", "fourth point": "4)", "fifth point": "5)", "sixth point": "6)", "seventh point": "7)", "eighth point": "8)", "ninth point": "9)", "tenth point": "10)", 
    "eleventh point": "11)", "twelfth point": "12)", "thirteenth point": "13)", "fourteenth point": "14)", 
    "fifteenth point": "15)", "sixteenth point": "16)", "seventeenth point": "17)", "eighteenth point": "18)", 
    "nineteenth point": "19)", "twentieth point": "20)", "twenty-first point": "21)", "twenty-second point": "22)", 
    "twenty-third point": "23)", "twenty-fourth point": "24)", "twenty-fifth point": "25)", "twenty-sixth point": "26)", 
    "twenty-seventh point": "27)", "twenty-eighth point": "28)", "twenty-ninth point": "29)", "thirtieth point": "30)", 
    "thirty-first point": "31)", "thirty-second point": "32)", "thirty-third point": "33)", "thirty-fourth point": "34)", 
    "thirty-fifth point": "35)", "thirty-sixth point": "36)", "thirty-seventh point": "37)", "thirty-eighth point": "38)", 
    "thirty-ninth point": "39)", "fortieth point": "40)", "forty-first point": "41)", "forty-second point": "42)", 
    "forty-third point": "43)", "forty-fourth point": "44)", "forty-fifth point": "45)", "forty-sixth point": "46)", 
    "forty-seventh point": "47)", "forty-eighth point": "48)", "forty-ninth point": "49)", "fiftieth point": "50)", 
    "fifty-first point": "51)", "fifty-second point": "52)", "fifty-third point": "53)", "fifty-fourth point": "54)", 
    "fifty-fifth point": "55)", "fifty-sixth point": "56)", "fifty-seventh point": "57)", "fifty-eighth point": "58)", 
    "fifty-ninth point": "59)", "sixtieth point": "60)", "sixty-first point": "61)", "sixty-second point": "62)", 
    "sixty-third point": "63)", "sixty-fourth point": "64)", "sixty-fifth point": "65)", "sixty-sixth point": "66)", 
    "sixty-seventh point": "67)", "sixty-eighth point": "68)", "sixty-ninth point": "69)", "seventieth point": "70)", 
    "seventy-first point": "71)", "seventy-second point": "72)", "seventy-third point": "73)", "seventy-fourth point": "74)", 
    "seventy-fifth point": "75)", "seventy-sixth point": "76)", "seventy-seventh point": "77)", "seventy-eighth point": "78)", 
    "seventy-ninth point": "79)", "eightieth point": "80)", "eighty-first point": "81)", "eighty-second point": "82)", 
    "eighty-third point": "83)", "eighty-fourth point": "84)", "eighty-fifth point": "85)", "eighty-sixth point": "86)", 
    "eighty-seventh point": "87)", "eighty-eighth point": "88)", "eighty-ninth point": "89)", "ninetieth point": "90)", 
    "ninety-first point": "91)", "ninety-second point": "92)", "ninety-third point": "93)", "ninety-fourth point": "94)", 
    "ninety-fifth point": "95)", "ninety-sixth point": "96)", "ninety-seventh point": "97)", "ninety-eighth point": "98)", 
    "ninety-ninth point": "99)", "hundredth point": "100)"
    }

    text = re.sub(r"\b(new\s+line|next\s+line)\b", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(new\s+paragraph|next\s+paragraph)\b", "\n\n", text, flags=re.IGNORECASE)

    # Replace words using the dictionary
    for word, symbol in replacements.items():
        text = re.sub(rf"\b{re.escape(word)}\b", symbol, text, flags=re.IGNORECASE)

    # Remove extra spaces before punctuation
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)

    # Ensure multiple new lines are respected for readability
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # Fix cases where multiple punctuation marks appear incorrectly
    text = re.sub(r"\.{3,}", "...", text)  # Handle multiple dots as ellipses
    text = re.sub(r"([.,!?;:]){2,}", r"\1", text)  # Remove duplicate punctuation

    return text.strip()

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    try:
        audio_file = request.files.get("audio")
        if not audio_file:
            return jsonify({"success": False, "error": "No audio file uploaded"})

        # Create secure storage directory structure
        UPLOAD_FOLDER = os.path.join(os.environ["APPDATA"], "Advoice", "recordings")
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = os.path.join(UPLOAD_FOLDER, f"recorded_{timestamp}_{unique_id}.wav")

        # Save file with error handling
        try:
            audio_file.save(filename)
        except Exception as save_error:
            return jsonify({"success": False, "error": f"File save failed: {str(save_error)}"})

        # Transcription process
        try:
            result = whisper_model.transcribe(filename, language="en")
            processed_text = process_text(result["text"])
        except Exception as transcribe_error:
            return jsonify({"success": False, "error": f"Transcription failed: {str(transcribe_error)}"})

        return jsonify({
            "success": True,
            "text": processed_text,
            "audio_path": filename,  # Return path to saved file
            "file_id": f"{timestamp}_{unique_id}"  # Return unique identifier
        })

    except Exception as e:
        error_id = uuid.uuid4().hex[:8]
        print(f"Critical error [{error_id}]: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"System error ({error_id}). Please contact support.",
            "reference_id": f"{timestamp}_{unique_id}" if 'unique_id' in locals() else None
            })


DOWNLOADS_FOLDER = os.path.expanduser("~/Downloads")

@app.route("/save", methods=["POST"])
def save_to_word():
    data = request.json
    text = data.get('text')
    filename = data.get('filename')

    if not text or not filename:
        return jsonify({"success": False, "error": "Missing text or filename"})

    try:
        if not filename.endswith(".docx"):  # Ensure correct file extension
            filename += ".docx"

        file_path = os.path.join(DOWNLOADS_FOLDER, filename)

        # Save the document
        doc = Document()
        doc.add_paragraph(text)
        doc.save(file_path)

        return jsonify({"success": True, "file": f"/download/{filename}"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    file_path = os.path.join(DOWNLOADS_FOLDER, filename)

    # Ensure the file exists before sending
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"}), 404

    return send_file(file_path, as_attachment=True)


# @app.route("/download/<filename>", methods=["GET"])
# def download_file(filename):
#     return send_file(f"{filename}", as_attachment=True)



@app.route("/offline")
def offline():
    return render_template("offline.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "username" in session:
            return jsonify({"success": True, "redirect": "/option"})
        return render_template("login.html")
    try:
        data = request.json
        username = data.get("username")
        license_key = data.get("licenseKey")
        client_mac = get_mac_address()

        key_doc = access_key_collection.find_one({"licenseKey": license_key})
        if not key_doc:
            return jsonify({"success": False, "message": "Invalid license key."})

        stored_mac, stored_user = key_doc.get("macAddress"), key_doc.get("assignedTo")
        if not stored_mac:
            access_key_collection.update_one({"licenseKey": license_key},
                                             {"$set": {"assignedTo": username, "macAddress": client_mac}})
            users_collection.insert_one({"username": username, "licenseKey": license_key})
            session["username"] = username
            return jsonify({"success": True, "redirect": "/option"})
        if stored_user != username:
            return jsonify({"success": False, "message": "Username mismatch."})
        if stored_mac != client_mac:
            return jsonify({"success": False, "message": "Access denied."})
        session["username"] = username
        return jsonify({"success": True, "redirect": "/option"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/option")
def option():
    if "username" not in session:
        return jsonify({"success": False, "redirect": "/login"})
    return render_template("option.html")

@app.route("/")
def index():
    if "username" in session:
        return jsonify({"success": True, "redirect": "/option"})
    return render_template("begin.html")

# Start Flask Server
def start_flask():
    app.run(port=5000, threaded=True)

# Start WebView UI
def start_app():
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    webview.create_window("Advoice", "http://127.0.0.1:5000", width=1280, height=720, resizable=True)
    webview.start()

if __name__ == "__main__":
    start_app()
