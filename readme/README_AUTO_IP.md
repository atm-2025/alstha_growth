# Windows Client Auto-IP Detection

## Overview
The Windows client now automatically detects and configures your current WiFi IP address, eliminating the need to manually enter it when your IP changes.

## Features

### 🔄 **Auto-IP Detection**
- **Automatic Detection**: Detects your current WiFi IP address on startup
- **Smart Fallback**: Falls back to manual input if detection fails
- **Multiple Methods**: Uses both socket connection and ipconfig command
- **Real-time Refresh**: Click the refresh button (🔄) to update IP anytime

### 📱 **User Interface Improvements**
- **Visual IP Display**: Shows detected IP address in green on startup
- **Split IP Input**: For common IP ranges (192.168.x.x), shows prefix + last octet
- **Full IP Input**: For other IP ranges, shows complete IP field
- **Status Updates**: Real-time feedback in the status area
- **Tooltips**: Helpful hints on hover

### 🛠 **Technical Details**
- **Detection Methods**:
  1. Socket connection to 8.8.8.8 (Google DNS)
  2. Windows `ipconfig` command parsing
  3. Regex pattern matching for IPv4 addresses
- **Supported IP Ranges**: 192.168.x.x, 10.x.x.x, 172.x.x.x
- **Error Handling**: Graceful fallback to manual input

## How It Works

### 1. **Startup Detection**
When you launch the Windows client:
- Automatically detects your WiFi IP address
- Displays it in the main window (green text)
- Pre-fills the converter tab with the detected IP
- Shows status message confirming detection

### 2. **IP Input Format**
- **Common IPs** (192.168.x.x): Shows as "192.168.1." + input field for last octet
- **Other IPs**: Shows complete IP address in one field
- **Manual Override**: You can still edit the IP manually if needed

### 3. **Refresh Functionality**
- Click the **🔄** button to refresh IP detection
- Updates both the input field and status
- Shows success/failure messages
- Works anytime during app usage

## Benefits

### ✅ **Convenience**
- No more manual IP entry when WiFi changes
- One-click refresh when IP changes
- Visual confirmation of current IP

### ✅ **Reliability**
- Multiple detection methods ensure high success rate
- Graceful fallback to manual input
- Clear error messages when detection fails

### ✅ **User Experience**
- Intuitive interface with visual feedback
- Tooltips for guidance
- Status updates for transparency

## Troubleshooting

### IP Detection Failed?
1. **Check Network**: Ensure you're connected to WiFi
2. **Firewall**: Check if Windows Firewall is blocking detection
3. **Manual Input**: You can always enter the IP manually
4. **Refresh**: Try clicking the refresh button

### Wrong IP Detected?
1. **Multiple Networks**: If you have multiple network adapters, it might detect the wrong one
2. **Manual Override**: Simply edit the IP field manually
3. **Refresh**: Try refreshing to re-detect

### Connection Issues?
1. **Verify IP**: Make sure the detected IP is correct
2. **Server Running**: Ensure Flask server is running on your computer
3. **Same Network**: Phone and computer must be on same WiFi
4. **Port 5000**: Check if port 5000 is accessible

## Technical Notes

- **Detection Priority**: Socket method first, then ipconfig parsing
- **IP Validation**: Supports standard IPv4 private ranges
- **Cross-platform**: Works on Windows (ipconfig) and other systems (socket method)
- **Performance**: Fast detection with minimal overhead
- **Memory**: Lightweight implementation with no persistent storage

## Future Enhancements

- **IP History**: Remember recently used IP addresses
- **Network Scanning**: Auto-detect Flask server on network
- **Connection Testing**: Built-in server connectivity test
- **Multiple Servers**: Support for multiple server configurations 

## Search Tab Icon Requirements

Place the following PNG icon files (40x40 or 48x48 recommended) in the `icons` directory:

- google.png
- youtube.png
- chatgpt.png
- bing.png
- gemini.png
- file_explorer.png
- windows_search.png

You can download free icons from:
- https://fonts.google.com/icons
- https://icon-sets.iconify.design/
- https://www.flaticon.com/
- https://icons8.com/icons

Name the files exactly as above for automatic detection. 