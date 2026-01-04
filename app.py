import os
import re
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from mistralai import Mistral

# Remove the complex import block for youtube_transcript_api
# We'll use yt-dlp instead

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
    print("[INFO] yt-dlp library loaded successfully")
except ImportError as e:
    print(f"[ERROR] Failed to import yt-dlp: {e}")
    print("Install it with: pip install yt-dlp")
    YT_DLP_AVAILABLE = False
    yt_dlp = None

load_dotenv()
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

app = Flask(__name__)
MODEL_NAME = "open-mistral-7b" 

# --- MISTRAL CLIENT ---
mistral_client = None
if MISTRAL_API_KEY:
    try:
        mistral_client = Mistral(api_key=MISTRAL_API_KEY)
        print("[INFO] Mistral client initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to create Mistral client: {e}")
else:
    print("[ERROR] MISTRAL_API_KEY missing in .env file.")

def get_video_id(url):
    if not url: return None
    match = re.search(r'(?<=v=)[\w-]+|(?<=youtu\.be\/)[\w-]+', url)
    return match.group(0) if match else None

def get_transcript_with_ytdlp(video_id):
    """
    Fetch transcript using yt-dlp
    Returns transcript text or raises exception
    """
    if not YT_DLP_AVAILABLE:
        raise Exception("yt-dlp library not available")
    
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],  # Prefer English
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", 
                download=False
            )
            
            # Try to get manual captions first, then auto-generated
            if 'subtitles' in info and info['subtitles']:
                # Manual captions exist
                if 'en' in info['subtitles']:
                    subtitle_url = info['subtitles']['en'][0]['url']
                elif list(info['subtitles'].keys()):
                    # Take first available language
                    first_lang = list(info['subtitles'].keys())[0]
                    subtitle_url = info['subtitles'][first_lang][0]['url']
                else:
                    subtitle_url = None
            elif 'automatic_captions' in info and info['automatic_captions']:
                # Auto-generated captions
                if 'en' in info['automatic_captions']:
                    subtitle_url = info['automatic_captions']['en'][0]['url']
                else:
                    subtitle_url = None
            else:
                raise Exception("No captions available for this video")
            
            if not subtitle_url:
                raise Exception("Could not find subtitle URL")
            
            # Download and parse the subtitle file
            subtitle_response = ydl.urlopen(subtitle_url)
            subtitle_data = subtitle_response.read().decode('utf-8')
            
            # Parse the subtitles (typically in JSON format)
            subtitles = json.loads(subtitle_data)
            
            # Extract text from subtitle events
            transcript_parts = []
            for event in subtitles.get('events', []):
                if 'segs' in event:
                    for seg in event['segs']:
                        if 'utf8' in seg:
                            transcript_parts.append(seg['utf8'])
            
            transcript_text = ' '.join(transcript_parts)
            
            if not transcript_text.strip():
                raise Exception("Transcript extracted but empty")
                
            return transcript_text
            
    except Exception as e:
        print(f"[YT-DLP ERROR] {e}")
        raise Exception(f"Failed to fetch transcript with yt-dlp: {str(e)}")

def summarize_transcript(transcript):
    if not mistral_client:
        return "Mistral client unavailable. Check API key or imports.", False

    prompt = (
        "Summarize this video transcript in 3 paragraphs. Focus on the main topic and conclusion. List out the main points in list form which must be bullet list form. Give significance to main points. STAY ONLY ACCORDING TO THE TRANSCRIPT GIVEN AND NOTHING ELSE.\n\n"
        f"{transcript[:10000]}"
    )

    try:
        response = mistral_client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        msg = response.choices[0].message.content
        return msg, True
    except Exception as e:
        print(f"[MISTRAL ERROR] {e}")
        return f"Mistral API Error: {e}", False

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/summarize", methods=['POST'])
def summarize():
    # Check if yt-dlp is available
    if not YT_DLP_AVAILABLE:
        return jsonify({
            'success': False, 
            'error': "Server Error: yt-dlp library not installed. Install with: pip install yt-dlp"
        }), 500
    
    if not mistral_client:
        return jsonify({
            'success': False, 
            'error': "Mistral API Key or client initialization failed."
        }), 500

    # Get video URL
    try:
        data = request.get_json()
        video_url = data.get("video_url")
        if not video_url: 
            return jsonify({'success': False, 'error': 'No URL provided.'}), 400
    except:
        return jsonify({'success': False, 'error': 'Invalid JSON.'}), 400 

    video_id = get_video_id(video_url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube Link.'}), 400

    # Fetch transcript with yt-dlp
    print(f"Fetching transcript for: {video_id}")
    
    try:
        transcript_text = get_transcript_with_ytdlp(video_id)
        print(f"[DEBUG] Transcript length: {len(transcript_text)} characters")
        
        # Summarize
        print("Summarizing...")
        summary, success = summarize_transcript(transcript_text)
        
        if success:
            return jsonify({'success': True, 'summary': summary})
        else:
            return jsonify({'success': False, 'error': summary}), 500
            
    except Exception as e:
        print(f"Transcript Error: {e}")
        return jsonify({
            'success': False, 
            'error': f"Failed to get transcript: {str(e)}"
        }), 500

@app.route("/ask", methods=['POST'])
def ask():
    try:
        if not request.is_json:  #request is Flask’s representation of the incoming HTTP request (like an envelope)
            return jsonify({'verification':False, 'error': 'JSON not available.' }), 400 
        
        data = request.get_json() #fetching data from request HTTP
        if data == None:    
            return jsonify({'verification':False, 'error': 'Request failed.' }), 400
        print("Incoming data:", data)

        # validating data (keys)
        required_keys = ["question", "prompt_count", "summary"]
        for keys in required_keys:
            if keys not in data:
                return jsonify({'error': f"{keys} is required."}), 400
        #saving data
        question = data["question"]
        prompt_count = data["prompt_count"]
        summary = data["summary"]
        
        prompt_count = int(data.get("prompt_count", 0))

        # Checking if prompt limit reached
        if prompt_count >= 8:
            return jsonify({
                "success": False,
                "error": "Max prompt limit reached"
            }), 400
        # API calling
        if not mistral_client:
            return jsonify({ 
            'success': False,
            'error': "Mistral API Key or client initialization failed."
        }), 500
        #Giving prompt to Mistral AI
        prompt = (
        "Answer the question of the user based off the summary. Use the summary as the context. List out the main points in list form which must be bullet list form. The answer MUST STAY ONLY ACCORDING TO THE QUESTION GIVEN AND NOTHING ELSE. If the user asks questions outside the context provided, response by saying: I cannot answer this question as it is out of context. \n\n"
        f"Summary: {summary[:2500]}" "\n" f"Question: {question[:500]}"# Question should be moderate in length
    )
        response = mistral_client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
        
        # Succes response
        return jsonify({
            "success": True,
            "answer": answer,
            "prompt_count": prompt_count + 1
        }), 200
       
    except Exception as e:
        return jsonify({'verification':False, 'error':f"Internal server error {str(e)}"}), 500
    

if __name__ == "__main__":
    app.run(debug=True)