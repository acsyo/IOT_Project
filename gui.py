# GUI interface for my aquarium project - shows status and allows manual control
import sys, json, datetime
from PyQt5 import QtWidgets, QtCore
import paho.mqtt.client as mqtt
from init import (
    MqttAuth,
    TOPIC_TEMP, TOPIC_WATER, TOPIC_ALERTS,
    TOPIC_FEED_CMD, TOPIC_HEATER_CMD, TOPIC_PUMP_CMD,
    TOPIC_HEATER, TOPIC_COOLER, TOPIC_PUMP,
    DEFAULT_TARGET_TEMP, MAX_FEED_SECONDS
)

auth = MqttAuth()

class AquariumGUI(QtWidgets.QWidget):
    # these signals let us update the GUI from MQTT messages safely
    tempSignal = QtCore.pyqtSignal(float)  
    waterSignal = QtCore.pyqtSignal(float)
    alertSignal = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("My IoT Smart Aquarium")
        self.resize(600, 500)

        # Display current sensor readings
        self.tempLabel = QtWidgets.QLabel("Temperature: -- °C")
        self.waterLabel = QtWidgets.QLabel("Water Level: -- %")
        
        # Show status of equipment
        self.pumpStatus = QtWidgets.QLabel("Pump: OFF")
        self.heaterStatus = QtWidgets.QLabel("Heater: OFF")
        self.coolerStatus = QtWidgets.QLabel("Cooler: OFF")

        # Manual control buttons
        self.feedBtn = QtWidgets.QPushButton("Feed Fish")
        self.feedSeconds = QtWidgets.QSpinBox()
        self.feedSeconds.setRange(1, MAX_FEED_SECONDS)
        self.feedSeconds.setValue(3)

        # temperature control
        self.targetSpin = QtWidgets.QDoubleSpinBox()
        self.targetSpin.setRange(15, 35)
        self.targetSpin.setValue(DEFAULT_TARGET_TEMP)
        self.setTargetBtn = QtWidgets.QPushButton("Set Target Temp")

        # emergency refill button
        self.refillBtn = QtWidgets.QPushButton("Manual Refill → 100%")

        # area to show system alerts and messages
        self.alertsBox = QtWidgets.QTextEdit()
        self.alertsBox.setReadOnly(True)
        self.alertsBox.setMaximumHeight(150)

        # --- Layout ---
        layout = QtWidgets.QVBoxLayout()
        
        # Sensor readings group
        sensorGroup = QtWidgets.QGroupBox("Sensor Readings")
        sensorLayout = QtWidgets.QFormLayout()
        sensorLayout.addRow("Water Temperature:", self.tempLabel)
        sensorLayout.addRow("Water Level:", self.waterLabel)
        sensorGroup.setLayout(sensorLayout)
        
        # System status group
        statusGroup = QtWidgets.QGroupBox("System Status")
        statusLayout = QtWidgets.QFormLayout()
        statusLayout.addRow("Water Pump:", self.pumpStatus)
        statusLayout.addRow("Heater:", self.heaterStatus)
        statusLayout.addRow("Cooler:", self.coolerStatus)
        statusGroup.setLayout(statusLayout)
        
        # Manual controls group
        controlGroup = QtWidgets.QGroupBox("Manual Controls")
        controlLayout = QtWidgets.QFormLayout()
        
        feedRow = QtWidgets.QHBoxLayout()
        feedRow.addWidget(self.feedBtn)
        feedRow.addWidget(self.feedSeconds)
        feedRow.addWidget(QtWidgets.QLabel("seconds"))
        controlLayout.addRow("Fish Feeding:", feedRow)
        
        tempRow = QtWidgets.QHBoxLayout()
        tempRow.addWidget(self.targetSpin)
        tempRow.addWidget(self.setTargetBtn)
        controlLayout.addRow("Target Temperature:", tempRow)
        
        controlLayout.addRow("Water Refill:", self.refillBtn)
        controlGroup.setLayout(controlLayout)
        
        # Alerts group
        alertGroup = QtWidgets.QGroupBox("System Alerts & Status")
        alertLayout = QtWidgets.QVBoxLayout()
        alertLayout.addWidget(self.alertsBox)
        alertGroup.setLayout(alertLayout)
        
        # Add all groups to main layout
        layout.addWidget(sensorGroup)
        layout.addWidget(statusGroup)
        layout.addWidget(controlGroup)
        layout.addWidget(alertGroup)
        self.setLayout(layout)

        # --- Signals ---
        self.tempSignal.connect(self.update_temp)
        self.waterSignal.connect(self.update_water)
        self.alertSignal.connect(self.update_alerts)
        self.feedBtn.clicked.connect(self.send_feed_cmd)
        self.setTargetBtn.clicked.connect(self.send_target_temp)
        self.refillBtn.clicked.connect(self.send_refill_cmd)

        # --- MQTT ---
        self.client = mqtt.Client(
            client_id="gui.smart_aquarium",
            clean_session=True,
            transport=auth.transport,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        if auth.username: 
            self.client.username_pw_set(auth.username, auth.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(auth.host, auth.port, 60)
        self.client.loop_start()

    # ---------- MQTT ----------
    def on_connect(self, client, userdata, flags, rc):
        print(f"[GUI] Connected to MQTT: {rc}")
        client.subscribe([
            (TOPIC_TEMP,0), (TOPIC_WATER,0), (TOPIC_ALERTS,0),
            (TOPIC_HEATER,0), (TOPIC_COOLER,0), (TOPIC_PUMP,0)
        ])

    def on_message(self, client, userdata, msg):
        try: 
            data = json.loads(msg.payload.decode())
        except: 
            data = {}
            
        if msg.topic == TOPIC_TEMP:
            temp = data.get("temp")
            if temp is not None:
                self.tempSignal.emit(float(temp))
                
        elif msg.topic == TOPIC_WATER and "level" in data:
            self.waterSignal.emit(float(data["level"]))
            
        elif msg.topic == TOPIC_ALERTS:
            level = data.get("level","INFO")
            message = data.get("msg","")
            self.alertSignal.emit(level, message)
            
        elif msg.topic == TOPIC_HEATER:
            status = data.get("status", "off")
            if status == "on":
                self.heaterStatus.setText("Heater: ON")
                self.heaterStatus.setStyleSheet("color: red;")
            else:
                self.heaterStatus.setText("Heater: OFF")
                self.heaterStatus.setStyleSheet("color: black;")
                
        elif msg.topic == TOPIC_COOLER:
            status = data.get("status", "off")
            if status == "on":
                self.coolerStatus.setText("Cooler: ON")
                self.coolerStatus.setStyleSheet("color: blue;")
            else:
                self.coolerStatus.setText("Cooler: OFF")
                self.coolerStatus.setStyleSheet("color: black;")
                
        elif msg.topic == TOPIC_PUMP:
            status = data.get("status", "off")
            if status == "on":
                target = data.get("target", "")
                self.pumpStatus.setText(f"Pump: ON → {target}%")
                self.pumpStatus.setStyleSheet("color: blue;")
            else:
                self.pumpStatus.setText("Pump: OFF")
                self.pumpStatus.setStyleSheet("color: black;")

    # ---------- GUI updates ----------
    def update_temp(self, temp):  
        self.tempLabel.setText(f"{temp:.1f} °C")
        
    def update_water(self, level):  
        self.waterLabel.setText(f"{level:.1f} %")
        
    def update_alerts(self, level, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        color = {"INFO": "blue", "WARNING": "orange", "CRITICAL": "red"}.get(level, "black")
        
        formatted_msg = f'<span style="color: {color};">[{timestamp}] <b>{level}:</b> {message}</span>'
        self.alertsBox.append(formatted_msg)

    # ---------- Publish ----------
    def send_feed_cmd(self):
        sec = int(self.feedSeconds.value())
        self.client.publish(TOPIC_FEED_CMD, json.dumps({"feed":True,"seconds":sec}))

    def send_target_temp(self):
        t = float(self.targetSpin.value())
        self.client.publish(TOPIC_HEATER_CMD, json.dumps({"target":t}))

    def send_refill_cmd(self):
        # מבקשים מהמנהל להפעיל משאבה עד 100%
        self.client.publish(TOPIC_PUMP_CMD, json.dumps({"refill": True, "target": 100}))

    # ---------- Qt ----------
    def closeEvent(self, e):
        try:
            self.client.loop_stop(); self.client.disconnect()
        finally:
            e.accept()

def main():
    app = QtWidgets.QApplication(sys.argv); w = AquariumGUI(); w.show(); sys.exit(app.exec_())

if __name__ == "__main__":
    main()
