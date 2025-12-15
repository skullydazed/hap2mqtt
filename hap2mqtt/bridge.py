"""Main bridge class for HomeKit to MQTT."""

import asyncio
import logging
from typing import Dict, Any, Optional
from .homekit_controller import HomeKitController
from .mqtt_publisher import MQTTPublisher

logger = logging.getLogger(__name__)


class HomeKitMQTTBridge:
    """Bridge between HomeKit and MQTT."""

    def __init__(
        self,
        mqtt_broker: str,
        mqtt_port: int = 1883,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        mqtt_base_topic: str = "homekit",
        mqtt_hostname: Optional[str] = None,
        pairing_data_file: str = "pairing_data.json",
    ):
        """Initialize the bridge.
        
        Args:
            mqtt_broker: MQTT broker hostname/IP
            mqtt_port: MQTT broker port
            mqtt_username: MQTT username (optional)
            mqtt_password: MQTT password (optional)
            mqtt_base_topic: Base topic for MQTT messages
            mqtt_hostname: Hostname to use in MQTT topics (optional, defaults to system hostname)
            pairing_data_file: Path to store pairing data
        """
        self.homekit = HomeKitController(pairing_data_file=pairing_data_file)
        self.mqtt = MQTTPublisher(
            broker=mqtt_broker,
            port=mqtt_port,
            username=mqtt_username,
            password=mqtt_password,
            base_topic=mqtt_base_topic,
            hostname=mqtt_hostname,
        )
        self.running = False
        self._tasks = []

    async def start(self):
        """Start the bridge."""
        logger.info("Starting HomeKit to MQTT bridge...")
        
        # Connect to MQTT
        if not await self.mqtt.connect():
            logger.error("Failed to connect to MQTT broker")
            return False
        
        self.running = True
        logger.info("Bridge started successfully")
        return True

    async def stop(self):
        """Stop the bridge."""
        logger.info("Stopping HomeKit to MQTT bridge...")
        self.running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Close connections
        await self.homekit.close()
        await self.mqtt.disconnect()
        
        logger.info("Bridge stopped")

    async def discover_devices(self, timeout: int = 10) -> Dict[str, Any]:
        """Discover unpaired HomeKit devices.
        
        Args:
            timeout: Discovery timeout in seconds
            
        Returns:
            Dictionary of discovered devices
        """
        return await self.homekit.discover_devices(timeout=timeout)

    async def pair_device(self, device_id: str, pin: str, alias: Optional[str] = None) -> bool:
        """Pair with a HomeKit device.
        
        Args:
            device_id: Device ID to pair with
            pin: PIN code for pairing
            alias: Optional alias for the pairing
            
        Returns:
            True if pairing successful, False otherwise
        """
        success = await self.homekit.pair_device(device_id, pin, alias)
        if success:
            # After pairing, start monitoring the device
            await self.start_monitoring_device(alias or device_id)
        return success

    async def load_pairing(self, alias: str) -> bool:
        """Load an existing pairing.
        
        Args:
            alias: Alias of the pairing to load
            
        Returns:
            True if pairing loaded successfully, False otherwise
        """
        success = await self.homekit.load_pairing(alias)
        if success:
            # After loading, start monitoring the device
            await self.start_monitoring_device(alias)
        return success

    async def start_monitoring_device(self, alias: str):
        """Start monitoring a paired device and publish its state to MQTT.
        
        Args:
            alias: Alias of the pairing to monitor
        """
        logger.info(f"Starting monitoring for device {alias}...")
        
        # Get initial state
        accessories = await self.homekit.get_accessories(alias)
        if not accessories:
            logger.error(f"Failed to get accessories for {alias}")
            return
        
        # Publish initial state
        await self._publish_accessories_state(alias, accessories)
        
        # Subscribe to events
        await self.homekit.subscribe_to_events(alias, self._handle_device_event)
        
        logger.info(f"Monitoring started for device {alias}")

    async def _publish_accessories_state(self, alias: str, accessories: list):
        """Publish state of all accessories to MQTT.
        
        Args:
            alias: Device alias
            accessories: List of accessories
        """
        for accessory in accessories:
            aid = accessory['aid']
            
            # Build state for this accessory
            state = {}
            
            for service in accessory.get('services', []):
                service_type = service.get('type', 'unknown')
                
                for char in service.get('characteristics', []):
                    char_type = char.get('type', 'unknown')
                    char_value = char.get('value')
                    
                    if char_value is not None:
                        state[f"{service_type}/{char_type}"] = char_value
                        
                        # Publish individual characteristic
                        await self.mqtt.publish_device_state(
                            device_alias=alias,
                            accessory_id=aid,
                            service_type=service_type,
                            characteristic_type=char_type,
                            value=char_value,
                        )
            
            # Publish full accessory state
            if state:
                await self.mqtt.publish_accessory_state(
                    device_alias=alias,
                    accessory_id=aid,
                    state=state,
                )

    async def _handle_device_event(self, alias: str, event_data: Dict[str, Any]):
        """Handle device events and publish to MQTT.
        
        Args:
            alias: Device alias
            event_data: Event data from the device
        """
        logger.debug(f"Received event from {alias}: {event_data}")
        
        # Event data format from aiohomekit:
        # {(aid, iid): {'value': value, ...}, ...}
        for (aid, iid), char_data in event_data.items():
            value = char_data.get('value')
            
            # Get the full accessories to find service and characteristic types
            accessories = await self.homekit.get_accessories(alias)
            if not accessories:
                continue
            
            # Find the characteristic
            for accessory in accessories:
                if accessory['aid'] != aid:
                    continue
                
                for service in accessory.get('services', []):
                    for char in service.get('characteristics', []):
                        if char['iid'] == iid:
                            service_type = service.get('type', 'unknown')
                            char_type = char.get('type', 'unknown')
                            
                            # Publish the update
                            await self.mqtt.publish_device_state(
                                device_alias=alias,
                                accessory_id=aid,
                                service_type=service_type,
                                characteristic_type=char_type,
                                value=value,
                            )
                            
                            logger.info(f"Published update for {alias}/{aid}/{service_type}/{char_type}: {value}")

    async def run(self):
        """Run the bridge continuously."""
        if not self.running:
            await self.start()
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Bridge run loop cancelled")
        finally:
            await self.stop()
