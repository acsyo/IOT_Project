# Hardware emulator for my aquarium project - simulates sensors and equipment
import json, time, random
import paho.mqtt.client as mqtt
from init import (
    MqttAuth,
    # topics
    TOPIC_TEMP, TOPIC_WATER,
    TOPIC_FEEDER, TOPIC_HEATER, TOPIC_COOLER, TOPIC_PUMP,
    # params
    MAX_FEED_SECONDS, DEFAULT_TARGET_TEMP,
    MIN_SAFE_WATER, EVAP_RATE_PER_STEP,
    REFILL_RATE_PER_STEP, DEFAULT_REFILL_TARGET,
)

# Current state of the aquarium
water_temp = 26.0
water_level = 100.0  # start with full tank
heater_on = cooler_on = feeder_on = False
pump_on = False
pump_target = DEFAULT_REFILL_TARGET
auth = MqttAuth()

# used to add random temperature changes
temp_step_counter = 0  

def log(msg): print(f"[EMULATOR] {msg}")

# MQTT connection functions
def on_connect(client, userdata, flags, rc):
    log(f"Connected to MQTT broker, result code={rc}")
    # subscribe to equipment control topics
    client.subscribe([
        (TOPIC_FEEDER,0), (TOPIC_HEATER,0),
        (TOPIC_COOLER,0), (TOPIC_PUMP,0)
    ])

def on_message(client, userdata, msg):
    global feeder_on, heater_on, cooler_on, pump_on, pump_target
    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        data = {}

    if msg.topic == TOPIC_FEEDER:
        if data.get("status") == "on":
            sec = int(data.get("seconds", MAX_FEED_SECONDS))
            feeder_on = True; log(f"Fish feeder ON for {sec} seconds"); time.sleep(sec)
            feeder_on = False; log("Fish feeder OFF")

    elif msg.topic == TOPIC_HEATER:
        s = data.get("status"); heater_on = (s == "on"); log(f"Water heater -> {s}")

    elif msg.topic == TOPIC_COOLER:
        s = data.get("status"); cooler_on = (s == "on"); log(f"Water cooler -> {s}")

    elif msg.topic == TOPIC_PUMP:
        s = data.get("status")
        pump_on = (s == "on")
        pump_target = float(data.get("target", DEFAULT_REFILL_TARGET))
        log(f"Water pump -> {s} (target {pump_target}%)")

# Functions to simulate the aquarium behavior
def step_temperature():
    global water_temp, temp_step_counter
    
    # Add some random temperature change every 2 seconds to make it realistic
    temp_step_counter += 1
    environmental_change = 0.0
    if temp_step_counter >= 2:
        temp_step_counter = 0
        # Random temperature drift (like room temp changing)
        environmental_change = random.choice([-0.05, 0.05])
        print(f"[EMULATOR] Room temperature changed by: {environmental_change:+.2f}°C")
    
    # Small random changes each second
    drift = random.uniform(-0.01, 0.01)
    
    # Equipment effects on temperature
    actuator_change = 0.0
    if heater_on: 
        actuator_change += 0.1  # heater warms water slowly
    if cooler_on: 
        actuator_change -= 0.1  # cooler cools water slowly
        
    # Update temperature
    water_temp += environmental_change + actuator_change + drift
    water_temp = max(15.0, min(35.0, water_temp))  # keep within realistic range
    return round(water_temp, 2)

def step_water_level():
    global water_level, pump_on, pump_target

    # Water evaporates slowly over time
    evaporation = EVAP_RATE_PER_STEP
    water_level -= evaporation
    
    # Add tiny random variation
    variation = random.uniform(-0.001, 0.001)
    water_level += variation

    # 2. PUMP REFILL (gradual when active)
    if pump_on:
        refill_amount = REFILL_RATE_PER_STEP
        water_level += refill_amount
        if water_level >= pump_target:
            pump_on = False
            log(f"Pump OFF - Target {pump_target:.1f}% reached")

    # 3. SAFETY LIMITS
    water_level = max(MIN_SAFE_WATER, min(100.0, water_level))
    
    return round(water_level, 2)

# -------- main loop --------
def make_client():
    cl = mqtt.Client(
        client_id="emulator.smart_aquarium",
        clean_session=True,
        transport=auth.transport,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1  # תואם לקוד שלך
    )
    if auth.username:
        cl.username_pw_set(auth.username, auth.password or None)
    cl.on_connect = on_connect
    cl.on_message = on_message
    return cl

def main():
    client = make_client()
    log(f"CONNECTING TO {auth.host}:{auth.port}")
    client.connect(auth.host, auth.port, 60)
    client.loop_start()
    try:
        while True:
            # Sensor readings - just temperature and water level
            t = step_temperature()
            l = step_water_level()
            
            # Publish sensor data
            client.publish(TOPIC_TEMP,  json.dumps({"temp": t, "unit": "C"}))
            client.publish(TOPIC_WATER, json.dumps({"level": l}))
            
            time.sleep(1.0)  # Faster updates for responsive demo (1 second per reading)
    except KeyboardInterrupt:
        log("Shutting down emulator...")
    finally:
        client.loop_stop(); client.disconnect()

if __name__ == "__main__":
    main()
