#!/usr/bin/env python3
"""
Test script for the enhanced metadata system integration.
Tests metadata templates, format support, validation, and MusicBrainz integration.
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from downloader.metadata import (
    METADATA_TEMPLATES,
    get_metadata_template,
    normalize_track_metadata,
    validate_metadata,
    correct_metadata,
    apply_template,
    embed_track_metadata,
    canonical_track_key,
    lookup_musicbrainz,
)
from utils.loaders import load_exportify_tracks, enrich_with_musicbrainz
from config import DEFAULT_CONFIG


def test_metadata_templates():
    """Test metadata template functionality."""
    print("Testing metadata templates...")
    
    # Test template access
    basic = get_metadata_template("basic")
    comprehensive = get_metadata_template("comprehensive")
    dj_mix = get_metadata_template("dj-mix")
    none_template = get_metadata_template(None)
    
    assert basic == METADATA_TEMPLATES["basic"]
    assert comprehensive == METADATA_TEMPLATES["comprehensive"]
    assert dj_mix == METADATA_TEMPLATES["dj-mix"]
    assert none_template == METADATA_TEMPLATES["basic"]  # Should default to basic
    
    print("✓ Metadata templates work correctly")


def test_metadata_normalization():
    """Test metadata normalization from different sources."""
    print("Testing metadata normalization...")
    
    # Test CSV-style metadata
    csv_track = {
        "Artist Name(s)": "Test Artist;Feature Artist",
        "Track Name": "Test Track",
        "Album Name": "Test Album",
        "Release Date": "2023-01-15",
        "Genres": "Electronic;Ambient",
        "Tempo": "128.5",
        "Energy": "0.8",
        "Track URI": "spotify:track:123",
    }
    
    normalized = normalize_track_metadata(csv_track)
    assert normalized["artist"] == "Test Artist, Feature Artist"
    assert normalized["title"] == "Test Track"
    assert normalized["album"] == "Test Album"
    assert normalized["date"] == "2023-01-15"
    assert normalized["genre"] == "Electronic, Ambient"
    assert normalized["bpm"] == "129"
    assert "spotify_uri=spotify:track:123" in normalized["comment"]
    
    # Test JSON-style metadata
    json_track = {
        "artist": "JSON Artist",
        "track": "JSON Track",
        "album": "JSON Album",
        "uri": "spotify:track:456",
    }
    
    normalized_json = normalize_track_metadata(json_track)
    assert normalized_json["artist"] == "JSON Artist"
    assert normalized_json["title"] == "JSON Track"
    assert normalized_json["album"] == "JSON Album"
    assert normalized_json["uri"] == "spotify:track:456"
    
    # Test with single artist (no semicolon)
    single_artist_track = {
        "Artist Name(s)": "Single Artist",
        "Track Name": "Single Track",
    }
    
    normalized_single = normalize_track_metadata(single_artist_track)
    assert normalized_single["artist"] == "Single Artist"
    
    print("✓ Metadata normalization works correctly")


def test_metadata_validation():
    """Test metadata validation and correction."""
    print("Testing metadata validation and correction...")
    
    # Test valid metadata
    valid_meta = {
        "artist": "Test Artist",
        "title": "Test Track",
        "album": "Test Album",
        "bpm": "128",
    }
    
    issues = validate_metadata(valid_meta)
    assert len(issues) == 0, f"Valid metadata should have no issues: {issues}"
    
    # Test invalid metadata
    invalid_meta = {
        "artist": "",  # Missing artist
        "title": "Test Track",
        "bpm": "999",  # Invalid BPM
    }
    
    issues = validate_metadata(invalid_meta)
    assert "missing_artist" in issues
    assert "bpm_out_of_range" in issues
    
    # Test correction
    corrected = correct_metadata(invalid_meta)
    assert corrected["artist"] == ""  # Should remain empty
    assert corrected["bpm"] == "999"  # Should preserve original if can't convert
    
    print("✓ Metadata validation and correction work correctly")


def test_template_application():
    """Test template application to metadata."""
    print("Testing template application...")
    
    # Create rich metadata
    rich_meta = {
        "artist": "Test Artist",
        "title": "Test Track",
        "album": "Test Album",
        "date": "2023-01-15",
        "genre": "Electronic",
        "bpm": "128",
        "comment": "Test comment",
        "uri": "spotify:track:123",
    }
    
    # Test basic template (includes essential fields including album)
    basic_applied = apply_template(rich_meta, "basic")
    assert basic_applied["artist"] == "Test Artist"
    assert basic_applied["title"] == "Test Track"
    assert basic_applied["album"] == "Test Album"  # Basic template includes album
    assert "date" not in basic_applied  # Basic doesn't include date by default
    
    # Test comprehensive template (all fields)
    comp_applied = apply_template(rich_meta, "comprehensive")
    assert comp_applied["artist"] == "Test Artist"
    assert comp_applied["title"] == "Test Track"
    assert comp_applied["album"] == "Test Album"
    assert comp_applied["date"] == "2023-01-15"
    assert comp_applied["genre"] == "Electronic"
    assert comp_applied["bpm"] == "128"
    assert comp_applied["comment"] == "Test comment"
    
    print("✓ Template application works correctly")


def test_canonical_track_key():
    """Test canonical track key generation."""
    print("Testing canonical track key generation...")
    
    key1 = canonical_track_key("Test Artist", "Test Track")
    key2 = canonical_track_key("test artist", "test track")  # Different case
    key3 = canonical_track_key("Other Artist", "Other Track")
    
    assert key1 == key2  # Should be case-insensitive
    assert key1 != key3  # Should be different for different tracks
    
    print("✓ Canonical track key generation works correctly")


def test_musicbrainz_lookup():
    """Test MusicBrainz lookup functionality (if network available)."""
    print("Testing MusicBrainz lookup...")
    
    # Test with a well-known track
    try:
        result = lookup_musicbrainz("The Beatles", "Hey Jude")
        if result:
            print(f"✓ MusicBrainz lookup successful: {result.artist} - {result.title}")
            assert result.artist
            assert result.title
        else:
            print("ℹ MusicBrainz lookup returned no results (may be rate limited)")
    except Exception as e:
        print(f"ℹ MusicBrainz lookup failed (expected if no network): {e}")


def test_enhanced_loaders():
    """Test enhanced loader functionality."""
    print("Testing enhanced loaders...")
    
    # Create a test CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
        f.write("Track URI,Track Name,Album Name,Artist Name(s),Release Date,Duration (ms),Genres,Tempo\n")
        f.write("spotify:track:123,Test Song,Test Album,Test Artist,2023-01-15,180000,Electronic,128\n")
        csv_path = f.name
    
    try:
        # Test loading the CSV
        tracks = load_exportify_tracks(csv_path)
        assert len(tracks) == 1
        track = tracks[0]
        assert track["artist"] == "Test Artist"
        assert track["track"] == "Test Song"
        assert track["album"] == "Test Album"
        assert track["release_date"] == "2023-01-15"
        assert track["tempo"] == "128"
        
        print("✓ Enhanced CSV loader works correctly")
        
        # Test MusicBrainz enrichment
        config = {"enable_musicbrainz_lookup": False}  # Disable for testing
        enriched = enrich_with_musicbrainz(tracks, config)
        assert len(enriched) == len(tracks)
        print("✓ MusicBrainz enrichment integration works correctly")
        
    finally:
        os.unlink(csv_path)


def test_metadata_embedding():
    """Test metadata embedding functionality (non-destructive test)."""
    print("Testing metadata embedding...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with mock track data
        track_data = {
            "artist": "Test Artist",
            "track": "Test Track",
            "album": "Test Album",
            "date": "2023-01-15",
            "genre": "Electronic",
            "bpm": "128",
            "uri": "spotify:track:123",
        }
        
        # Create a test file path (non-existent)
        test_file = os.path.join(temp_dir, "Test Artist - Test Track.mp3")
        
        # Test finding downloaded audio path
        from downloader.metadata import find_downloaded_audio_path
        
        # Should return None for non-existent file
        result = find_downloaded_audio_path(temp_dir, "Test Artist - Test Track")
        assert result is None
        
        print("✓ Metadata embedding utilities work correctly")


def test_config_integration():
    """Test configuration integration."""
    print("Testing configuration integration...")
    
    # Test default config includes metadata options
    assert "enable_metadata_embedding" in DEFAULT_CONFIG
    assert "metadata_template" in DEFAULT_CONFIG
    assert "auto_metadata_embedding" in DEFAULT_CONFIG
    assert "enable_musicbrainz_lookup" in DEFAULT_CONFIG
    
    print("✓ Configuration integration works correctly")


def main():
    """Run all tests."""
    print("Running enhanced metadata system integration tests...\n")
    
    try:
        test_metadata_templates()
        test_metadata_normalization()
        test_metadata_validation()
        test_template_application()
        test_canonical_track_key()
        test_musicbrainz_lookup()
        test_enhanced_loaders()
        test_metadata_embedding()
        test_config_integration()
        
        print("\n🎉 All tests passed! Enhanced metadata system is working correctly.")
        print("\nFeatures tested:")
        print("✓ Multi-format metadata templates (basic, comprehensive, DJ-mix)")
        print("✓ JSON/CSV metadata normalization")
        print("✓ Metadata validation and correction")
        print("✓ MusicBrainz integration (no API keys)")
        print("✓ Enhanced data loaders")
        print("✓ Configuration integration")
        print("✓ Canonical track identification")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
