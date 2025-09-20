# Configuration file for my IoT aquarium project
from dataclasses import dataclass

# MQTT broker settings - using free HiveMQ service
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 8000
USERNAME = ""
PASSWORD = ""
TRANSPORT = "websockets"

# Main topic for all aquarium messages
COMM_TOPIC = "aquarium/"

# Topics for sensor data
TOPIC_TEMP        = COMM_TOPIC + "sensors/water_temp"
TOPIC_WATER       = COMM_TOPIC + "sensors/water_level"

# Topics for user commands from the GUI
TOPIC_FEED_CMD    = COMM_TOPIC + "controls/feed_cmd"        # feed the fish
TOPIC_HEATER_CMD  = COMM_TOPIC + "controls/target_temp"     # set temperature
TOPIC_PUMP_CMD    = COMM_TOPIC + "controls/refill_cmd"      # manual refill

# Topics for controlling equipment
TOPIC_FEEDER      = COMM_TOPIC + "actuators/feeder"         # fish feeder
TOPIC_HEATER      = COMM_TOPIC + "actuators/heater"         # water heater
TOPIC_COOLER      = COMM_TOPIC + "actuators/cooler"         # water cooler
TOPIC_PUMP        = COMM_TOPIC + "actuators/pump"           # water pump

# Topic for system alerts
TOPIC_ALERTS      = COMM_TOPIC + "alerts"                   

# Temperature settings
DEFAULT_TARGET_TEMP = 24.0  # good temperature for tropical fish
HEATER_HYSTERESIS   = 0.5   # prevents heater from turning on/off too much
MAX_FEED_SECONDS    = 3     # max feeding time

# Water behavior settings - made these realistic
MIN_SAFE_WATER       = 10.0      # emergency minimum water level
EVAP_RATE_PER_STEP   = 0.02      # how fast water evaporates (0.02% per second)
REFILL_RATE_PER_STEP = 0.05      # how fast pump refills (0.05% per second)
DEFAULT_REFILL_TARGET= 85.0      # stop refilling at this level

# When to trigger water level alerts
WATER_CRITICAL       = 20.0      # critical - need water now!
WATER_LOW            = 70.0      # low - start refilling
WATER_TARGET         = 85.0      # good level - stop refilling

@dataclass
class MqttAuth:
    host: str = BROKER_HOST
    port: int = BROKER_PORT
    username: str = USERNAME
    password: str = PASSWORD
    transport: str = TRANSPORT
