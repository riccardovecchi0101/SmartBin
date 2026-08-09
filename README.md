# SmartBin 🗑️

An IoT-based smart waste management system designed to monitor and manage waste bins remotely.

## Overview

SmartBin combines sensors, IoT communication and a web application to monitor the status of waste bins and support more efficient collection management.

Each bin uses an ultrasonic sensor and a load cell to estimate its fill level by combining distance and weight measurements. When configurable thresholds are exceeded, the system can automatically close the bin.

The bins communicate with the central application using MQTT, allowing their status to be monitored remotely.

## Features

* 📡 MQTT-based communication
* ⚖️ Waste weight measurement using a load cell
* 📏 Fill-level estimation using an ultrasonic sensor
* 🔒 Automatic lid control based on configurable thresholds
* 🖥️ LCD status and anomaly reporting
* 🌐 Web application for remote monitoring
* 🔓 Manual opening and closing of bins
* 🗺️ Interactive map of deployed bins
* 🚛 Collection route management
* 👥 Operator-oriented management interface

## System Architecture

```text
                    ┌──────────────────┐
                    │   SmartBin       │
                    │                  │
                    │ Ultrasonic       │
                    │ Load Cell        │
                    │ LCD              │
                    │ Lid Control      │
                    └────────┬─────────┘
                             │
                            MQTT
                             │
                             ▼
                    ┌──────────────────┐
                    │   Backend        │
                    │                  │
                    │ MQTT             │
                    │ Business Logic   │
                    │ Database         │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Web Application│
                    │                  │
                    │ Monitoring       │
                    │ Manual Control   │
                    │ Map              │
                    │ Routes           │
                    └──────────────────┘
```

## Technologies

* Python
* Flask
* MQTT
* Paho MQTT
* Flask-SQLAlchemy
* Flask-SocketIO
* JavaScript
* Leaflet
* SQLite / PostgreSQL

## How It Works

The ultrasonic sensor measures the distance between the sensor and the waste inside the bin, while the load cell measures the weight.

These measurements are combined to determine the current state of the bin.

The device communicates its status through MQTT. The backend processes the received data and makes it available through the web application.

Operators can monitor the bins remotely, manually control the lid and use the map and collection routes to organize waste collection.

## Web Application

The web application provides operators with an overview of the deployed bins and their current status.

It allows them to:

* Monitor bin status
* View bin locations on a map
* Open and close bins manually
* Identify bins requiring collection
* Manage collection routes
* Monitor anomalies

## Project Structure

```text
SmartBin/
├── ...
```

## Installation

Clone the repository:

```bash
git clone https://github.com/riccardovecchi0101/SmartBin.git
cd SmartBin
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables and MQTT broker settings before running the application.

## Project

SmartBin was developed as a university project focused on IoT, MQTT communication, web development and remote device management.

## Author

**Riccardo Vecchi**
**Giuseppe Bellissimo**


GitHub: https://github.com/riccardovecchi0101
