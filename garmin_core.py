import asyncio
from bleak import BleakClient

HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

class GarminCore:
    def __init__(self, watch_id, callback, status_callback):
        self.watch_id = watch_id
        self.callback = callback 
        self.status_callback = status_callback
        self.client = None
        self.is_connected = False
        self.should_run = True
        self.loop = None

    async def start(self):
        if not self.watch_id:
            self.status_callback("NO DEVICE SET", "red")
            return
        
        self.loop = asyncio.get_running_loop()

        while self.should_run: # Auto-reconnect loop
            try:
                self.status_callback("SEARCHING...", "#ffcc00")
                async with BleakClient(self.watch_id) as self.client:
                    self.is_connected = True
                    self.status_callback("● WATCH LINKED", "#00ff00")
                    
                    def handle_data(sender, data):
                        # data[1] is the heart rate byte in the standard HR profile
                        if self.callback:
                            self.callback(data[1])
                    
                    await self.client.start_notify(HR_UUID, handle_data)
                    while self.client.is_connected and self.should_run:
                        await asyncio.sleep(1)
            except Exception as e:
                if not self.should_run:
                    break
                self.is_connected = False
                self.status_callback(f"RETRYING...", "red")
                await asyncio.sleep(5) # Wait before trying again

    def stop(self):
        self.should_run = False
        if self.client and self.loop:
            # Safely schedule the disconnect in the running loop
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.client.disconnect())
            )