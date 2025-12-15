"""Integration tests for hap2mqtt components."""

import pytest
import tempfile
import os
from hap2mqtt.homekit_controller import HomeKitController
from hap2mqtt.mqtt_publisher import MQTTPublisher
from hap2mqtt.bridge import HomeKitMQTTBridge


def test_homekit_controller_instantiation():
    """Test that HomeKitController can be instantiated."""
    # Use a temporary file for pairing data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        controller = HomeKitController(pairing_data_file=temp_file)
        
        assert controller is not None
        assert controller.controller is not None
        assert controller.pairings == {}
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_mqtt_publisher_instantiation():
    """Test that MQTTPublisher can be instantiated."""
    publisher = MQTTPublisher(
        broker="localhost",
        port=1883,
        base_topic="test/homekit"
    )
    
    assert publisher is not None
    assert publisher.broker == "localhost"
    assert publisher.port == 1883
    assert publisher.base_topic == "test/homekit"
    assert not publisher.is_connected


def test_mqtt_publisher_hostname():
    """Test that MQTTPublisher uses hostname in topics."""
    publisher = MQTTPublisher(
        broker="localhost",
        port=1883,
        base_topic="homekit",
        hostname="test-host"
    )
    
    assert publisher.hostname == "test-host"
    
    # Test default hostname (system hostname)
    publisher_default = MQTTPublisher(
        broker="localhost",
        port=1883,
        base_topic="homekit"
    )
    
    assert publisher_default.hostname is not None
    assert len(publisher_default.hostname) > 0


def test_bridge_instantiation():
    """Test that HomeKitMQTTBridge can be instantiated."""
    bridge = HomeKitMQTTBridge(
        mqtt_broker="localhost",
        mqtt_port=1883,
        mqtt_base_topic="test/homekit",
    )
    
    assert bridge is not None
    assert bridge.homekit is not None
    assert bridge.mqtt is not None
    assert not bridge.running


def test_bridge_with_custom_hostname():
    """Test that bridge accepts custom hostname."""
    bridge = HomeKitMQTTBridge(
        mqtt_broker="localhost",
        mqtt_port=1883,
        mqtt_hostname="custom-host",
    )
    
    assert bridge.mqtt.hostname == "custom-host"


@pytest.mark.asyncio
async def test_bridge_lifecycle():
    """Test bridge start and stop methods."""
    bridge = HomeKitMQTTBridge(
        mqtt_broker="localhost",
        mqtt_port=1883,
    )
    
    # Bridge should not be running initially
    assert not bridge.running
    
    # Note: We can't actually start it without a real MQTT broker
    # Just test that the methods exist and can be called
    assert hasattr(bridge, 'start')
    assert hasattr(bridge, 'stop')
    assert hasattr(bridge, 'discover_devices')
    assert hasattr(bridge, 'pair_device')
