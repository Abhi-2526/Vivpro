from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from contextlib import asynccontextmanager
import json
import sqlite3
import os
from typing import List, Dict, Any, Optional
from config import config


class Song(BaseModel):
    index: int
    id: str
    title: str
    danceability: Optional[float] = None
    energy: Optional[float] = None
    key: Optional[int] = None
    loudness: Optional[float] = None
    mode: Optional[int] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    liveness: Optional[float] = None
    valence: Optional[float] = None
    tempo: Optional[float] = None
    duration_ms: Optional[int] = None
    time_signature: Optional[int] = None
    num_bars: Optional[int] = None
    num_sections: Optional[int] = None
    num_segments: Optional[int] = None
    class_label: Optional[int] = None
    star_rating: float = 0.0


class Rating(BaseModel):
    rating: float


def should_reload_data(json_file: str = None, db_file: str = None) -> bool:
    """
    Determine if data should be reloaded from JSON file into database.
    
    Args:
        json_file (str): Path to the JSON data file. Uses config default if None.
        db_file (str): Path to the SQLite database file. Uses config default if None.
    
    Returns:
        bool: True if data should be reloaded, False otherwise.
        
    Logic:
        - Returns False if JSON file doesn't exist (no source to reload from)
        - Returns True if database doesn't exist (first run)
        - Returns True if database is empty or corrupted
        - Returns True if JSON file is newer than database (updated data)
        - Returns False otherwise (use existing database)
    """
    if json_file is None:
        json_file = config.DEFAULT_JSON_FILE
    if db_file is None:
        db_file = config.DATABASE_URL

    if not os.path.exists(json_file):
        return False

    if not os.path.exists(db_file):
        return True

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.execute('SELECT COUNT(*) FROM songs')
        count = cursor.fetchone()[0]
        conn.close()
        if count == 0:
            return True
    except:
        return True

    json_mtime = os.path.getmtime(json_file)
    db_mtime = os.path.getmtime(db_file)

    return json_mtime > db_mtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for handling application startup and shutdown.
    
    This function manages the application lifecycle:
    - Startup: Initialize database and load data if needed
    - Shutdown: Clean up resources (currently no cleanup needed)
    
    Args:
        app (FastAPI): The FastAPI application instance.
        
    Yields:
        None: Control is yielded to FastAPI to handle requests.
        
    Startup Process:
        1. Initialize database tables
        2. Check if data reload is needed using should_reload_data()
        3. Either reload data from JSON or use existing database
    """
    init_db()

    if should_reload_data():
        try:
            song_count = load_data(config.DEFAULT_JSON_FILE)
            print(f"Data reloaded: {song_count} songs from updated JSON")
        except Exception as e:
            print(f"Failed to load {config.DEFAULT_JSON_FILE}: {e}")
    else:
        try:
            conn = sqlite3.connect(config.DATABASE_URL)
            cursor = conn.execute('SELECT COUNT(*) FROM songs')
            count = cursor.fetchone()[0]
            conn.close()
            print(f"Using existing database with {count} songs")
        except:
            print("Database exists but couldn't read song count")

    yield


app = FastAPI(title=config.API_TITLE, version=config.API_VERSION, lifespan=lifespan)


def init_db():
    """
    Initialize the SQLite database and create the songs table if it doesn't exist.
    
    Creates a comprehensive songs table with all audio analysis fields:
    
    The table uses 'CREATE TABLE IF NOT EXISTS' so it's safe to call multiple times.
    """
    conn = sqlite3.connect(config.DATABASE_URL)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            idx INTEGER PRIMARY KEY,
            id TEXT,
            title TEXT,
            danceability REAL,
            energy REAL,
            key INTEGER,
            loudness REAL,
            mode INTEGER,
            acousticness REAL,
            instrumentalness REAL,
            liveness REAL,
            valence REAL,
            tempo REAL,
            duration_ms INTEGER,
            time_signature INTEGER,
            num_bars INTEGER,
            num_sections INTEGER,
            num_segments INTEGER,
            class_label INTEGER,
            star_rating REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()


def normalize_json(json_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert attribute-map JSON format to normalized table format.
    
    Transforms JSON from attribute-map structure like:
    {
        "id": {"0": "song1", "1": "song2"},
        "title": {"0": "Title1", "1": "Title2"}
    }
    
    To normalized list of dictionaries:
    [
        {"index": 0, "id": "song1", "title": "Title1"},
        {"index": 1, "id": "song2", "title": "Title2"}
    ]
    
    Args:
        json_data (Dict[str, Dict[str, Any]]): Attribute-map JSON data.
        
    Returns:
        List[Dict[str, Any]]: List of normalized song dictionaries.
        
    Note:
        - Adds an "index" field for each song based on its position
        - Ensures "star_rating" field exists with default value 0.0
        - Handles missing attributes by setting them to None
    """
    if not json_data:
        return []

    first_attr = list(json_data.keys())[0]
    song_count = len(json_data[first_attr])

    songs = []
    for i in range(song_count):
        song = {"index": i}
        for attr, values in json_data.items():
            song[attr] = values.get(str(i))
        if "star_rating" not in song:
            song["star_rating"] = 0.0
        songs.append(song)

    return songs


def load_data(file_path: str, preserve_ratings: bool = True):
    """
    Load and insert song data from JSON file into the database.
    
    Args:
        file_path (str): Path to the JSON file containing song data.
        preserve_ratings (bool): Whether to preserve existing user ratings.
                               Defaults to True for automatic reloads,
                               should be False for manual /load API calls.
    
    Returns:
        int: Number of songs successfully loaded.
        
    Process:
        1. Read and parse JSON file
        2. Normalize data from attribute-map to table format
        3. If preserve_ratings=True, save existing user ratings
        4. Clear existing data from songs table
        5. Insert all songs with preserved or reset ratings
        6. Commit changes and return count
        
    Raises:
        FileNotFoundError: If the JSON file doesn't exist.
        json.JSONDecodeError: If the JSON file is malformed.
        sqlite3.Error: If database operations fail.
        
    Note:
        - Always deletes all existing songs before inserting new data
        - Preserves user ratings by song ID when preserve_ratings=True
    """
    with open(file_path, 'r') as f:
        json_data = json.load(f)

    songs = normalize_json(json_data)

    conn = sqlite3.connect(config.DATABASE_URL)

    existing_ratings = {}
    if preserve_ratings:
        try:
            cursor = conn.execute('SELECT id, star_rating FROM songs WHERE star_rating > 0')
            existing_ratings = {row[0]: row[1] for row in cursor.fetchall()}
            if existing_ratings:
                print(f"Preserving {len(existing_ratings)} existing ratings")
        except:
            pass
    else:
        print("Resetting all ratings to 0.0")

    conn.execute('DELETE FROM songs')

    for song in songs:
        preserved_rating = existing_ratings.get(song.get('id'), 0.0) if preserve_ratings else 0.0

        # Use proper SQL parameter binding to avoid SQL injection and quote issues
        conn.execute('''
            INSERT INTO songs (idx, id, title, danceability, energy, key, loudness, mode, 
                             acousticness, instrumentalness, liveness, valence, tempo, 
                             duration_ms, time_signature, num_bars, num_sections, 
                             num_segments, class_label, star_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            song.get('index'),
            song.get('id'),
            song.get('title'),
            song.get('danceability'),
            song.get('energy'),
            song.get('key'),
            song.get('loudness'),
            song.get('mode'),
            song.get('acousticness'),
            song.get('instrumentalness'),
            song.get('liveness'),
            song.get('valence'),
            song.get('tempo'),
            song.get('duration_ms'),
            song.get('time_signature'),
            song.get('num_bars'),
            song.get('num_sections'),
            song.get('num_segments'),
            song.get('class_label'),
            preserved_rating
        ))

    conn.commit()
    conn.close()
    return len(songs)


# API Endpoints

@app.get("/songs", response_model=List[Song])
def get_all_songs(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    """
    Retrieve all songs with pagination support.

    Args:
        page (int): Page number starting from 1. Must be >= 1.
        limit (int): Number of songs per page. Must be between 1 and 100.
        
    Returns:
        List[Song]: List of song objects for the requested page.
        
    Example:
        GET /songs?page=1&limit=20  # First 20 songs
        GET /songs?page=2&limit=10  # Songs 11-20
        
    Note:
        - Songs are ordered by their index (idx) in ascending order
        - Returns empty list if page is beyond available data
    """
    offset = (page - 1) * limit

    conn = sqlite3.connect(config.DATABASE_URL)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(f'SELECT * FROM songs ORDER BY idx LIMIT {limit} OFFSET {offset}')
    rows = cursor.fetchall()
    conn.close()

    songs = []
    for row in rows:
        song = dict(row)
        song['index'] = song.pop('idx')
        songs.append(song)

    return songs


@app.get("/songs/search", response_model=List[Song])
def search_by_title(title: str):
    """
    Search for songs by exact title matching.    
    Args:
        title (str): Exact title to match against song titles.
                    Performs case-sensitive exact matching.
                    
    Returns:
        List[Song]: List of songs with exactly matching titles (0 or 1 song).
        
    Example:
        GET /songs/search?title=3AM    
        
    Note:
        - Uses exact string equality (=) for matching
        - Case-sensitive search
        - Returns empty list if no exact match found
    """
    conn = sqlite3.connect(config.DATABASE_URL)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM songs WHERE title = ?", (title,))
    rows = cursor.fetchall()
    conn.close()

    songs = []
    for row in rows:
        song = dict(row)
        song['index'] = song.pop('idx')
        songs.append(song)

    return songs


@app.put("/songs/{song_id}/rating")
def rate_song(song_id: str, rating: Rating):
    """
    Update the star rating for a specific song.    
    Args:
        song_id (str): The unique Spotify ID of the song to rate.
        rating (Rating): Pydantic model containing the rating value (0.0-5.0).
        
    Returns:
        dict: Success message with song_id and new rating value.
        
    Raises:
        HTTPException(400): If rating is not between 0 and 5.
        HTTPException(404): If song with given ID is not found.
        
    Example:
        PUT /songs/5vYA1mW9g2Coh1HUFUSmlb/rating
        Body: {"rating": 4.5}
        
    Note:
        - Rating must be between 0.0 and 5.0 (inclusive)
        - Updates existing rating or sets new rating
        - Rating is preserved during automatic data reloads
    """
    if not 0 <= rating.rating <= 5:
        raise HTTPException(status_code=400, detail=f"Rating must be between 0 and 5")

    conn = sqlite3.connect(config.DATABASE_URL)
    cursor = conn.execute("UPDATE songs SET star_rating = ? WHERE id = ?", (rating.rating, song_id))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Song not found")

    conn.commit()
    conn.close()

    return {"message": "Rating updated", "song_id": song_id, "rating": rating.rating}


@app.post("/load")
def load_json_data(file_path: str = None):
    """
    Manually reload data from JSON file
    
    Args:
        file_path (str): Path to the JSON file to load. Uses config default if None.
        
    Returns:
        dict: Success message with count of loaded songs.
        
    Raises:
        HTTPException(500): If file reading or database operations fail.
        
    Example:
        POST /load                           # Load default file from config
        POST /load?file_path=new_songs.json  # Load different file
        
    Process:
        1. Calls load_data() with preserve_ratings=False
        2. All existing songs are deleted
        3. New songs are inserted with ratings set to 0.0
        4. Returns count of successfully loaded songs
    """
    if file_path is None:
        file_path = config.DEFAULT_JSON_FILE

    try:
        songs_loaded = load_data(file_path, preserve_ratings=False)
        return {"message": f"Loaded {songs_loaded} songs"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
