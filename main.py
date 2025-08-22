
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import random
import time
import threading
from datetime import datetime
from instagrapi import Client
import shutil

class InstagramPoster:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Reel Poster")
        self.root.geometry("800x600")
        
        self.accounts = []
        self.captions = []
        self.reels = []
        self.is_posting = False
        self.posting_thread = None
        
        # Create directories
        os.makedirs("reels", exist_ok=True)
        
        self.create_gui()
        self.load_accounts()
        self.load_captions()
        self.load_reels()
    
    def create_gui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Accounts tab
        accounts_frame = ttk.Frame(notebook)
        notebook.add(accounts_frame, text="Accounts")
        self.create_accounts_tab(accounts_frame)
        
        # Reels tab
        reels_frame = ttk.Frame(notebook)
        notebook.add(reels_frame, text="Reels")
        self.create_reels_tab(reels_frame)
        
        # Captions tab
        captions_frame = ttk.Frame(notebook)
        notebook.add(captions_frame, text="Captions")
        self.create_captions_tab(captions_frame)
        
        # Posting tab
        posting_frame = ttk.Frame(notebook)
        notebook.add(posting_frame, text="Posting")
        self.create_posting_tab(posting_frame)
    
    def create_accounts_tab(self, parent):
        # Add account section
        add_frame = ttk.LabelFrame(parent, text="Add Account")
        add_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(add_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.username_entry = ttk.Entry(add_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(add_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.password_entry = ttk.Entry(add_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Button(add_frame, text="Add Account", command=self.add_account).grid(row=2, column=0, columnspan=2, pady=5)
        
        add_frame.columnconfigure(1, weight=1)
        
        # Accounts list
        list_frame = ttk.LabelFrame(parent, text="Saved Accounts")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.accounts_listbox = tk.Listbox(list_frame)
        self.accounts_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Button(list_frame, text="Remove Selected", command=self.remove_account).pack(pady=5)
    
    def create_reels_tab(self, parent):
        upload_frame = ttk.Frame(parent)
        upload_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(upload_frame, text="Upload Reels (MP4 files)", command=self.upload_reels).pack(pady=5)
        
        list_frame = ttk.LabelFrame(parent, text="Uploaded Reels")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.reels_listbox = tk.Listbox(list_frame)
        self.reels_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Button(list_frame, text="Remove Selected", command=self.remove_reel).pack(pady=5)
    
    def create_captions_tab(self, parent):
        ttk.Label(parent, text="Enter captions (one per line):").pack(anchor='w', padx=10, pady=5)
        
        self.captions_text = scrolledtext.ScrolledText(parent, height=15)
        self.captions_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        ttk.Button(parent, text="Save Captions", command=self.save_captions).pack(pady=5)
    
    def create_posting_tab(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_button = ttk.Button(control_frame, text="Start Posting", command=self.start_posting)
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="STOP", command=self.stop_posting, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Status
        status_frame = ttk.LabelFrame(parent, text="Status")
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready to post")
        self.status_label.pack(padx=5, pady=5)
        
        # Log
        log_frame = ttk.LabelFrame(parent, text="Activity Log")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def add_account(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        account = {"username": username, "password": password}
        self.accounts.append(account)
        self.save_accounts()
        self.update_accounts_list()
        
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        
        self.log(f"Added account: {username}")
    
    def remove_account(self):
        selected = self.accounts_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Please select an account to remove")
            return
        
        index = selected[0]
        username = self.accounts[index]["username"]
        del self.accounts[index]
        self.save_accounts()
        self.update_accounts_list()
        
        self.log(f"Removed account: {username}")
    
    def upload_reels(self):
        files = filedialog.askopenfilenames(
            title="Select MP4 files",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        
        for file in files:
            filename = os.path.basename(file)
            destination = os.path.join("reels", filename)
            shutil.copy2(file, destination)
            self.log(f"Uploaded reel: {filename}")
        
        self.load_reels()
    
    def remove_reel(self):
        selected = self.reels_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Please select a reel to remove")
            return
        
        index = selected[0]
        reel = self.reels[index]
        os.remove(os.path.join("reels", reel))
        self.load_reels()
        
        self.log(f"Removed reel: {reel}")
    
    def save_captions(self):
        captions_content = self.captions_text.get("1.0", tk.END).strip()
        with open("captions.txt", "w", encoding="utf-8") as f:
            f.write(captions_content)
        self.load_captions()
        self.log("Captions saved")
        messagebox.showinfo("Success", "Captions saved successfully")
    
    def start_posting(self):
        if not self.accounts:
            messagebox.showerror("Error", "No accounts added")
            return
        
        if not self.reels:
            messagebox.showerror("Error", "No reels uploaded")
            return
        
        if not self.captions:
            messagebox.showerror("Error", "No captions available")
            return
        
        self.is_posting = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        self.posting_thread = threading.Thread(target=self.posting_loop)
        self.posting_thread.daemon = True
        self.posting_thread.start()
    
    def stop_posting(self):
        self.is_posting = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="Stopping...")
        self.log("Posting stopped by user")
    
    def posting_loop(self):
        reel_index = 0
        
        while self.is_posting:
            for account in self.accounts:
                if not self.is_posting:
                    break
                
                try:
                    self.post_reel(account, self.reels[reel_index])
                    
                    # Random delay between posts (10-30 seconds)
                    delay = random.randint(10, 30)
                    self.status_label.config(text=f"Waiting {delay} seconds...")
                    
                    for i in range(delay):
                        if not self.is_posting:
                            break
                        time.sleep(1)
                    
                except Exception as e:
                    self.log(f"Error posting to {account['username']}: {str(e)}")
            
            # Move to next reel, loop back to start if at end
            reel_index = (reel_index + 1) % len(self.reels)
        
        self.status_label.config(text="Ready to post")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
    
    def post_reel(self, account, reel_filename):
        try:
            self.status_label.config(text=f"Posting to {account['username']}...")
            
            # Create Instagram client
            client = Client()
            client.login(account["username"], account["password"])
            
            # Get random caption
            caption = random.choice(self.captions) if self.captions else ""
            
            # Upload reel
            reel_path = os.path.join("reels", reel_filename)
            client.clip_upload(reel_path, caption)
            
            log_message = f"Posted {reel_filename} to {account['username']} with caption: {caption[:50]}..."
            self.log(log_message)
            
            # Save to logs.txt
            with open("logs.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: {log_message}\n")
            
        except Exception as e:
            error_msg = f"Failed to post {reel_filename} to {account['username']}: {str(e)}"
            self.log(error_msg)
            
            with open("logs.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: {error_msg}\n")
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        self.log_text.insert(tk.END, log_entry + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def save_accounts(self):
        with open("accounts.json", "w") as f:
            json.dump(self.accounts, f, indent=2)
    
    def load_accounts(self):
        try:
            if os.path.exists("accounts.json"):
                with open("accounts.json", "r") as f:
                    self.accounts = json.load(f)
            self.update_accounts_list()
        except Exception as e:
            self.log(f"Error loading accounts: {str(e)}")
    
    def update_accounts_list(self):
        self.accounts_listbox.delete(0, tk.END)
        for account in self.accounts:
            self.accounts_listbox.insert(tk.END, account["username"])
    
    def load_captions(self):
        try:
            if os.path.exists("captions.txt"):
                with open("captions.txt", "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    self.captions = [line.strip() for line in content.split('\n') if line.strip()]
                    self.captions_text.delete("1.0", tk.END)
                    self.captions_text.insert("1.0", content)
        except Exception as e:
            self.log(f"Error loading captions: {str(e)}")
    
    def load_reels(self):
        self.reels = []
        if os.path.exists("reels"):
            for filename in os.listdir("reels"):
                if filename.lower().endswith('.mp4'):
                    self.reels.append(filename)
        
        self.reels_listbox.delete(0, tk.END)
        for reel in self.reels:
            self.reels_listbox.insert(tk.END, reel)

if __name__ == "__main__":
    root = tk.Tk()
    app = InstagramPoster(root)
    root.mainloop()
