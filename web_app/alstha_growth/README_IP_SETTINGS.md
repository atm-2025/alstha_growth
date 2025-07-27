# Android App IP Address Settings

## Overview
The Android app now supports manual IP address configuration, allowing you to easily change the server IP address when your WiFi IP changes.

## Features
- **Manual IP Input**: Enter any IP address for the Flask server
- **IP Validation**: Validates IP address format before saving
- **Connection Testing**: Test if the server is reachable before saving
- **Persistent Storage**: IP address is saved and remembered between app sessions
- **Easy Access**: Settings button on the main screen

## How to Use

### 1. Access Settings
- Open the Android app
- Tap the **"Settings"** button on the main screen

### 2. Enter IP Address
- In the settings screen, enter your computer's IP address
- Format: `192.168.1.xxx` (replace xxx with your actual IP)
- Example: `192.168.1.5` or `172.30.208.1`

### 3. Test Connection (Optional)
- Tap **"Test Connection"** to verify the server is reachable
- You'll see a success or failure message

### 4. Save Settings
- Tap **"Save IP"** to store the IP address
- The app will now use this IP for all uploads

## Finding Your Computer's IP Address

### On Windows:
1. Open Command Prompt
2. Type: `ipconfig`
3. Look for "IPv4 Address" under your WiFi adapter
4. Use that IP address (e.g., `192.168.1.5`)

### On Mac/Linux:
1. Open Terminal
2. Type: `ifconfig` (Mac/Linux) or `ip addr` (Linux)
3. Look for your WiFi interface and find the IP address

## Troubleshooting

### Connection Failed?
1. **Check IP Address**: Make sure you entered the correct IP
2. **Same Network**: Ensure phone and computer are on the same WiFi
3. **Server Running**: Make sure the Flask server is running on your computer
4. **Firewall**: Check if Windows Firewall is blocking the connection
5. **Port 5000**: Ensure port 5000 is not blocked

### Server Not Found?
- Try using `localhost` or `127.0.0.1` if testing on the same device
- Check if the Flask server is running with: `python app.py`

## Default Settings
- **Default IP**: `192.168.1.9`
- **Port**: `5000` (hardcoded)
- **Protocol**: `HTTP`

## Notes
- The IP address is stored locally on your device
- You only need to change it when your computer's IP address changes
- The app will remember your settings even after closing and reopening 