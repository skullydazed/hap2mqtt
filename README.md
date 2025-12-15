# hap2mqtt

Bridge HomeKit controllers to MQTT using aiohomekit.

## Overview

`hap2mqtt` is a Python-based bridge that allows you to pair with HomeKit accessories (such as Homebridge or Philips Hue Bridge) and publish their status to MQTT. This enables integration with home automation systems like Home Assistant, Node-RED, or any other MQTT-compatible platform.

## Features

- **Pair with HomeKit Bridges**: Connect to HomeKit-compatible bridges like Homebridge or Philips Hue Bridge
- **Device Discovery**: Discover unpaired HomeKit devices on your network
- **Real-time Updates**: Subscribe to device events and publish changes to MQTT in real-time
- **MQTT Publishing**: Publish device states to MQTT with configurable topics
- **Persistent Pairing**: Store pairing data for automatic reconnection
- **Multiple Devices**: Support for monitoring multiple HomeKit bridges simultaneously
- **Command-line Interface**: Easy-to-use CLI for discovery, pairing, and running the bridge

## Installation

### From Source

```bash
git clone https://github.com/skullydazed/hap2mqtt.git
cd hap2mqtt
pip install -r requirements.txt
pip install -e .
```

## Configuration

Create a configuration file (e.g., `config.yaml`) based on the example:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to configure your MQTT broker settings:

```yaml
mqtt:
  broker: localhost        # Your MQTT broker hostname or IP
  port: 1883              # MQTT broker port
  username: null          # MQTT username (optional)
  password: null          # MQTT password (optional)
  base_topic: homekit     # Base topic for all MQTT messages

homekit:
  pairing_data_file: pairing_data.json
  devices:
    - alias: my_bridge    # Add your paired devices here

logging:
  level: INFO
```

## Usage

### Discover Unpaired Devices

Find HomeKit devices on your network:

```bash
hap2mqtt discover
```

Optional: Specify discovery timeout (default: 10 seconds):

```bash
hap2mqtt discover --timeout 30
```

### Pair with a Device

Pair with a HomeKit device using its ID and PIN:

```bash
hap2mqtt pair <device_id> <pin> --alias <friendly_name>
```

Example:

```bash
hap2mqtt pair "12:34:56:78:90:AB" "123-45-678" --alias homebridge
```

To automatically add the device to your configuration file:

```bash
hap2mqtt pair <device_id> <pin> --alias <friendly_name> --update-config
```

### Run the Bridge

Start the bridge to monitor devices and publish to MQTT:

```bash
hap2mqtt run
```

Or with a custom configuration file:

```bash
hap2mqtt run --config /path/to/config.yaml
```

Enable verbose logging:

```bash
hap2mqtt run --verbose
```

## MQTT Topics

The bridge publishes device states to MQTT using the following topic structure:

```
<base_topic>/<hostname>/<device_alias>/<accessory_id>/<service_type>/<characteristic_type>
```

Where:
- `hostname`: The hostname of the machine running hap2mqtt (supports multiple bridge instances)
- `device_alias`: The alias/name of the paired HomeKit device
- `accessory_id`: The accessory ID from HomeKit
- `service_type`: The HomeKit service type
- `characteristic_type`: The HomeKit characteristic type

Example topics:

```
homekit/livingroom-pi/homebridge/1/public.hap.service.lightbulb/public.hap.characteristic.on
homekit/livingroom-pi/homebridge/1/public.hap.service.lightbulb/public.hap.characteristic.brightness
homekit/bedroom-pi/hue_bridge/2/public.hap.service.lightbulb/public.hap.characteristic.hue
```

Full accessory state is also published to:

```
<base_topic>/<hostname>/<device_alias>/<accessory_id>/state
```

Bridge availability is published to:

```
<base_topic>/<hostname>/status
```

### Multiple Bridge Support

The hostname-based topic structure allows multiple hap2mqtt instances to run simultaneously on different machines, each publishing to their own topic namespace. This prevents conflicts and makes it easy to identify which bridge is publishing each message.

You can customize the hostname used in topics via the `mqtt.hostname` configuration option.

## Examples

### Example Workflow

1. **Discover devices**:
   ```bash
   hap2mqtt discover --timeout 15
   ```

2. **Pair with a Homebridge instance**:
   ```bash
   hap2mqtt pair "AA:BB:CC:DD:EE:FF" "031-45-154" --alias homebridge --update-config
   ```

3. **Run the bridge**:
   ```bash
   hap2mqtt run
   ```

### Integration with Home Assistant

Once running, you can use MQTT sensors in Home Assistant to monitor your HomeKit devices:

```yaml
mqtt:
  sensor:
    - name: "Living Room Light"
      state_topic: "homekit/homebridge/1/public.hap.service.lightbulb/public.hap.characteristic.on"
      
    - name: "Living Room Brightness"
      state_topic: "homekit/homebridge/1/public.hap.service.lightbulb/public.hap.characteristic.brightness"
```

## Requirements

- Python 3.9 or higher
- MQTT Broker (e.g., Mosquitto)
- HomeKit-compatible devices or bridges

## Dependencies

- `aiohomekit` - HomeKit controller implementation
- `aiomqtt` - Async MQTT client
- `pyyaml` - YAML configuration file support

## Troubleshooting

### "No unpaired devices found"

- Ensure your HomeKit device is in pairing mode
- Make sure you're on the same network as the device
- Try increasing the discovery timeout: `hap2mqtt discover --timeout 30`

### "Failed to pair with device"

- Double-check the PIN code
- Ensure the device hasn't reached its maximum pairing limit
- Try resetting the device and pairing again

### "Not connected to MQTT broker"

- Verify your MQTT broker is running and accessible
- Check the broker hostname, port, username, and password in your config
- Test connectivity: `mosquitto_sub -h <broker> -t "#" -v`

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [aiohomekit](https://github.com/Jc2k/aiohomekit) - Python HomeKit implementation
- Inspired by the need for HomeKit to MQTT integration in home automation
