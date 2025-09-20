# Data logger for my aquarium - saves all sensor data to SQLite database
import json
import sqlite3
import datetime
import paho.mqtt.client as mqtt
from init import (
    MqttAuth,
    TOPIC_TEMP, TOPIC_WATER, TOPIC_ALERTS,
)

class AquariumDataManager:
    def __init__(self, db_path="aquarium_data.db"):
        self.db_path = db_path
        self.auth = MqttAuth()
        self.setup_database()
        
    def setup_database(self):
        """Creates the database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for sensor readings (temperature, water level)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                sensor_type TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                water_level REAL
            )
        ''')
        
        # Table for system alerts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("[DATA LOGGER] Database ready")
        
    def store_sensor_data(self, sensor_type, **data):
        """Saves sensor readings to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_readings (sensor_type, temperature, humidity, water_level)
            VALUES (?, ?, ?, ?)
        ''', (
            sensor_type,
            data.get('temperature'),
            data.get('humidity'), 
            data.get('water_level')
        ))
        
        conn.commit()
        conn.close()
        
    def store_alert(self, level, message):
        """Store alert to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts (level, message) VALUES (?, ?)
        ''', (level, message))
        
        conn.commit()
        conn.close()
        print(f"[DATA] Alert stored: {level} - {message}")
        
    def get_recent_readings(self, limit=10):
        """Get recent sensor readings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, sensor_type, temperature, humidity, water_level
            FROM sensor_readings 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        return results
        
    def get_recent_alerts(self, limit=5):
        """Get recent alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, level, message 
            FROM alerts 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        return results

    # MQTT Callbacks
    def on_connect(self, client, userdata, flags, rc):
        print(f"[DATA] Connected to MQTT broker: {rc}")
        client.subscribe([
            (TOPIC_TEMP, 0),
            (TOPIC_WATER, 0),
            (TOPIC_ALERTS, 0),
        ])

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
        except Exception:
            return

        if msg.topic == TOPIC_TEMP:
            # DHT sensor data (temperature + humidity)
            self.store_sensor_data(
                sensor_type="DHT",
                temperature=data.get("temp"),
                humidity=data.get("humidity")
            )
            
        elif msg.topic == TOPIC_WATER:
            # Water level sensor data
            self.store_sensor_data(
                sensor_type="WATER_LEVEL",
                water_level=data.get("level")
            )
            
        elif msg.topic == TOPIC_ALERTS:
            # Store alerts for history tracking
            level = data.get("level", "INFO")
            message = data.get("msg", "")
            self.store_alert(level, message)

    def start_collection(self):
        """Start MQTT data collection"""
        client = mqtt.Client(
            client_id="data_manager.smart_aquarium",
            clean_session=True,
            transport=self.auth.transport,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        
        if self.auth.username:
            client.username_pw_set(self.auth.username, self.auth.password)
            
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        
        print(f"[DATA] Connecting to {self.auth.host}:{self.auth.port}")
        client.connect(self.auth.host, self.auth.port, 60)
        client.loop_forever()

if __name__ == "__main__":
    data_manager = AquariumDataManager()
    try:
        data_manager.start_collection()
    except KeyboardInterrupt:
        print("[DATA] Data manager stopped")