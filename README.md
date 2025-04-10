# Terminal Daily Journal

A simple terminal-based diary application with a two-panel interface and network synchronization.

## Features

- Two-panel layout: notes list on the left, content editor on the right
- Create, edit, and delete journal entries
- Entries are stored as JSON files with timestamps
- Full-text editing capabilities in the terminal
- **Network synchronization** to share entries across computers on the same network

## Requirements

- Python 3.x
- Standard Python libraries (os, json, datetime)
- For the curses version (Linux/Mac): Built-in curses library
- For the Windows version: prompt_toolkit library
- Network sync: Flask and requests libraries

## Installation

Install the required dependencies:

```
pip install -r requirements.txt
```

## How to Run

### Server (for network synchronization)

First, start the server on one computer that will act as the central data store:

```
cd NEther/daily_journal
python server.py
```

The server will run on port 5000 by default and will be accessible from other computers on the local network.

### Clients

#### On Linux/Mac
```
cd NEther/daily_journal
python daily_journal.py [server_url]
```

#### On Windows
```
cd NEther/daily_journal
python daily_journal_win.py [server_url]
```

Where `[server_url]` is the URL of the server (optional). If not specified, it defaults to `http://localhost:5000`.

Example with a specific server:
```
python daily_journal.py http://192.168.1.100:5000
```

## Network Synchronization

The application supports real-time synchronization across multiple computers:

1. Run the server on one computer
2. Run clients on other computers pointing to the server
3. Entries will be automatically synchronized every 10 seconds
4. Changes made on any client will be visible to all other clients
5. Press 'r' to manually refresh entries from the server

If the server is unavailable, clients will work offline with their local data and automatically sync when the server becomes available again.

## Controls

### Navigation Mode

- **Arrow Up/Down**: Navigate through entries
- **Enter**: View selected entry
- **n**: Create a new entry
- **e**: Edit the selected entry
- **d**: Delete the selected entry
- **r**: Refresh entries from server
- **q**: Quit the application

### Edit Mode

- **Arrow Keys**: Move the cursor
- **Enter**: Create a new line/Save changes (Windows version)
- **Backspace/Delete**: Delete characters
- **Tab**: Insert 4 spaces (Linux/Mac version)
- **Ctrl+S**: Save changes (Linux/Mac version)
- **Esc**: Cancel editing (discard changes)

## Data Storage

Entries are stored as JSON files in the `data` directory. Each entry is saved with the date as the filename (YYYY-MM-DD.json).

When network synchronization is enabled, entries are also stored on the server and synchronized across all clients. 