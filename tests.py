import pytest
import json
import os
import sqlite3
import tempfile
import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import (
    app, normalize_json, init_db, load_data, should_reload_data,
)

client = TestClient(app)

test_json = {
    "id": {
        "0": "5vYA1mW9g2Coh1HUFUSmlb",
        "1": "2klCjJcucgGQysgH170npL",
        "2": "093PI3mdUvOSlvMYDwnV1e"
    },
    "title": {
        "0": "3AM",
        "1": "4 Walls", 
        "2": "11:11"
    },
    "danceability": {
        "0": 0.521,
        "1": 0.735,
        "2": 0.612
    },
    "energy": {
        "0": 0.673,
        "1": 0.849,
        "2": 0.756
    },
    "key": {
        "0": 4,
        "1": 7,
        "2": 2
    },
    "loudness": {
        "0": -8.123,
        "1": -6.456,
        "2": -7.789
    },
    "mode": {
        "0": 1,
        "1": 0,
        "2": 1
    },
    "acousticness": {
        "0": 0.234,
        "1": 0.567,
        "2": 0.345
    },
    "instrumentalness": {
        "0": 0.001,
        "1": 0.0,
        "2": 0.123
    },
    "liveness": {
        "0": 0.123,
        "1": 0.456,
        "2": 0.234
    },
    "valence": {
        "0": 0.678,
        "1": 0.345,
        "2": 0.567
    },
    "tempo": {
        "0": 128.0,
        "1": 140.5,
        "2": 95.8
    },
    "duration_ms": {
        "0": 210000,
        "1": 195000,
        "2": 230000
    },
    "time_signature": {
        "0": 4,
        "1": 4,
        "2": 3
    },
    "num_bars": {
        "0": 64,
        "1": 72,
        "2": 80
    },
    "num_sections": {
        "0": 8,
        "1": 9,
        "2": 10
    },
    "num_segments": {
        "0": 320,
        "1": 298,
        "2": 345
    },
    "class_label": {
        "0": 1,
        "1": 2,
        "2": 1
    }
}

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def temp_json():
    """Create a temporary JSON file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_json, f)
        json_path = f.name
    yield json_path
    if os.path.exists(json_path):
        os.unlink(json_path)

class TestDataNormalization:
    """Test data normalization functionality"""
    
    def test_normalize_json_basic(self):
        """Test basic JSON normalization"""
        result = normalize_json(test_json)
        
        assert len(result) == 3
        assert result[0]["index"] == 0
        assert result[0]["id"] == "5vYA1mW9g2Coh1HUFUSmlb"
        assert result[0]["title"] == "3AM"
        assert result[0]["danceability"] == 0.521
        assert result[0]["star_rating"] == 0.0
        
        assert result[1]["index"] == 1
        assert result[1]["id"] == "2klCjJcucgGQysgH170npL"
        assert result[1]["title"] == "4 Walls"
        
    def test_normalize_json_empty(self):
        """Test normalization with empty data"""
        result = normalize_json({})
        assert result == []
        
        result = normalize_json(None)
        assert result == []
        
    def test_normalize_json_handles_missing_values(self):
        """Test normalization with missing values"""
        incomplete_json = {
            "id": {"0": "test1", "1": "test2"},
            "title": {"0": "Song1"}
        }
        result = normalize_json(incomplete_json)
        assert len(result) == 2
        assert result[0]["title"] == "Song1"
        assert result[1]["title"] is None

    """Test database initialization and operations"""
    
    def test_init_db(self, temp_db):
        """Test database initialization"""
        # Mock sqlite3.connect to use temp database
        with patch('api.sqlite3.connect') as mock_connect:
            mock_conn = mock_connect.return_value
            mock_conn.execute.return_value = None
            mock_conn.commit.return_value = None
            mock_conn.close.return_value = None
            
            init_db()
            
            mock_connect.assert_called_once_with('database.db')
            mock_conn.execute.assert_called_once()
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
    
    def test_should_reload_data_no_json(self, temp_db):
        """Test should_reload_data when JSON file doesn't exist"""
        result = should_reload_data("nonexistent.json", temp_db)
        assert result is False
        
    def test_should_reload_data_no_db(self, temp_json):
        """Test should_reload_data when database doesn't exist"""
        result = should_reload_data(temp_json, "nonexistent.db")
        assert result is True
        
    def test_should_reload_data_empty_db(self, temp_json, temp_db):
        """Test should_reload_data with empty database"""
        conn = sqlite3.connect(temp_db)
        conn.execute('''
            CREATE TABLE songs (
                idx INTEGER PRIMARY KEY,
                id TEXT,
                title TEXT,
                star_rating REAL DEFAULT 0.0
            )
        ''')
        conn.commit()
        conn.close()
        
        result = should_reload_data(temp_json, temp_db)
        assert result is True
        
    def test_should_reload_data_newer_json(self, temp_json, temp_db):
        """Test should_reload_data when JSON is newer than database"""
        conn = sqlite3.connect(temp_db)
        conn.execute('''
            CREATE TABLE songs (
                idx INTEGER PRIMARY KEY,
                id TEXT,
                title TEXT,
                star_rating REAL DEFAULT 0.0
            )
        ''')
        conn.execute("INSERT INTO songs (id, title) VALUES ('test', 'test')")
        conn.commit()
        conn.close()
        
        # Make JSON file newer
        time.sleep(0.1)
        os.utime(temp_json)
        
        result = should_reload_data(temp_json, temp_db)
        assert result is True
        
    def test_should_reload_data_older_json(self, temp_json, temp_db):
        """Test should_reload_data when JSON is older than database"""
        # Create database after JSON file
        time.sleep(0.1)
        conn = sqlite3.connect(temp_db)
        conn.execute('''
            CREATE TABLE songs (
                idx INTEGER PRIMARY KEY,
                id TEXT,
                title TEXT,
                star_rating REAL DEFAULT 0.0
            )
        ''')
        conn.execute("INSERT INTO songs (id, title) VALUES ('test', 'test')")
        conn.commit()
        conn.close()
        
        result = should_reload_data(temp_json, temp_db)
        assert result is False

class TestDataLoading:
    """Test data loading functionality"""
    
    def test_load_data_basic(self, temp_json):
        """Test basic data loading"""
        with patch('api.sqlite3.connect') as mock_connect:
            mock_conn = mock_connect.return_value
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_conn.commit.return_value = None
            mock_conn.close.return_value = None
            
            count = load_data(temp_json)
            
            assert count == 3
            mock_connect.assert_called_with('database.db')
            
    def test_load_data_preserve_ratings(self, temp_json):
        """Test loading data while preserving ratings"""
        with patch('api.sqlite3.connect') as mock_connect:
            mock_conn = mock_connect.return_value
            # Mock existing ratings
            mock_conn.execute.return_value.fetchall.return_value = [
                ('5vYA1mW9g2Coh1HUFUSmlb', 4.5),
                ('2klCjJcucgGQysgH170npL', 3.0)
            ]
            mock_conn.commit.return_value = None
            mock_conn.close.return_value = None
            
            count = load_data(temp_json, preserve_ratings=True)
            
            assert count == 3
            
    def test_load_data_reset_ratings(self, temp_json):
        """Test loading data and resetting ratings"""
        with patch('api.sqlite3.connect') as mock_connect:
            mock_conn = mock_connect.return_value
            mock_conn.execute.return_value.fetchall.return_value = []
            mock_conn.commit.return_value = None
            mock_conn.close.return_value = None
            
            count = load_data(temp_json, preserve_ratings=False)
            
            assert count == 3
            
    def test_load_data_file_not_found(self):
        """Test loading data from non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_data("nonexistent.json")
            
    def test_load_data_invalid_json(self):
        """Test loading invalid JSON data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            invalid_json_path = f.name
            
        try:
            with pytest.raises(json.JSONDecodeError):
                load_data(invalid_json_path)
        finally:
            os.unlink(invalid_json_path)
            
    def test_load_data_missing_attributes(self):
        """Test loading data with missing attributes - should handle None values properly"""
        minimal_json = {
            "id": {"0": "test_song_1", "1": "test_song_2"},
            "title": {"0": "Test Song 1", "1": "Test Song 2"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(minimal_json, f)
            minimal_json_path = f.name
            
        try:
            with patch('api.sqlite3.connect') as mock_connect:
                mock_conn = mock_connect.return_value
                mock_conn.execute.return_value.fetchall.return_value = []
                mock_conn.commit.return_value = None
                mock_conn.close.return_value = None
                
                count = load_data(minimal_json_path, preserve_ratings=False)
                
                assert count == 2
                
                insert_calls = [call for call in mock_conn.execute.call_args_list if 'INSERT' in str(call)]
                assert len(insert_calls) == 2  # Two songs
                
                first_insert_call = insert_calls[0]
                insert_args = first_insert_call[0][1]  # Get the tuple of arguments
                
                assert None in insert_args 
                assert 'Test Song 1' in insert_args 
                
        finally:
            os.unlink(minimal_json_path)
            
    def test_load_data_partial_attributes(self):
        """Test loading data with partially missing attributes across songs"""
        partial_json = {
            "id": {"0": "song1", "1": "song2", "2": "song3"},
            "title": {"0": "Song 1", "1": "Song 2", "2": "Song 3"},
            "danceability": {"0": 0.5, "1": 0.7},  # Missing for song3
            "energy": {"0": 0.8}  # Missing for song2 and song3
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(partial_json, f)
            partial_json_path = f.name
            
        try:
            with patch('api.sqlite3.connect') as mock_connect:
                mock_conn = mock_connect.return_value
                mock_conn.execute.return_value.fetchall.return_value = []
                mock_conn.commit.return_value = None
                mock_conn.close.return_value = None
                
                count = load_data(partial_json_path, preserve_ratings=False)
                
                assert count == 3
                
                insert_calls = [call for call in mock_conn.execute.call_args_list if 'INSERT' in str(call)]
                assert len(insert_calls) == 3  # Three songs
                
                # Check first song (has both danceability and energy)
                first_args = insert_calls[0][0][1]  # Get the tuple of arguments
                assert 'song1' in first_args
                assert 0.5 in first_args  # danceability
                assert 0.8 in first_args  # energy
                
                # Check second song (has danceability but missing energy)
                second_args = insert_calls[1][0][1]  # Get the tuple of arguments
                assert 'song2' in second_args
                assert 0.7 in second_args  # danceability
                assert None in second_args  # Missing energy should be None (becomes NULL)
                
                # Check third song (missing both danceability and energy)
                third_args = insert_calls[2][0][1]  # Get the tuple of arguments
                assert 'song3' in third_args
                assert None in third_args  # Should have None values (become NULL)
                
        finally:
            os.unlink(partial_json_path)


class TestAPIEndpoints:
    """Test REST API endpoints"""
    
    def test_get_all_songs_default(self):
        """Get all songs with default pagination"""
        response = client.get("/songs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_all_songs_pagination(self):
        """Get all songs with custom pagination"""
        response = client.get("/songs?page=1&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_all_songs_invalid_pagination(self):
        """Test pagination with invalid parameters"""
        response = client.get("/songs?page=0")
        assert response.status_code == 422
        
        response = client.get("/songs?limit=0")
        assert response.status_code == 422
        
        response = client.get("/songs?limit=101")
        assert response.status_code == 422
        
    def test_search_by_title_exists(self):
        """Search by title for existing song"""
        response = client.get("/songs/search?title=3AM")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_search_by_title_not_exists(self):
        """Search by title for non-existent song"""
        response = client.get("/songs/search?title=NonExistentSong")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
        
    def test_search_by_title_missing_param(self):
        """Test search without title parameter"""
        response = client.get("/songs/search")
        assert response.status_code == 422
        
    def test_rate_song_valid(self):
        """Rate a song with valid rating"""
        response = client.put("/songs/test_id/rating", json={"rating": 4.5})
        # May be 404 if song doesn't exist, but endpoint accepts valid rating
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert data["rating"] == 4.5
            assert data["song_id"] == "test_id"
            
    def test_rate_song_invalid_rating_high(self):
        """Rate a song with rating too high"""
        response = client.put("/songs/test_id/rating", json={"rating": 6.0})
        assert response.status_code == 400
        data = response.json()
        assert "Rating must be between 0 and 5" in data["detail"]
        
    def test_rate_song_invalid_rating_low(self):
        """Rate a song with negative rating"""
        response = client.put("/songs/test_id/rating", json={"rating": -1.0})
        assert response.status_code == 400
        
    def test_rate_song_invalid_rating_format(self):
        """Test rating with invalid format"""
        response = client.put("/songs/test_id/rating", json={"rating": "invalid"})
        assert response.status_code == 422
        
    def test_rate_song_missing_rating(self):
        """Test rating without rating field"""
        response = client.put("/songs/test_id/rating", json={})
        assert response.status_code == 422
    

# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])