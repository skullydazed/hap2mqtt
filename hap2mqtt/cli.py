"""Command-line interface for hap2mqtt."""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from .bridge import HomeKitMQTTBridge
from .config import Config

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Set up logging configuration.
    
    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


async def run_bridge(config: Config):
    """Run the HomeKit to MQTT bridge.
    
    Args:
        config: Configuration object
    """
    # Create bridge instance
    bridge = HomeKitMQTTBridge(
        mqtt_broker=config.get('mqtt.broker'),
        mqtt_port=config.get('mqtt.port'),
        mqtt_username=config.get('mqtt.username'),
        mqtt_password=config.get('mqtt.password'),
        mqtt_base_topic=config.get('mqtt.base_topic'),
        pairing_data_file=config.get('homekit.pairing_data_file'),
    )
    
    # Start the bridge
    if not await bridge.start():
        logger.error("Failed to start bridge")
        return 1
    
    # Load configured devices
    devices = config.get('homekit.devices', [])
    for device in devices:
        alias = device.get('alias')
        if alias:
            logger.info(f"Loading pairing for {alias}...")
            await bridge.load_pairing(alias)
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    # Run until stopped
    try:
        logger.info("Bridge is running. Press Ctrl+C to stop.")
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bridge.stop()
    
    return 0


async def discover_devices(timeout: int = 10):
    """Discover unpaired HomeKit devices.
    
    Args:
        timeout: Discovery timeout in seconds
    """
    from .homekit_controller import HomeKitController
    
    controller = HomeKitController()
    devices = await controller.discover_devices(timeout=timeout)
    
    if not devices:
        print("No unpaired devices found.")
        return
    
    print(f"\nFound {len(devices)} unpaired device(s):\n")
    for device_id, info in devices.items():
        print(f"  ID: {device_id}")
        print(f"  Name: {info['name']}")
        print(f"  Category: {info['category']}")
        print()


async def pair_device(device_id: str, pin: str, alias: Optional[str], config_file: Optional[str]):
    """Pair with a HomeKit device.
    
    Args:
        device_id: Device ID to pair with
        pin: PIN code for pairing
        alias: Optional alias for the device
        config_file: Optional config file to update
    """
    from .homekit_controller import HomeKitController
    
    controller = HomeKitController()
    
    if not alias:
        alias = device_id
    
    success = await controller.pair_device(device_id, pin, alias)
    
    if success:
        print(f"Successfully paired with device {alias}")
        
        # Update config file if specified
        if config_file:
            config = Config(config_file)
            devices = config.get('homekit.devices', [])
            
            # Add device if not already in config
            if not any(d.get('alias') == alias for d in devices):
                devices.append({'alias': alias})
                config.set('homekit.devices', devices)
                config.save()
                print(f"Added {alias} to configuration file")
    else:
        print(f"Failed to pair with device {device_id}")
        return 1
    
    return 0


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='HomeKit to MQTT Bridge',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Path to configuration file (YAML or JSON)',
        default='config.yaml',
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the bridge')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover unpaired devices')
    discover_parser.add_argument(
        '-t', '--timeout',
        type=int,
        default=10,
        help='Discovery timeout in seconds (default: 10)',
    )
    
    # Pair command
    pair_parser = subparsers.add_parser('pair', help='Pair with a device')
    pair_parser.add_argument('device_id', help='Device ID to pair with')
    pair_parser.add_argument('pin', help='PIN code for pairing (e.g., 123-45-678)')
    pair_parser.add_argument('-a', '--alias', help='Alias for the device')
    pair_parser.add_argument(
        '--update-config',
        action='store_true',
        help='Update configuration file with paired device',
    )
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging(log_level)
    
    # Handle commands
    if args.command == 'discover':
        return asyncio.run(discover_devices(timeout=args.timeout))
    
    elif args.command == 'pair':
        config_file = args.config if args.update_config else None
        return asyncio.run(pair_device(
            args.device_id,
            args.pin,
            args.alias,
            config_file,
        ))
    
    elif args.command == 'run' or args.command is None:
        # Load configuration
        config = Config(args.config)
        
        # Override log level from config if not verbose flag
        if not args.verbose:
            log_level = config.get('logging.level', 'INFO')
            setup_logging(log_level)
        
        return asyncio.run(run_bridge(config))
    
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
