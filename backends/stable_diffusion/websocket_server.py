import asyncio
import websockets
import json

# A set to store all connected clients
connected_clients = set()

async def handler(websocket, path):
    """
    Handle incoming WebSocket connections.
    """
    # Add the new client to our set of connected clients
    connected_clients.add(websocket)
    print(f"New client connected. Total clients: {len(connected_clients)}")

    try:
        # Listen for messages from the client
        async for message in websocket:
            # When a message is received, broadcast it to all other clients
            # (or all clients including the sender, depending on the desired logic)
            print(f"Received message: {message}")

            # Create a list of tasks to send the message to all clients
            # This avoids waiting for one client to finish before sending to the next
            tasks = [client.send(message) for client in connected_clients]
            await asyncio.gather(*tasks)

    except websockets.exceptions.ConnectionClosed:
        print("A client disconnected.")
    finally:
        # Remove the client from our set when they disconnect
        connected_clients.remove(websocket)
        print(f"Client removed. Total clients: {len(connected_clients)}")

async def main():
    """
    Start the WebSocket server.
    """
    port = 8765
    print(f"Starting WebSocket server on ws://0.0.0.0:{port}...")
    async with websockets.serve(handler, "0.0.0.0", port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
