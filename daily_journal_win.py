#!/usr/bin/env python3
import os
import json
import requests
import time
import threading
from datetime import datetime
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import TextArea, Frame, Box
from prompt_toolkit.styles import Style
from prompt_toolkit.application import get_app

class NetworkJournal:
    def __init__(self, server_url="http://localhost:5000"):
        self.entries = {}
        self.server_url = server_url
        self.data_dir = "data"
        self.ensure_data_directory()
        self.sync_lock = threading.Lock()
        self.load_entries()
        
        # Start background sync thread
        self.sync_thread = threading.Thread(target=self.background_sync, daemon=True)
        self.sync_thread.start()

    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def load_entries(self):
        """Load all journal entries from server or local cache"""
        try:
            # Try to fetch from server
            response = requests.get(f"{self.server_url}/entries", timeout=2)
            if response.status_code == 200:
                self.entries = response.json()
                # Update local cache
                self.update_local_cache()
                return
        except requests.RequestException:
            pass
            
        # If server fetch fails, load from local cache
        self.entries = {}
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json'):
                    date_str = filename[:-5]  # Remove .json extension
                    file_path = os.path.join(self.data_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.entries[date_str] = json.load(f)
                    except Exception as e:
                        print(f"Error loading {file_path}: {e}")

    def update_local_cache(self):
        """Update local cache with current entries"""
        for date_str, content in self.entries.items():
            file_path = os.path.join(self.data_dir, f"{date_str}.json")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error caching {file_path}: {e}")

    def save_entry(self, date_str, content):
        """Save a journal entry to server and local cache"""
        with self.sync_lock:
            self.entries[date_str] = content
            
            # Try to save to server
            try:
                response = requests.post(
                    f"{self.server_url}/entries/{date_str}", 
                    json=content,
                    timeout=2
                )
            except requests.RequestException:
                pass
            
            # Always save to local cache
            file_path = os.path.join(self.data_dir, f"{date_str}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)

    def delete_entry(self, date_str):
        """Delete a journal entry from server and local cache"""
        with self.sync_lock:
            if date_str in self.entries:
                del self.entries[date_str]
            
            # Try to delete from server
            try:
                requests.delete(f"{self.server_url}/entries/{date_str}", timeout=2)
            except requests.RequestException:
                pass
            
            # Delete from local cache
            file_path = os.path.join(self.data_dir, f"{date_str}.json")
            if os.path.exists(file_path):
                os.remove(file_path)

    def background_sync(self):
        """Background thread for syncing with server"""
        while True:
            try:
                # Sleep to avoid constant polling
                time.sleep(10)
                
                # Get entries from server
                response = requests.get(f"{self.server_url}/entries", timeout=2)
                if response.status_code == 200:
                    with self.sync_lock:
                        server_entries = response.json()
                        
                        # Update local entries with server entries
                        for date_str, content in server_entries.items():
                            if date_str not in self.entries:
                                self.entries[date_str] = content
                            elif 'updated_at' in content and 'updated_at' in self.entries[date_str]:
                                # Compare timestamps to see which is newer
                                server_time = datetime.fromisoformat(content['updated_at'])
                                local_time = datetime.fromisoformat(self.entries[date_str]['updated_at'])
                                if server_time > local_time:
                                    self.entries[date_str] = content
                        
                        # Update local cache
                        self.update_local_cache()
            except Exception:
                pass

class JournalUI:
    def __init__(self, server_url="http://localhost:5000"):
        self.journal = NetworkJournal(server_url)
        
        # Create key bindings
        self.kb = KeyBindings()
        
        # Initialize UI state
        self.entries_list = sorted(self.journal.entries.keys(), reverse=True)
        self.selected_index = 0
        self.edit_mode = False
        self.status_message = "Welcome to Daily Journal (Network Sync Enabled)"
        
        # Create UI components
        self.entries_control = FormattedTextControl(self.get_entries_text)
        self.entries_window = Window(content=self.entries_control)
        
        self.content_area = TextArea(
            text="",
            read_only=True,
            scrollbar=True,
            wrap_lines=True,
        )
        
        self.status_bar = Window(
            height=1,
            content=FormattedTextControl(lambda: [("class:status", self.status_message)]),
        )
        
        # Register keybindings
        self.setup_keybindings()
        
        # Create layout
        self.body = VSplit([
            # Left panel - Entries list
            Frame(
                Box(self.entries_window, padding=1),
                title="Journal Entries",
                width=30
            ),
            # Right panel - Content/Editor
            Frame(
                Box(self.content_area, padding=1),
                title="Content"
            )
        ])
        
        self.container = HSplit([
            self.body,
            self.status_bar
        ])
        
        # Create style
        self.style = Style.from_dict({
            'status': 'reverse',
            'frame.border': '#888888',
            'selected': 'reverse',
        })
        
        # Start refresh thread
        self.refresh_thread = threading.Thread(target=self.refresh_entries_list, daemon=True)
        self.refresh_thread.start()
        
        # Create application
        self.app = Application(
            layout=Layout(self.container),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
            style=self.style,
        )
        
        # Load first entry if available
        if self.entries_list:
            self.load_current_entry()
        else:
            self.status_message = "No entries available. Press 'n' to create a new entry."
    
    def refresh_entries_list(self):
        """Background thread to refresh entries list periodically"""
        while True:
            time.sleep(5)  # Check every 5 seconds
            
            # Get latest entries
            old_entries = set(self.entries_list)
            new_entries = set(sorted(self.journal.entries.keys(), reverse=True))
            
            # If there are changes, update UI
            if old_entries != new_entries:
                self.entries_list = sorted(self.journal.entries.keys(), reverse=True)
                
                # Notify UI thread to refresh
                if get_app().is_running:
                    get_app().invalidate()
    
    def setup_keybindings(self):
        @self.kb.add('q')
        def _(event):
            event.app.exit()
        
        @self.kb.add('n')
        def _(event):
            self.create_new_entry()
        
        @self.kb.add('d')
        def _(event):
            self.delete_current_entry()
        
        @self.kb.add('e')
        def _(event):
            self.edit_current_entry()
        
        @self.kb.add('r')
        def _(event):
            self.manual_refresh()
        
        @self.kb.add('up')
        def _(event):
            self.move_selection_up()
        
        @self.kb.add('down')
        def _(event):
            self.move_selection_down()
        
        @self.kb.add('enter')
        def _(event):
            if self.edit_mode:
                self.save_current_entry()
            else:
                self.load_current_entry()
        
        @self.kb.add('escape')
        def _(event):
            if self.edit_mode:
                self.cancel_edit()
    
    def manual_refresh(self):
        """Manually refresh entries from server"""
        self.status_message = "Syncing with server..."
        self.journal.load_entries()
        self.entries_list = sorted(self.journal.entries.keys(), reverse=True)
        self.status_message = "Sync completed"
        
        # Reload current entry if it still exists
        if self.entries_list and 0 <= self.selected_index < len(self.entries_list):
            self.load_current_entry()
    
    def get_entries_text(self):
        """Generate formatted text for entries list"""
        result = []
        for i, date_str in enumerate(self.entries_list):
            if i == self.selected_index:
                result.append(("class:selected", f" {date_str} \n"))
            else:
                result.append(("", f" {date_str} \n"))
        
        if not self.entries_list:
            result.append(("", " No entries available. \n"))
        
        return result
    
    def move_selection_up(self):
        """Move selection up in entries list"""
        if self.entries_list and self.selected_index > 0:
            self.selected_index -= 1
            self.load_current_entry()
    
    def move_selection_down(self):
        """Move selection down in entries list"""
        if self.entries_list and self.selected_index < len(self.entries_list) - 1:
            self.selected_index += 1
            self.load_current_entry()
    
    def load_current_entry(self):
        """Load the currently selected entry"""
        if self.entries_list and 0 <= self.selected_index < len(self.entries_list):
            date_str = self.entries_list[self.selected_index]
            content = self.journal.entries[date_str].get('content', '')
            self.content_area.text = content
            self.content_area.read_only = True
            self.edit_mode = False
            self.status_message = f"Viewing entry from {date_str} | e:Edit | d:Delete | n:New | r:Refresh | q:Quit"
    
    def create_new_entry(self):
        """Create a new journal entry"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # If today's entry exists, append a suffix
        base_date = today
        counter = 1
        date_str = base_date
        while date_str in self.journal.entries:
            date_str = f"{base_date}_{counter}"
            counter += 1
        
        # Create empty entry
        self.journal.save_entry(date_str, {'content': '', 'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat()})
        
        # Update UI
        self.entries_list = sorted(self.journal.entries.keys(), reverse=True)
        self.selected_index = self.entries_list.index(date_str)
        
        # Enter edit mode
        self.edit_current_entry()
    
    def edit_current_entry(self):
        """Edit the current entry"""
        if self.entries_list and 0 <= self.selected_index < len(self.entries_list):
            date_str = self.entries_list[self.selected_index]
            content = self.journal.entries[date_str].get('content', '')
            
            self.content_area.text = content
            self.content_area.read_only = False
            self.edit_mode = True
            self.status_message = "Editing entry | Enter:Save | Esc:Cancel"
    
    def save_current_entry(self):
        """Save the current entry"""
        if self.entries_list and 0 <= self.selected_index < len(self.entries_list):
            date_str = self.entries_list[self.selected_index]
            entry_data = self.journal.entries.get(date_str, {})
            entry_data['content'] = self.content_area.text
            entry_data['updated_at'] = datetime.now().isoformat()
            
            self.journal.save_entry(date_str, entry_data)
            self.content_area.read_only = True
            self.edit_mode = False
            self.status_message = f"Entry saved | e:Edit | d:Delete | n:New | r:Refresh | q:Quit"
    
    def cancel_edit(self):
        """Cancel editing and discard changes"""
        self.edit_mode = False
        self.load_current_entry()
    
    def delete_current_entry(self):
        """Delete the current entry"""
        if self.entries_list and 0 <= self.selected_index < len(self.entries_list):
            date_str = self.entries_list[self.selected_index]
            self.journal.delete_entry(date_str)
            
            # Update UI
            self.entries_list = sorted(self.journal.entries.keys(), reverse=True)
            if self.entries_list:
                self.selected_index = min(self.selected_index, len(self.entries_list) - 1)
                self.load_current_entry()
            else:
                self.selected_index = 0
                self.content_area.text = ""
                self.status_message = "No entries available. Press 'n' to create a new entry."
    
    def run(self):
        """Run the application"""
        self.app.run()

def main():
    # Default to localhost, can be changed via command line
    import sys
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    ui = JournalUI(server_url)
    ui.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass 