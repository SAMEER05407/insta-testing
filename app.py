
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import os
import threading
import time
import random
from datetime import datetime
from werkzeug.utils import secure_filename
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, FeedbackRequired, BadPassword, UnknownError, ClientError
import shutil

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = 'reels'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Global variables
accounts = []
captions = []
reels = []
is_posting = False
posting_thread = None
logs = []

# Create directories
os.makedirs("reels", exist_ok=True)
os.makedirs("sessions", exist_ok=True)

def load_accounts():
    global accounts
    try:
        if os.path.exists("accounts.json"):
            with open("accounts.json", "r") as f:
                accounts = json.load(f)
    except Exception as e:
        print(f"Error loading accounts: {str(e)}")

def save_accounts():
    with open("accounts.json", "w") as f:
        json.dump(accounts, f, indent=2)

def load_captions():
    global captions
    try:
        if os.path.exists("captions.txt"):
            with open("captions.txt", "r", encoding="utf-8") as f:
                content = f.read().strip()
                captions = [line.strip() for line in content.split('\n') if line.strip()]
    except Exception as e:
        print(f"Error loading captions: {str(e)}")

def save_captions():
    with open("captions.txt", "w", encoding="utf-8") as f:
        f.write('\n'.join(captions))

def load_reels():
    global reels
    reels = []
    if os.path.exists("reels"):
        for filename in os.listdir("reels"):
            if filename.lower().endswith('.mp4'):
                reels.append(filename)

def log_message(message):
    global logs
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    logs.append(log_entry)
    print(log_entry)  # Also print to console
    
    # Save to logs.txt
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {message}\n")
    
    # Keep only last 100 logs in memory
    if len(logs) > 100:
        logs = logs[-100:]

def create_instagram_client(username, password):
    """Create and authenticate Instagram client with proper error handling"""
    try:
        # Create client with custom settings
        client = Client()
        
        # Set more realistic settings
        client.delay_range = [1, 3]  # Random delay between requests
        
        # Try to load existing session
        session_file = f"sessions/session_{username}.json"
        
        if os.path.exists(session_file):
            try:
                log_message(f"Loading existing session for {username}")
                client.load_settings(session_file)
                
                # Test if session is still valid
                try:
                    client.get_timeline_feed()
                    log_message(f"✅ Session valid for {username}")
                    return client
                except Exception:
                    log_message(f"Session expired for {username}, creating new one")
                    os.remove(session_file)  # Remove invalid session
            except Exception as e:
                log_message(f"Failed to load session for {username}: {str(e)}")
                if os.path.exists(session_file):
                    os.remove(session_file)
        
        # Create new session
        log_message(f"Creating new session for {username}")
        
        # Fresh client for new login
        client = Client()
        client.delay_range = [1, 3]
        
        # Login with better error handling
        try:
            client.login(username, password)
            log_message(f"✅ Successfully logged in {username}")
            
            # Save session
            client.dump_settings(session_file)
            log_message(f"Session saved for {username}")
            
            return client
            
        except BadPassword:
            log_message(f"❌ Wrong password for {username}")
            return None
        except ChallengeRequired as e:
            log_message(f"❌ Challenge required for {username}. Please complete verification on Instagram app/website")
            return None
        except FeedbackRequired as e:
            log_message(f"❌ Account {username} is temporarily restricted by Instagram")
            return None
        except Exception as e:
            error_msg = str(e).lower()
            if "can't find an account" in error_msg or "user not found" in error_msg:
                log_message(f"❌ Account {username} not found. Check if username is correct")
            elif "login" in error_msg:
                log_message(f"❌ Login failed for {username}: Check credentials")
            else:
                log_message(f"❌ Login error for {username}: {str(e)}")
            return None
            
    except Exception as e:
        log_message(f"❌ Client creation failed for {username}: {str(e)}")
        return None

def post_reel(account, reel_filename):
    """Post reel with comprehensive error handling"""
    username = account['username']
    password = account['password']
    
    try:
        log_message(f"🚀 Starting post to {username}...")
        
        # Create authenticated client
        client = create_instagram_client(username, password)
        if not client:
            log_message(f"❌ Could not authenticate {username}")
            return False
        
        # Get random caption
        caption = random.choice(captions) if captions else ""
        
        # Prepare reel path
        reel_path = os.path.join("reels", reel_filename)
        
        if not os.path.exists(reel_path):
            log_message(f"❌ Reel file not found: {reel_filename}")
            return False
        
        log_message(f"📤 Uploading {reel_filename} to {username}...")
        
        # Add delay before upload
        time.sleep(random.randint(2, 5))
        
        # Upload reel
        media = client.clip_upload(reel_path, caption)
        
        if media:
            log_message(f"✅ Successfully posted {reel_filename} to {username}")
            log_message(f"📝 Caption: {caption[:50]}...")
            return True
        else:
            log_message(f"❌ Upload failed for {reel_filename} to {username}")
            return False
            
    except FeedbackRequired:
        log_message(f"❌ {username} is temporarily restricted by Instagram")
        return False
    except ChallengeRequired:
        log_message(f"❌ {username} requires challenge completion")
        return False
    except Exception as e:
        error_msg = str(e)
        log_message(f"❌ Failed to post {reel_filename} to {username}: {error_msg}")
        
        # Provide specific solutions
        if "challenge" in error_msg.lower():
            log_message(f"💡 Solution: Complete Instagram security challenge for {username}")
        elif "feedback" in error_msg.lower():
            log_message(f"💡 Solution: Account {username} may be temporarily restricted")
        elif "login" in error_msg.lower():
            log_message(f"💡 Solution: Verify {username} credentials and login manually first")
        
        return False

def posting_loop():
    """Main posting loop with improved logic"""
    global is_posting
    reel_index = 0
    
    log_message("🚀 Posting loop started")
    
    while is_posting:
        if not reels or not accounts or not captions:
            log_message("❌ Missing requirements: accounts, reels, or captions")
            break
            
        for account in accounts:
            if not is_posting:
                log_message("⏹️ Posting stopped by user")
                break
            
            try:
                success = post_reel(account, reels[reel_index])
                
                if success:
                    log_message(f"✅ Post successful to {account['username']}")
                else:
                    log_message(f"❌ Post failed to {account['username']}")
                
                # Random delay between accounts (15-45 seconds)
                if is_posting:  # Check again before delay
                    delay = random.randint(15, 45)
                    log_message(f"⏳ Waiting {delay} seconds before next post...")
                    
                    for i in range(delay):
                        if not is_posting:
                            break
                        time.sleep(1)
                
            except Exception as e:
                log_message(f"❌ Error posting to {account['username']}: {str(e)}")
        
        # Move to next reel, loop back to start if at end
        if is_posting:
            reel_index = (reel_index + 1) % len(reels)
            log_message(f"📹 Moving to next reel: {reels[reel_index]}")
    
    log_message("⏹️ Posting loop stopped")

# Routes
@app.route('/')
def dashboard():
    load_accounts()
    load_reels()
    load_captions()
    
    return render_template('dashboard.html', 
                         total_accounts=len(accounts),
                         total_reels=len(reels),
                         total_captions=len(captions),
                         logs=logs[-20:],  # Show last 20 logs
                         is_posting=is_posting)

@app.route('/accounts')
def accounts_page():
    load_accounts()
    return render_template('accounts.html', accounts=accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not username or not password:
        flash('Please enter both username and password', 'error')
        return redirect(url_for('accounts_page'))
    
    # Check if account already exists
    for acc in accounts:
        if acc['username'] == username:
            flash(f'Account {username} already exists', 'error')
            return redirect(url_for('accounts_page'))
    
    account = {"username": username, "password": password}
    accounts.append(account)
    save_accounts()
    
    log_message(f"➕ Added account: {username}")
    flash(f'Account {username} added successfully', 'success')
    return redirect(url_for('accounts_page'))

@app.route('/remove_account/<int:index>')
def remove_account(index):
    if 0 <= index < len(accounts):
        username = accounts[index]["username"]
        del accounts[index]
        save_accounts()
        
        # Remove session file if exists
        session_file = f"sessions/session_{username}.json"
        if os.path.exists(session_file):
            os.remove(session_file)
        
        log_message(f"🗑️ Removed account: {username}")
        flash(f'Account {username} removed successfully', 'success')
    return redirect(url_for('accounts_page'))

@app.route('/reels')
def reels_page():
    load_reels()
    load_captions()
    return render_template('reels.html', reels=reels, captions=captions)

@app.route('/upload_reels', methods=['POST'])
def upload_reels():
    if 'files' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('reels_page'))
    
    files = request.files.getlist('files')
    uploaded_count = 0
    
    for file in files:
        if file and file.filename and file.filename.lower().endswith('.mp4'):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            log_message(f"📤 Uploaded reel: {filename}")
            uploaded_count += 1
    
    if uploaded_count > 0:
        flash(f'{uploaded_count} reels uploaded successfully', 'success')
    else:
        flash('No valid MP4 files were uploaded', 'error')
    
    return redirect(url_for('reels_page'))

@app.route('/remove_reel/<filename>')
def remove_reel(filename):
    reel_path = os.path.join("reels", filename)
    if os.path.exists(reel_path):
        os.remove(reel_path)
        log_message(f"🗑️ Removed reel: {filename}")
        flash(f'Reel {filename} removed successfully', 'success')
    return redirect(url_for('reels_page'))

@app.route('/save_captions', methods=['POST'])
def save_captions_route():
    global captions
    captions_text = request.form.get('captions', '').strip()
    captions = [line.strip() for line in captions_text.split('\n') if line.strip()]
    save_captions()
    log_message("💬 Captions saved")
    flash('Captions saved successfully', 'success')
    return redirect(url_for('reels_page'))

@app.route('/start_posting', methods=['POST'])
def start_posting():
    global is_posting, posting_thread
    
    if not accounts:
        flash('No accounts added', 'error')
        return redirect(url_for('dashboard'))
    
    if not reels:
        flash('No reels uploaded', 'error')
        return redirect(url_for('dashboard'))
    
    if not captions:
        flash('No captions available', 'error')
        return redirect(url_for('dashboard'))
    
    if not is_posting:
        is_posting = True
        posting_thread = threading.Thread(target=posting_loop)
        posting_thread.daemon = True
        posting_thread.start()
        log_message("🚀 Posting started")
        flash('Posting started successfully', 'success')
    else:
        flash('Posting is already running', 'info')
    
    return redirect(url_for('dashboard'))

@app.route('/stop_posting', methods=['POST'])
def stop_posting():
    global is_posting
    is_posting = False
    log_message("⏹️ Posting stopped by user")
    flash('Posting stopped', 'info')
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    return jsonify({
        'is_posting': is_posting,
        'total_accounts': len(accounts),
        'total_reels': len(reels),
        'total_captions': len(captions),
        'recent_logs': logs[-5:]
    })

@app.route('/ping')
def ping():
    return jsonify({'status': 'alive', 'timestamp': datetime.now().isoformat()})

# Test account login route
@app.route('/test_account/<int:index>')
def test_account(index):
    if 0 <= index < len(accounts):
        account = accounts[index]
        username = account['username']
        password = account['password']
        
        log_message(f"🧪 Testing login for {username}...")
        
        client = create_instagram_client(username, password)
        if client:
            flash(f'✅ Account {username} login successful!', 'success')
            log_message(f"✅ Test successful for {username}")
        else:
            flash(f'❌ Account {username} login failed', 'error')
            log_message(f"❌ Test failed for {username}")
    
    return redirect(url_for('accounts_page'))

# Initialize data on startup
load_accounts()
load_captions()
load_reels()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
