"""HomeKit Controller for discovering and managing HomeKit accessories."""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from aiohomekit import Controller
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import ServicesTypes

logger = logging.getLogger(__name__)


class HomeKitController:
    """HomeKit Controller for pairing and managing accessories."""

    def __init__(self, pairing_data_file: str = "pairing_data.json"):
        """Initialize the HomeKit controller.
        
        Args:
            pairing_data_file: Path to store pairing data
        """
        self.controller = Controller()
        self.pairing_data_file = pairing_data_file
        self.pairings: Dict[str, Any] = {}
        self.update_callbacks: Dict[str, Callable] = {}

    async def discover_devices(self, timeout: int = 10) -> Dict[str, Any]:
        """Discover unpaired HomeKit devices.
        
        Args:
            timeout: Discovery timeout in seconds
            
        Returns:
            Dictionary of discovered devices
        """
        logger.info(f"Discovering HomeKit devices for {timeout} seconds...")
        discoveries = {}
        
        try:
            async for discovery in self.controller.async_discover(timeout):
                device_id = discovery.description.id
                discoveries[device_id] = {
                    'name': discovery.description.name,
                    'id': device_id,
                    'category': discovery.description.category,
                    'config_num': discovery.description.config_num,
                    'status_flags': discovery.description.status_flags,
                }
                logger.info(f"Discovered device: {discovery.description.name} ({device_id})")
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            
        return discoveries

    async def pair_device(self, device_id: str, pin: str, alias: Optional[str] = None) -> bool:
        """Pair with a HomeKit device.
        
        Args:
            device_id: Device ID to pair with
            pin: PIN code for pairing
            alias: Optional alias for the pairing
            
        Returns:
            True if pairing successful, False otherwise
        """
        if not alias:
            alias = device_id
            
        try:
            logger.info(f"Attempting to pair with device {device_id} (alias: {alias})...")
            pairing = await self.controller.async_pair(device_id, alias, pin)
            self.pairings[alias] = pairing
            logger.info(f"Successfully paired with {alias}")
            return True
        except Exception as e:
            logger.error(f"Failed to pair with device {device_id}: {e}")
            return False

    async def load_pairing(self, alias: str) -> bool:
        """Load an existing pairing from the controller.
        
        Args:
            alias: Alias of the pairing to load
            
        Returns:
            True if pairing loaded successfully, False otherwise
        """
        try:
            pairing = self.controller.get_pairing(alias)
            if pairing:
                self.pairings[alias] = pairing
                logger.info(f"Loaded pairing for {alias}")
                return True
            else:
                logger.warning(f"No pairing found for {alias}")
                return False
        except Exception as e:
            logger.error(f"Error loading pairing for {alias}: {e}")
            return False

    async def get_accessories(self, alias: str) -> Optional[Dict[str, Any]]:
        """Get accessories from a paired device.
        
        Args:
            alias: Alias of the pairing
            
        Returns:
            Dictionary of accessories or None if failed
        """
        if alias not in self.pairings:
            logger.error(f"No pairing found for {alias}")
            return None
            
        try:
            pairing = self.pairings[alias]
            accessories = await pairing.async_list_accessories_and_characteristics()
            logger.info(f"Retrieved {len(accessories)} accessories from {alias}")
            return accessories
        except Exception as e:
            logger.error(f"Error getting accessories from {alias}: {e}")
            return None

    async def read_characteristics(self, alias: str, characteristics: list) -> Optional[Dict]:
        """Read characteristic values from a paired device.
        
        Args:
            alias: Alias of the pairing
            characteristics: List of (aid, iid) tuples to read
            
        Returns:
            Dictionary of characteristic values or None if failed
        """
        if alias not in self.pairings:
            logger.error(f"No pairing found for {alias}")
            return None
            
        try:
            pairing = self.pairings[alias]
            values = await pairing.async_get_characteristics(characteristics)
            return values
        except Exception as e:
            logger.error(f"Error reading characteristics from {alias}: {e}")
            return None

    async def subscribe_to_events(self, alias: str, callback: Callable) -> bool:
        """Subscribe to events from a paired device.
        
        Args:
            alias: Alias of the pairing
            callback: Callback function to call on events
            
        Returns:
            True if subscription successful, False otherwise
        """
        if alias not in self.pairings:
            logger.error(f"No pairing found for {alias}")
            return False
            
        try:
            pairing = self.pairings[alias]
            self.update_callbacks[alias] = callback
            
            # Subscribe to all characteristics that support events
            accessories = await pairing.async_list_accessories_and_characteristics()
            characteristics_to_subscribe = []
            
            for accessory in accessories:
                aid = accessory['aid']
                for service in accessory.get('services', []):
                    for char in service.get('characteristics', []):
                        iid = char['iid']
                        perms = char.get('perms', [])
                        if 'ev' in perms:  # Event notification support
                            characteristics_to_subscribe.append((aid, iid))
            
            if characteristics_to_subscribe:
                await pairing.async_subscribe(characteristics_to_subscribe)
                logger.info(f"Subscribed to {len(characteristics_to_subscribe)} characteristics from {alias}")
            
            # Set up the callback handler
            pairing.dispatcher_connect(self._handle_event)
            
            return True
        except Exception as e:
            logger.error(f"Error subscribing to events from {alias}: {e}")
            return False

    def _handle_event(self, data: Dict[str, Any]):
        """Handle incoming events from HomeKit devices.
        
        Args:
            data: Event data from the device
        """
        # Find which pairing this event is from
        for alias, pairing in self.pairings.items():
            if alias in self.update_callbacks:
                callback = self.update_callbacks[alias]
                try:
                    # Call the callback with the event data
                    asyncio.create_task(callback(alias, data))
                except Exception as e:
                    logger.error(f"Error in event callback for {alias}: {e}")

    async def remove_pairing(self, alias: str) -> bool:
        """Remove a pairing.
        
        Args:
            alias: Alias of the pairing to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            if alias in self.pairings:
                pairing = self.pairings[alias]
                await pairing.async_unpair()
                del self.pairings[alias]
                if alias in self.update_callbacks:
                    del self.update_callbacks[alias]
                logger.info(f"Removed pairing for {alias}")
                return True
            else:
                logger.warning(f"No pairing found for {alias}")
                return False
        except Exception as e:
            logger.error(f"Error removing pairing for {alias}: {e}")
            return False

    async def close(self):
        """Close all connections."""
        logger.info("Closing HomeKit controller...")
        for alias, pairing in self.pairings.items():
            try:
                await pairing.async_close()
            except Exception as e:
                logger.error(f"Error closing pairing {alias}: {e}")
