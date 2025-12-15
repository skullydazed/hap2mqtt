"""Configuration management for hap2mqtt."""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_file: Path to configuration file (YAML or JSON)
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = self._default_config()
        
        if config_file:
            self.load(config_file)

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            'mqtt': {
                'broker': 'localhost',
                'port': 1883,
                'username': None,
                'password': None,
                'base_topic': 'homekit',
            },
            'homekit': {
                'pairing_data_file': 'pairing_data.json',
                'devices': [],
            },
            'logging': {
                'level': 'INFO',
            },
        }

    def load(self, config_file: str):
        """Load configuration from file.
        
        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    loaded_config = yaml.safe_load(f)
                elif config_path.suffix == '.json':
                    loaded_config = json.load(f)
                else:
                    logger.error(f"Unsupported configuration file format: {config_path.suffix}")
                    return
            
            # Merge loaded config with defaults
            self._merge_config(loaded_config)
            logger.info(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            logger.error(f"Error loading configuration from {config_file}: {e}")

    def _merge_config(self, loaded_config: Dict[str, Any]):
        """Merge loaded configuration with defaults.
        
        Args:
            loaded_config: Loaded configuration dictionary
        """
        for key, value in loaded_config.items():
            if key in self.config and isinstance(value, dict) and isinstance(self.config[key], dict):
                self.config[key].update(value)
            else:
                self.config[key] = value

    def save(self, config_file: Optional[str] = None):
        """Save configuration to file.
        
        Args:
            config_file: Path to configuration file (uses loaded file if not specified)
        """
        save_path = config_file or self.config_file
        
        if not save_path:
            logger.error("No configuration file specified")
            return
        
        config_path = Path(save_path)
        
        try:
            with open(config_path, 'w') as f:
                if config_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False)
                elif config_path.suffix == '.json':
                    json.dump(self.config, f, indent=2)
                else:
                    logger.error(f"Unsupported configuration file format: {config_path.suffix}")
                    return
            
            logger.info(f"Saved configuration to {save_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration to {save_path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'mqtt.broker')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

    def set(self, key: str, value: Any):
        """Set a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
