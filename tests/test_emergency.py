"""
Tests for Emergency Control System

Tests the halt/resume functionality and state persistence.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch


class TestEmergencyControl:
    """Test the EmergencyControl class."""
    
    def test_halt_sets_halted_state(self, temp_dir):
        """Test that halt() sets halted to True."""
        from qsconnect.emergency import EmergencyControl
        
        state_file = temp_dir / "system_state.json"
        
        with patch('qsconnect.emergency.STATE_FILE', state_file):
            result = EmergencyControl.halt("Test halt")
            
            assert result is True
            assert state_file.exists()
            
            with open(state_file) as f:
                data = json.load(f)
            
            assert data["halted"] is True
            assert data["reason"] == "Test halt"
    
    def test_resume_sets_halted_false(self, temp_dir):
        """Test that resume() sets halted to False."""
        from qsconnect.emergency import EmergencyControl
        
        state_file = temp_dir / "system_state.json"
        
        with patch('qsconnect.emergency.STATE_FILE', state_file):
            # First halt
            EmergencyControl.halt("Test")
            
            # Then resume
            result = EmergencyControl.resume()
            
            assert result is True
            
            with open(state_file) as f:
                data = json.load(f)
            
            assert data["halted"] is False
    
    def test_is_halted_returns_correct_state(self, temp_dir):
        """Test that is_halted() returns correct state."""
        from qsconnect.emergency import EmergencyControl
        
        state_file = temp_dir / "system_state.json"
        
        with patch('qsconnect.emergency.STATE_FILE', state_file):
            # Initially not halted (no file)
            assert EmergencyControl.is_halted() is False
            
            # After halt
            EmergencyControl.halt("Test")
            assert EmergencyControl.is_halted() is True
            
            # After resume
            EmergencyControl.resume()
            assert EmergencyControl.is_halted() is False
    
    def test_is_halted_handles_missing_file(self, temp_dir):
        """Test that is_halted() returns False when file doesn't exist."""
        from qsconnect.emergency import EmergencyControl
        
        state_file = temp_dir / "nonexistent.json"
        
        with patch('qsconnect.emergency.STATE_FILE', state_file):
            assert EmergencyControl.is_halted() is False
    
    def test_get_status_returns_full_state(self, temp_dir):
        """Test that get_status() returns complete state dict."""
        from qsconnect.emergency import EmergencyControl
        
        state_file = temp_dir / "system_state.json"
        
        with patch('qsconnect.emergency.STATE_FILE', state_file):
            EmergencyControl.halt("Dashboard Override")
            
            status = EmergencyControl.get_status()
            
            assert isinstance(status, dict)
            assert "halted" in status
            assert "reason" in status
            assert "timestamp" in status
            assert status["halted"] is True
            assert status["reason"] == "Dashboard Override"
    
    def test_get_status_handles_missing_file(self, temp_dir):
        """Test get_status() with missing file."""
        from qsconnect.emergency import EmergencyControl
        
        state_file = temp_dir / "nonexistent.json"
        
        with patch('qsconnect.emergency.STATE_FILE', state_file):
            status = EmergencyControl.get_status()
            
            assert status["halted"] is False
            assert "reason" in status
