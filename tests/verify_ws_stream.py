import asyncio
import websockets
import json

async def monitor_events():
    uri = "ws://localhost:9090/ws/events"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected. Waiting for events...")
            while True:
                try:
                    message = await websocket.recv()
                    print(f"Raw message: {message[:100]}")
                    data = json.loads(message)
                    
                    # Defensively handle strings
                    for _ in range(3):
                        if isinstance(data, str):
                            try: data = json.loads(data)
                            except: break
                        else: break
                    
                    if not isinstance(data, dict):
                        print(f"Expected dict, got {type(data)}")
                        continue

                    event_type = data.get("type", "UNKNOWN")
                    # Use .get chain for safety
                    inner_data = data.get("data", {})
                    if isinstance(inner_data, str):
                        try: inner_data = json.loads(inner_data)
                        except: pass
                    
                    eid = "N/A"
                    if isinstance(inner_data, dict):
                        eid = inner_data.get("execution_id", "N/A")
                    
                    print(f"EVENT: {event_type} | ID: {eid}")

                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
                except Exception as e:
                    print(f"Inner Error: {str(e)}")
    except Exception as e:
        print(f"Outer Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(monitor_events())
