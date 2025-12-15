"""Basic tests for hap2mqtt."""

import pytest
from hap2mqtt.config import Config


def test_config_defaults():
    """Test default configuration."""
    config = Config()
    
    assert config.get('mqtt.broker') == 'localhost'
    assert config.get('mqtt.port') == 1883
    assert config.get('mqtt.base_topic') == 'homekit'
    assert config.get('homekit.pairing_data_file') == 'pairing_data.json'
    assert config.get('logging.level') == 'INFO'


def test_config_get_nested():
    """Test nested configuration access."""
    config = Config()
    
    # Test dot notation
    assert config.get('mqtt.broker') == 'localhost'
    
    # Test with default
    assert config.get('mqtt.nonexistent', 'default') == 'default'


def test_config_set():
    """Test setting configuration values."""
    config = Config()
    
    config.set('mqtt.broker', 'test.broker.com')
    assert config.get('mqtt.broker') == 'test.broker.com'
    
    config.set('mqtt.port', 8883)
    assert config.get('mqtt.port') == 8883


def test_config_merge():
    """Test configuration merging."""
    config = Config()
    
    loaded_config = {
        'mqtt': {
            'broker': 'custom.broker.com',
            'port': 8883,
        },
        'custom_key': 'custom_value',
    }
    
    config._merge_config(loaded_config)
    
    assert config.get('mqtt.broker') == 'custom.broker.com'
    assert config.get('mqtt.port') == 8883
    assert config.get('mqtt.base_topic') == 'homekit'  # Should retain default
    assert config.get('custom_key') == 'custom_value'
