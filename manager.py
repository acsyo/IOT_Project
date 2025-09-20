# Smart manager for my aquarium - the "brain" that controls everything automatically
import json
import paho.mqtt.client as mqtt
from init import (
    MqttAuth,
    # sensors
    TOPIC_TEMP, TOPIC_WATER,
    # controls (GUI->manager)
    TOPIC_FEED_CMD, TOPIC_HEATER_CMD, TOPIC_PUMP_CMD,
    # actuators (manager->emulator)
    TOPIC_FEEDER, TOPIC_HEATER, TOPIC_COOLER, TOPIC_PUMP,
    # alerts
    TOPIC_ALERTS,
    # params
    DEFAULT_TARGET_TEMP, HEATER_HYSTERESIS, MAX_FEED_SECONDS,
    # water management
    WATER_CRITICAL, WATER_LOW, WATER_TARGET,
)

auth = MqttAuth()
target_temp = DEFAULT_TARGET_TEMP  # temperature we want to maintain
last_water_level = None
pump_on = False  # keep track of whether pump is running

# for manual refill mode (None = automatic, number = manual target)
manual_refill_target = None

def make_client():
    cl = mqtt.Client(
        client_id="manager.smart_aquarium",
        clean_session=True,
        transport=auth.transport,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1
    )
    if auth.username: cl.username_pw_set(auth.username, auth.password)
    cl.on_connect, cl.on_message = on_connect, on_message
    cl.connect(auth.host, auth.port, 60)
    cl.loop_forever()

def on_connect(client, userdata, flags, rc):
    print("Smart manager connected to MQTT:", rc)
    # subscribe to all the topics we need to monitor
    client.subscribe([
        (TOPIC_TEMP, 0),
        (TOPIC_WATER, 0),
        (TOPIC_FEED_CMD, 0),
        (TOPIC_HEATER_CMD, 0),
        (TOPIC_PUMP_CMD, 0),
    ])

def send_alert(client, level, msg):
    client.publish(TOPIC_ALERTS, json.dumps({"level": level, "msg": msg}))

def heater_cooler_control(client, temp):
    global target_temp
    print(f"[MANAGER] Temp control: current={temp}°C, target={target_temp}°C, hysteresis={HEATER_HYSTERESIS}")
    if temp < target_temp - HEATER_HYSTERESIS:
        print(f"[MANAGER] Activating HEATER (temp {temp} < {target_temp - HEATER_HYSTERESIS})")
        client.publish(TOPIC_HEATER, json.dumps({"status": "on"}))
        client.publish(TOPIC_COOLER, json.dumps({"status": "off"}))
    elif temp > target_temp + HEATER_HYSTERESIS:
        print(f"[MANAGER] Activating COOLER (temp {temp} > {target_temp + HEATER_HYSTERESIS})")
        client.publish(TOPIC_COOLER, json.dumps({"status": "on"}))
        client.publish(TOPIC_HEATER, json.dumps({"status": "off"}))
    else:
        print(f"[MANAGER] Temperature OK - turning off both heater and cooler")
        client.publish(TOPIC_HEATER, json.dumps({"status": "off"}))
        client.publish(TOPIC_COOLER, json.dumps({"status": "off"}))

def set_pump(client, on: bool, target: float = None):
    global pump_on
    pump_on = on
    payload = {"status": "on" if on else "off"}
    if on and target is not None:
        payload["target"] = float(target)
    print(f"[MANAGER] Pump command: {payload}")
    client.publish(TOPIC_PUMP, json.dumps(payload))

def on_message(client, userdata, msg):
    global target_temp, last_water_level, manual_refill_target
    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        data = {}

    if msg.topic == TOPIC_TEMP:
        temp = float(data.get("temp", 0))
        heater_cooler_control(client, temp)
        if temp < 18:
            send_alert(client, "WARNING", f"Water too cold: {temp}C")
        elif temp > 30:
            send_alert(client, "WARNING", f"Water too hot: {temp}C")

    elif msg.topic == TOPIC_WATER:
        level = float(data.get("level", 0))
        print(f"[MANAGER] Water level: {level:.1f}%, pump_on: {pump_on}")

        # ----- WATER LEVEL ALERTS -----
        if level <= WATER_CRITICAL:
            send_alert(client, "CRITICAL", f"CRITICAL: Water level at {level:.1f}%!")
        elif level <= WATER_LOW:
            send_alert(client, "WARNING", f"Low water level: {level:.1f}%")

        # ----- SIMPLE AUTO-REFILL LOGIC -----
        if manual_refill_target is not None:
            # Manual refill mode (from GUI button)
            if level >= manual_refill_target - 0.5:
                set_pump(client, False)
                send_alert(client, "INFO", f"Manual refill complete: {level:.1f}%")
                manual_refill_target = None
            else:
                set_pump(client, True, target=manual_refill_target)
        else:
            # Automatic refill logic
            if level <= WATER_LOW and not pump_on:  # Start refill
                set_pump(client, True, target=WATER_TARGET)
                send_alert(client, "INFO", f"Auto-refill started (level: {level:.1f}%)")
            elif level >= WATER_TARGET and pump_on:  # Stop refill
                set_pump(client, False)
                send_alert(client, "INFO", f"Auto-refill complete (level: {level:.1f}%)")

        last_water_level = level

    elif msg.topic == TOPIC_HEATER_CMD:
        t = data.get("target")
        if t is not None:
            target_temp = float(t)
            send_alert(client, "INFO", f"Target temp set to {target_temp}C")

    elif msg.topic == TOPIC_FEED_CMD:
        if data.get("feed"):
            sec = int(data.get("seconds", MAX_FEED_SECONDS))
            client.publish(TOPIC_FEEDER, json.dumps({"status": "on", "seconds": sec}))
            send_alert(client, "INFO", f"Feeder ON for {sec}s")

    elif msg.topic == TOPIC_PUMP_CMD:
        # Manual refill button
        if data.get("refill"):
            manual_refill_target = float(data.get("target", WATER_TARGET))
            set_pump(client, True, target=manual_refill_target)
            send_alert(client, "INFO", f"Manual refill started → {manual_refill_target:.1f}%")

if __name__ == "__main__":
    make_client()