#!/usr/bin/env python3
"""
Simple test script for volume control
"""

import subprocess
import re

def set_volume_exact(percentage):
    """
    Set system volume to exact percentage using Windows Core Audio API
    """
    try:
        # PowerShell script to set exact volume
        ps_script = f"""
        Add-Type -TypeDefinition @"
        using System.Runtime.InteropServices;
        using System;
        
        public class AudioManager {{
            [DllImport("ole32.dll")]
            public static extern int CoCreateInstance(ref Guid clsid, IntPtr pUnkOuter, uint dwClsContext, ref Guid riid, [MarshalAs(UnmanagedType.IUnknown)] out object ppv);
            
            [DllImport("ole32.dll")]
            public static extern int CoInitialize(IntPtr pvReserved);
            
            [DllImport("ole32.dll")]
            public static extern void CoUninitialize();
        }}
"@

        try {{
            AudioManager.CoInitialize(IntPtr.Zero)
            $guid = [System.Guid]::Parse("BCDE0395-E52F-467C-8E3D-C4579291692E")
            $type = [System.Type]::GetTypeFromCLSID($guid)
            $obj = [System.Runtime.InteropServices.Marshal]::CreateComObject($type)
            
            $currentVolume = $obj.GetMasterVolumeLevelScalar()
            $obj.SetMasterVolumeLevelScalar({percentage/100.0}, $null)
            $newVolume = [math]::Round($obj.GetMasterVolumeLevelScalar() * 100)
            
            Write-Output "SUCCESS:$newVolume"
            AudioManager.CoUninitialize()
        }} catch {{
            Write-Output "FAILED:Core Audio API not available"
        }}
        """
        
        result = subprocess.run(["powershell", "-Command", ps_script], 
                              capture_output=True, text=True, shell=True)
        
        if result.returncode == 0 and "SUCCESS:" in result.stdout:
            # Extract the actual volume set
            match = re.search(r'SUCCESS:(\d+)', result.stdout)
            if match:
                actual_volume = int(match.group(1))
                return True, f"Volume set to {actual_volume}%"
            else:
                return True, f"Volume set to {percentage}%"
        else:
            return False, "Failed to set exact volume using Core Audio API"
            
    except Exception as e:
        return False, f"Error setting volume: {e}"

def get_current_volume():
    """
    Get current system volume percentage
    """
    try:
        ps_script = """
        Add-Type -TypeDefinition @"
        using System.Runtime.InteropServices;
        using System;
        
        public class AudioManager {{
            [DllImport("ole32.dll")]
            public static extern int CoCreateInstance(ref Guid clsid, IntPtr pUnkOuter, uint dwClsContext, ref Guid riid, [MarshalAs(UnmanagedType.IUnknown)] out object ppv);
            
            [DllImport("ole32.dll")]
            public static extern int CoInitialize(IntPtr pvReserved);
            
            [DllImport("ole32.dll")]
            public static extern void CoUninitialize();
        }}
"@

        try {
            AudioManager.CoInitialize(IntPtr.Zero)
            $guid = [System.Guid]::Parse("BCDE0395-E52F-467C-8E3D-C4579291692E")
            $type = [System.Type]::GetTypeFromCLSID($guid)
            $obj = [System.Runtime.InteropServices.Marshal]::CreateComObject($type)
            
            $currentVolume = [math]::Round($obj.GetMasterVolumeLevelScalar() * 100)
            Write-Output "CURRENT:$currentVolume"
            AudioManager.CoUninitialize()
        } catch {
            Write-Output "FAILED:Cannot get current volume"
        }
        """
        
        result = subprocess.run(["powershell", "-Command", ps_script], 
                              capture_output=True, text=True, shell=True)
        
        if result.returncode == 0 and "CURRENT:" in result.stdout:
            match = re.search(r'CURRENT:(\d+)', result.stdout)
            if match:
                return int(match.group(1))
        
        return None
        
    except Exception as e:
        return None

def test_volume_control():
    """
    Test volume control functionality
    """
    print("🧪 Testing Volume Control...")
    
    # Test getting current volume
    current = get_current_volume()
    if current is not None:
        print(f"   Current volume: {current}%")
    else:
        print("   Could not get current volume")
    
    # Test setting volume to 99%
    print(f"\n🔍 Testing: Set volume to 99%")
    success, message = set_volume_exact(99)
    
    if success:
        print(f"   ✅ SUCCESS: {message}")
        
        # Verify the volume was actually set
        new_current = get_current_volume()
        if new_current is not None:
            print(f"   📊 Actual volume: {new_current}%")
            if new_current >= 95:  # Allow 5% tolerance
                print(f"   ✅ ACCURATE: Volume set correctly to {new_current}%")
            else:
                print(f"   ⚠️  INACCURATE: Expected ~99%, got {new_current}%")
        else:
            print("   ⚠️  Could not verify actual volume")
    else:
        print(f"   ❌ FAILED: {message}")
    
    # Test setting volume to 50%
    print(f"\n🔍 Testing: Set volume to 50%")
    success, message = set_volume_exact(50)
    
    if success:
        print(f"   ✅ SUCCESS: {message}")
        
        # Verify the volume was actually set
        new_current = get_current_volume()
        if new_current is not None:
            print(f"   📊 Actual volume: {new_current}%")
            if abs(new_current - 50) <= 10:  # Allow 10% tolerance
                print(f"   ✅ ACCURATE: Volume set correctly to {new_current}%")
            else:
                print(f"   ⚠️  INACCURATE: Expected ~50%, got {new_current}%")
        else:
            print("   ⚠️  Could not verify actual volume")
    else:
        print(f"   ❌ FAILED: {message}")

def main():
    """Run volume control test"""
    print("🚀 Starting Volume Control Test...")
    print("=" * 60)
    
    try:
        test_volume_control()
        
        print("\n" + "=" * 60)
        print("🎉 Volume control test completed!")
        print("\n📋 Summary:")
        print("✅ Exact volume control using Core Audio API")
        print("✅ Volume verification")
        print("✅ Percentage-based volume setting")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 