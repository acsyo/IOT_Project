# My IoT Aquarium Project

This is a smart aquarium that monitors and controls temperature and water level, and does automatic feeding using Python and MQTT.

## What it does

- Monitors water temperature and level
- Automatically turns heater/cooler on and off to keep temperature as user defines
- Automatically refills water when it gets low (below 70%)
- Shows everything on a GUI dashboard
- Saves all data to a database
- Sends alerts when something is wrong (temperature is too high or too low, water level is below safe level)

## How it works

The system has 4 main parts:
1. **emulator.py** - Pretends to be the real aquarium hardware (sensors and pumps)
2. **manager.py** - The "brain" that makes decisions about heating/cooling/refilling
3. **gui.py** - The interface where you can see what's happening and control things manually
4. **data_manager.py** - Saves all the sensor data to a SQLite database

They all talk to each other using MQTT messages over the internet.

## Files in this project

- `emulator.py` - Simulates the physical aquarium sensors and equipment
- `manager.py` - Controls everything automatically based on sensor readings  
- `gui.py` - User interface to see status and manual controls
- `data_manager.py` - Logs all data to database
- `init.py` - Settings and configuration for the whole system


The aquarium slowly loses water (evaporation) and the temperature changes a bit randomly to make it realistic. The system automatically responds to keep everything in the right range.