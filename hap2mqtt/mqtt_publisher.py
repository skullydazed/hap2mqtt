"""MQTT Publisher for sending HomeKit device data to MQTT."""

import asyncio
import json
import logging
import socket
from typing import Dict, Any, Optional
import aiomqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """MQTT Publisher for HomeKit device data."""

    def __init__(
        self,
        broker: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        base_topic: str = "homekit",
        client_id: Optional[str] = None,
        hostname: Optional[str] = None,
    ):
        """Initialize the MQTT publisher.
        
        Args:
            broker: MQTT broker hostname/IP
            port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
            base_topic: Base topic for all messages
            client_id: MQTT client ID (optional)
            hostname: Hostname to use in topics (defaults to system hostname)
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.base_topic = base_topic
        self.hostname = hostname or socket.gethostname()
        self.client_id = client_id or "hap2mqtt"
        self.client: Optional[aiomqtt.Client] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to the MQTT broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}...")
            
            # Create the client context manager
            self.client = aiomqtt.Client(
                hostname=self.broker,
                port=self.port,
                username=self.username,
                password=self.password,
                identifier=self.client_id,
            )
            
            await self.client.__aenter__()
            self._connected = True
            logger.info("Connected to MQTT broker")
            
            # Publish availability message
            await self.publish_availability("online")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from the MQTT broker."""
        if self.client and self._connected:
            try:
                await self.publish_availability("offline")
                await self.client.__aexit__(None, None, None)
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {e}")
            finally:
                self._connected = False

    async def publish(self, topic: str, payload: Any, retain: bool = False) -> bool:
        """Publish a message to MQTT.
        
        Args:
            topic: Topic to publish to (without base topic)
            payload: Message payload (will be JSON encoded if dict/list)
            retain: Whether to retain the message
            
        Returns:
            True if publish successful, False otherwise
        """
        if not self._connected or not self.client:
            logger.error("Not connected to MQTT broker")
            return False
            
        try:
            full_topic = f"{self.base_topic}/{topic}"
            
            # Convert payload to string if needed
            if isinstance(payload, (dict, list)):
                payload_str = json.dumps(payload)
            else:
                payload_str = str(payload)
            
            await self.client.publish(full_topic, payload_str, retain=retain)
            logger.debug(f"Published to {full_topic}: {payload_str}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False

    async def publish_availability(self, status: str):
        """Publish availability status.
        
        Args:
            status: Availability status (online/offline)
        """
        topic = f"{self.hostname}/status"
        await self.publish(topic, status, retain=True)

    async def publish_device_state(
        self,
        device_alias: str,
        accessory_id: int,
        service_type: str,
        characteristic_type: str,
        value: Any,
    ):
        """Publish device state to MQTT.
        
        Args:
            device_alias: Device alias/name
            accessory_id: Accessory ID
            service_type: Service type
            characteristic_type: Characteristic type
            value: Characteristic value
        """
        topic = f"{self.hostname}/{device_alias}/{accessory_id}/{service_type}/{characteristic_type}"
        await self.publish(topic, value, retain=True)

    async def publish_accessory_state(
        self,
        device_alias: str,
        accessory_id: int,
        state: Dict[str, Any],
    ):
        """Publish full accessory state to MQTT.
        
        Args:
            device_alias: Device alias/name
            accessory_id: Accessory ID
            state: Full state dictionary
        """
        topic = f"{self.hostname}/{device_alias}/{accessory_id}/state"
        await self.publish(topic, state, retain=True)

    async def publish_discovery(
        self,
        device_alias: str,
        accessory_id: int,
        discovery_info: Dict[str, Any],
    ):
        """Publish discovery information for Home Assistant integration.
        
        Args:
            device_alias: Device alias/name
            accessory_id: Accessory ID
            discovery_info: Discovery information
        """
        topic = f"{self.hostname}/{device_alias}/{accessory_id}/config"
        await self.publish(topic, discovery_info, retain=True)

    @property
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self._connected
