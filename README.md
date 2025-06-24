# Vivpro Music Playlist API

A FastAPI-based REST API for managing music playlists with song ratings and search functionality. 

## Features

- **Data Processing** - Converts JSON attribute-map format to normalized table format
- **Song Search** - Search songs by exact title matching
- **Rating System** - 5-star rating system (0.0-5.0) for songs
- **Pagination** - Paginated song listings
- **SQLite** - Simple, embedded database
- **Smart Data Loading** - Preserves ratings on restarts, reloads when JSON updated

## Requirements Satisfied

**1.1** Data Processing - Normalize JSON attribute-maps to table format  
**1.2.1** REST API with pagination for all items  
**1.2.2** Search by title functionality  
**1.2.3** Star rating system (0-5)  
**1.2.4** Comprehensive unit tests  

## Quick Start

### Install Dependencies
```bash
pip install -r minimal_requirements.txt
```

### Run the API
```bash
python minimal_api.py
```

The API will start on `http://localhost:8000` and automatically:
1. Create SQLite database (`minimal.db`)
2. Load songs from `playlist.json` if available
3. Preserve existing ratings on restart


## API Endpoints

### Song Management
- `GET /songs?page=1&limit=20` - Get all songs with pagination
- `GET /songs/search?title=<title>` - Search songs by exact title
- `PUT /songs/{song_id}/rating` - Rate a song (0.0-5.0)

### Data Management  
- `POST /load?file_path=playlist.json` - Reload data (resets ratings)

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)

## Data Format

### Input Format (playlist.json)
```json
{
  "id": {"0": "5vYA1mW9g2Coh1HUFUSmlb", "1": "2klCjJcucgGQysgH170npL"},
  "title": {"0": "3AM", "1": "4 Walls"},
  "danceability": {"0": 0.521, "1": 0.735},
  "energy": {"0": 0.673, "1": 0.849},
  "key": {"0": 4, "1": 7},
  "loudness": {"0": -8.123, "1": -6.456},
  "mode": {"0": 1, "1": 0},
  "acousticness": {"0": 0.234, "1": 0.567},
  "instrumentalness": {"0": 0.001, "1": 0.0},
  "liveness": {"0": 0.123, "1": 0.456},
  "valence": {"0": 0.678, "1": 0.345},
  "tempo": {"0": 128.0, "1": 140.5},
  "duration_ms": {"0": 210000, "1": 195000},
  "time_signature": {"0": 4, "1": 4},
  "num_bars": {"0": 64, "1": 72},
  "num_sections": {"0": 8, "1": 9},
  "num_segments": {"0": 320, "1": 298},
  "class": {"0": 1, "1": 2}
}
```

### API Response Format
```json
[
  {
    "index": 0,
    "id": "5vYA1mW9g2Coh1HUFUSmlb",
    "title": "3AM",
    "danceability": 0.521,
    "energy": 0.673,
    "key": 4,
    "loudness": -8.123,
    "mode": 1,
    "acousticness": 0.234,
    "instrumentalness": 0.001,
    "liveness": 0.123,
    "valence": 0.678,
    "tempo": 128.0,
    "duration_ms": 210000,
    "time_signature": 4,
    "num_bars": 64,
    "num_sections": 8,
    "num_segments": 320,
    "class_label": 1,
    "star_rating": 0.0
  }
]
```

## Testing the API

### Using Interactive Docs
Visit `http://localhost:8000/docs` for interactive API documentation with built-in testing interface.

### Running Unit Tests
```bash
# Run all tests
python -m pytest test_minimal.py -v

```

## Smart Data Management

The API intelligently manages data loading:

### Automatic Startup Behavior
- **First run**: Creates database, loads songs from JSON
- **Normal restart**: Preserves existing database and user ratings  
- **JSON updated**: Automatically reloads data while preserving ratings
- **No JSON file**: Uses existing database

### Manual Data Loading
- `POST /load` endpoint resets ALL ratings to 0.0
- Use only when you want to completely refresh data

### Rating Preservation
```python
PUT /songs/song123/rating {"rating": 4.5}
```

## Dependencies

Only 5 minimal dependencies:
```txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pytest==7.4.3
pytest-cov==6.1.1
```

## Configuration

### Environment
- **Database**: `minimal.db` (SQLite, auto-created)
- **Port**: 8000 (avoids macOS Control Center conflict on 5000)
- **Host**: 0.0.0.0 (accessible from network)

### Customization
```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

## License

This project is licensed under the MIT License.
