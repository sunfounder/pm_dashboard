# Dashboard Reference API

## Table of Contents
- [Dashboard Reference API](#dashboard-reference-api)
  - [Table of Contents](#table-of-contents)
  - [Server Configuration](#server-configuration)
  - [Endpoints](#endpoints)
    - [GET /get-device-info](#get-get-device-info)
    - [GET /test](#get-test)
    - [GET /test-mqtt](#get-test-mqtt)
    - [GET /get-history](#get-get-history)
    - [GET /get-time-range](#get-get-time-range)
    - [GET /get-config](#get-get-config)
    - [GET /get-log-list](#get-get-log-list)
    - [GET /get-log](#get-get-log)
    - [POST /set-config](#post-set-config)

## Server Configuration

- Port: `34001`
- Base URL: `/api/v1.0/`


## Endpoints

### GET /get-device-info

- Description: Get device information
- Response: 
  ```json
  {
    "status": true,
    "data": {
      "name": "Pironman 5",
      "id": "pironman5",
      "peripherals": [
        "ws2812",
        "oled"
      ]
    }
  }
  ```

### GET /test

- Description: Test if the server is running
- Response: 
  ```json
  {
    "status": true,
    "data": "OK"
  }
  ```

### GET /test-mqtt

- Description: Test if the MQTT configuration is correct
- Data: 
  - `host` - MQTT Broker Host
  - `port` - MQTT Broker Port
  - `username` - MQTT Broker Username
  - `password` - MQTT Broker Password
- Response: 
  - `{"status": true, "data": {"status": true, "error": null}}`
  - `{"status": true, "data": {"status": false, "error": "Timeout"}}`
  - `{"status": true, "data": {"status": false, "error": "Connection failed, Check hostname and port"}}`
  - `{"status": true, "data": {"status": false, "error": "Connection failed, Check username and password"}}`
  - `{"status": false, "error": "[ERROR] host not found"}`
  - `{"status": false, "error": "[ERROR] port not found"}`
  - `{"status": false, "error": "[ERROR] username not found"}`
  - `{"status": false, "error": "[ERROR] password not found"}`

### GET /get-history

- Description: Get history
- Data:
  - `n` - Number of records to return
- Response:
  - `{"status": true, "data": []}`

### GET /get-time-range

- Description: Get time range
- Data:
  - `start` - Start time
  - `end` - End time
  - `key`(optional) - Key to filter
- Response:
  - `{"status": true, "data": []}`

### GET /get-config

- Description: Get configuration
- Response:
  - `{"status": true, "data": {}`

### GET /get-log-list

- Description: Get log list
- Response:
  - `{"status": true, "data": []}`

### GET /get-log

- Description: Get log
- Data:
  - `filename` - Log file name
  - `lines`(optional) - Number of records to return
  - `filter`(optional) - Filter, divided by comma
  - `level`(optional) - Log level `['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']`
- Response:
  - `{"status": false, "error": "[ERROR] file not found"}`
  - `{"status": true, "data": []}`

### POST /set-config

- Description: Set configuration
- Data:
  - `data` - Configuration data
- Response:
  - `{"status": true, "data": data}`
