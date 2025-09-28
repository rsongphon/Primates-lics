# LICS Edge Agent

[![Edge Agent CI](https://github.com/rsongphon/Primates-lics/workflows/Edge%20Agent%20CI/badge.svg)](https://github.com/rsongphon/Primates-lics/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-red.svg)](https://www.raspberrypi.org/)

The LICS Edge Agent is a Python-based application designed to run on edge devices (primarily Raspberry Pi) for laboratory instrument control, data collection, and experiment execution.

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **Hardware**: Raspberry Pi 4+ (recommended)
- **GPIO**: RPi.GPIO / gpiozero
- **Database**: SQLite (local storage)
- **Communication**: MQTT (Paho MQTT)
- **Video**: OpenCV, Picamera2
- **Web Automation**: Playwright
- **Task Scheduling**: APScheduler
- **Configuration**: YAML/JSON
- **Logging**: Python logging with structured output

## 🚀 Quick Start

### Prerequisites

- Raspberry Pi 4+ with Raspberry Pi OS
- Python 3.11+ installed
- Camera module (optional)
- GPIO-connected sensors/actuators

### Installation

1. **System Dependencies**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install system dependencies
   sudo apt install -y python3-pip python3-venv git
   sudo apt install -y libcamera-dev python3-picamera2  # For camera support
   sudo apt install -y python3-gpiozero python3-rpi.gpio  # For GPIO
   ```

2. **Clone and Setup**
   ```bash
   cd /opt
   sudo git clone https://github.com/rsongphon/Primates-lics.git
   cd Primates-lics/services/edge-agent
   ```

3. **Python Environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt
   ```

4. **Configuration**
   ```bash
   # Copy configuration template
   cp config/config.example.yaml config/config.yaml
   # Edit configuration for your setup
   nano config/config.yaml
   ```

5. **Run Agent**
   ```bash
   python src/main.py
   ```

### Quick Setup Script

```bash
# Run the automated setup script
curl -sSL https://raw.githubusercontent.com/rsongphon/Primates-lics/main/services/edge-agent/scripts/install.sh | bash
```

## 📁 Project Structure

```
services/edge-agent/
├── src/                    # Source code
│   ├── agent/             # Core agent modules
│   │   ├── device_manager.py  # Device management
│   │   ├── task_executor.py   # Task execution
│   │   ├── mqtt_client.py     # MQTT communication
│   │   └── data_collector.py  # Data collection
│   ├── hardware/          # Hardware interfaces
│   │   ├── gpio_controller.py # GPIO control
│   │   ├── sensors/           # Sensor drivers
│   │   ├── actuators/         # Actuator drivers
│   │   └── camera.py          # Camera interface
│   ├── tasks/             # Task definitions
│   │   ├── base_task.py       # Base task class
│   │   ├── behavioral_tasks.py # Behavioral experiments
│   │   └── data_tasks.py      # Data collection tasks
│   ├── storage/           # Local storage
│   │   ├── database.py        # SQLite interface
│   │   └── sync_manager.py    # Cloud sync
│   ├── utils/             # Utilities
│   └── main.py            # Application entry point
├── config/                # Configuration files
│   ├── config.yaml        # Main configuration
│   ├── device_map.yaml    # GPIO pin mapping
│   └── tasks/             # Task definitions
├── data/                  # Local data storage
├── logs/                  # Log files
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── requirements.txt       # Dependencies
└── systemd/              # Service files
```

## ⚙️ Configuration

### Main Configuration (`config/config.yaml`)

```yaml
# Agent Configuration
agent:
  id: "rpi-lab-001"
  name: "Lab A - Cage 1"
  location: "Building A, Room 101"

# MQTT Configuration
mqtt:
  broker: "mqtt.lics.example.com"
  port: 8883
  username: "${MQTT_USERNAME}"
  password: "${MQTT_PASSWORD}"
  use_tls: true
  topic_prefix: "labs/lab-a/devices"

# Hardware Configuration
hardware:
  gpio_mode: "BCM"  # BCM or BOARD
  camera:
    enabled: true
    resolution: [1920, 1080]
    framerate: 30
  sensors:
    - type: "temperature"
      pin: 4
      name: "ambient_temp"
    - type: "motion"
      pin: 18
      name: "motion_detector"
  actuators:
    - type: "led"
      pin: 23
      name: "status_led"
    - type: "buzzer"
      pin: 24
      name: "alert_buzzer"

# Storage Configuration
storage:
  database_path: "data/agent.db"
  max_storage_mb: 1024
  sync_interval_seconds: 300

# Logging Configuration
logging:
  level: "INFO"
  file: "logs/agent.log"
  max_size_mb: 10
  backup_count: 5
```

### GPIO Pin Mapping (`config/device_map.yaml`)

```yaml
# GPIO Pin Mappings for Raspberry Pi
pins:
  # Sensors
  temperature_sensor: 4
  humidity_sensor: 17
  motion_detector: 18
  light_sensor: 22

  # Actuators
  status_led: 23
  alert_buzzer: 24
  servo_motor: 25

  # I2C Devices
  i2c_sda: 2
  i2c_scl: 3

  # SPI Devices
  spi_mosi: 10
  spi_miso: 9
  spi_sclk: 11
  spi_ce0: 8
```

## 🔧 Hardware Interfaces

### GPIO Controller

```python
from src.hardware.gpio_controller import GPIOController

class ExperimentController:
    def __init__(self):
        self.gpio = GPIOController()

    def setup_experiment(self):
        # Setup LED
        self.gpio.setup_output_pin(23, "status_led")

        # Setup motion sensor
        self.gpio.setup_input_pin(18, "motion_detector", pull_up=True)

        # Setup callbacks
        self.gpio.add_event_callback(18, self.on_motion_detected)

    def on_motion_detected(self, pin):
        print(f"Motion detected on pin {pin}")
        self.gpio.set_pin_high(23)  # Turn on LED
```

### Sensor Integration

```python
from src.hardware.sensors.temperature import TemperatureSensor

class DataCollector:
    def __init__(self):
        self.temp_sensor = TemperatureSensor(pin=4)

    async def collect_data(self):
        temperature = await self.temp_sensor.read()
        return {
            "timestamp": datetime.utcnow(),
            "temperature": temperature,
            "unit": "celsius"
        }
```

### Camera Interface

```python
from src.hardware.camera import CameraController

class VideoStreamer:
    def __init__(self):
        self.camera = CameraController()

    async def start_recording(self, duration_seconds=60):
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        await self.camera.start_recording(filename, duration_seconds)
        return filename
```

## 📋 Task System

### Task Definition

```python
from src.tasks.base_task import BaseTask

class MotionDetectionTask(BaseTask):
    def __init__(self, config: dict):
        super().__init__(config)
        self.motion_pin = config.get("motion_pin", 18)
        self.led_pin = config.get("led_pin", 23)

    async def setup(self):
        """Setup task hardware and resources"""
        self.gpio.setup_input_pin(self.motion_pin, "motion")
        self.gpio.setup_output_pin(self.led_pin, "led")

    async def execute(self):
        """Main task execution logic"""
        try:
            while self.is_running:
                if self.gpio.read_pin(self.motion_pin):
                    await self.handle_motion_detected()
                await asyncio.sleep(0.1)
        except Exception as e:
            await self.handle_error(e)

    async def handle_motion_detected(self):
        """Handle motion detection event"""
        self.gpio.set_pin_high(self.led_pin)
        await self.log_event("motion_detected", {"timestamp": datetime.utcnow()})
        await asyncio.sleep(1)
        self.gpio.set_pin_low(self.led_pin)

    async def cleanup(self):
        """Cleanup task resources"""
        self.gpio.cleanup_pin(self.motion_pin)
        self.gpio.cleanup_pin(self.led_pin)
```

### Task Configuration

```json
{
  "task_id": "motion_detection_001",
  "type": "motion_detection",
  "parameters": {
    "motion_pin": 18,
    "led_pin": 23,
    "sensitivity": 0.5,
    "duration_minutes": 60
  },
  "schedule": {
    "start_time": "09:00",
    "end_time": "17:00",
    "repeat": "daily"
  }
}
```

## 🔗 Communication

### MQTT Client

```python
from src.agent.mqtt_client import MQTTClient

class AgentCommunication:
    def __init__(self):
        self.mqtt = MQTTClient()
        self.mqtt.on_message = self.handle_message

    async def connect(self):
        await self.mqtt.connect()
        await self.mqtt.subscribe("commands/+/+")

    async def handle_message(self, topic: str, payload: dict):
        """Handle incoming MQTT messages"""
        if "commands" in topic:
            await self.process_command(payload)

    async def send_telemetry(self, data: dict):
        """Send telemetry data to cloud"""
        topic = f"telemetry/{self.agent_id}/data"
        await self.mqtt.publish(topic, data)
```

### WebSocket Integration

```python
import asyncio
import websockets

class WebSocketClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)

    async def send_data(self, data: dict):
        if self.websocket:
            await self.websocket.send(json.dumps(data))
```

## 💾 Local Storage

### SQLite Database

```python
from src.storage.database import Database

class LocalStorage:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    async def store_telemetry(self, device_id: str, data: dict):
        """Store telemetry data locally"""
        await self.db.execute("""
            INSERT INTO telemetry (device_id, timestamp, data)
            VALUES (?, ?, ?)
        """, (device_id, datetime.utcnow(), json.dumps(data)))

    async def get_pending_sync_data(self):
        """Get data pending sync to cloud"""
        return await self.db.fetch_all("""
            SELECT * FROM telemetry WHERE synced = 0
            ORDER BY timestamp ASC
            LIMIT 1000
        """)
```

### Data Synchronization

```python
from src.storage.sync_manager import SyncManager

class DataSync:
    def __init__(self):
        self.sync_manager = SyncManager()

    async def sync_to_cloud(self):
        """Sync local data to cloud storage"""
        pending_data = await self.get_pending_data()

        for batch in self.batch_data(pending_data):
            try:
                await self.upload_batch(batch)
                await self.mark_as_synced(batch)
            except Exception as e:
                logger.error(f"Sync failed: {e}")
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test category
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/hardware/

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run hardware tests (requires actual hardware)
python -m pytest tests/hardware/ --hardware
```

### Hardware Mocking

```python
import pytest
from unittest.mock import Mock, patch

class TestGPIOController:
    @patch('RPi.GPIO.setup')
    @patch('RPi.GPIO.output')
    def test_led_control(self, mock_output, mock_setup):
        gpio = GPIOController()
        gpio.setup_output_pin(23, "led")
        gpio.set_pin_high(23)

        mock_setup.assert_called_with(23, GPIO.OUT)
        mock_output.assert_called_with(23, GPIO.HIGH)
```

## 🚀 Deployment

### Systemd Service

Create service file at `/etc/systemd/system/lics-agent.service`:

```ini
[Unit]
Description=LICS Edge Agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/Primates-lics/services/edge-agent
Environment=PATH=/opt/Primates-lics/services/edge-agent/venv/bin
ExecStart=/opt/Primates-lics/services/edge-agent/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Enable and start service
sudo systemctl enable lics-agent
sudo systemctl start lics-agent

# Check status
sudo systemctl status lics-agent

# View logs
sudo journalctl -u lics-agent -f
```

### Auto-update Script

```bash
#!/bin/bash
# scripts/update.sh

set -e

echo "Updating LICS Edge Agent..."

# Pull latest code
git pull origin main

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart lics-agent

echo "Update complete!"
```

## 📊 Monitoring

### Health Checks

```python
from src.utils.health import HealthChecker

class AgentHealth:
    def __init__(self):
        self.health_checker = HealthChecker()

    async def check_system_health(self):
        """Comprehensive health check"""
        return {
            "cpu_usage": await self.health_checker.get_cpu_usage(),
            "memory_usage": await self.health_checker.get_memory_usage(),
            "disk_usage": await self.health_checker.get_disk_usage(),
            "temperature": await self.health_checker.get_cpu_temperature(),
            "network": await self.health_checker.check_network_connectivity(),
            "gpio_status": await self.health_checker.check_gpio_status()
        }
```

### Logging

```python
import logging
from src.utils.logger import setup_logger

# Setup structured logging
logger = setup_logger(__name__)

class TaskExecutor:
    def __init__(self):
        self.logger = logger

    async def execute_task(self, task):
        self.logger.info("Starting task execution", extra={
            "task_id": task.id,
            "task_type": task.type,
            "device_id": self.device_id
        })
```

## 🔧 Troubleshooting

### Common Issues

1. **GPIO Permission Denied**
   ```bash
   # Add user to gpio group
   sudo usermod -a -G gpio pi
   ```

2. **Camera Not Working**
   ```bash
   # Enable camera interface
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   ```

3. **MQTT Connection Failed**
   ```bash
   # Check network connectivity
   ping mqtt.lics.example.com

   # Check MQTT credentials
   mosquitto_pub -h mqtt.lics.example.com -p 8883 -u username -P password -t test -m "test"
   ```

### Debug Mode

```bash
# Run with debug logging
python src/main.py --debug

# Enable GPIO debug
export GPIO_DEBUG=1
python src/main.py
```

## 🤝 Contributing

1. Test on actual hardware when possible
2. Use hardware mocking for unit tests
3. Follow Python type hints
4. Document GPIO pin usage
5. Test power consumption implications

See the main [Contributing Guide](../../CONTRIBUTING.md) for more details.

## 📚 Additional Resources

- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [GPIO Pinout Reference](https://pinout.xyz/)
- [Paho MQTT Documentation](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)
- [OpenCV Python Tutorial](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [SQLite Python Documentation](https://docs.python.org/3/library/sqlite3.html)