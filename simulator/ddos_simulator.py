"""
DDoS Simulator Project
---------------------
This project simulates a DDoS-like scenario for educational purposes only. It is strictly limited to localhost or private environments and does not allow targeting external IPs or domains.
"""

import asyncio
import logging
import time
from aiohttp import web, ClientSession
from collections import deque
from statistics import mean

# Configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8080
MAX_CLIENTS = 10
REQUESTS_PER_CLIENT = 20
RATE_LIMIT = 5  # requests per second per client
THRESHOLD_RPS = 30  # threshold for detection
METRICS_WINDOW = 10  # seconds

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Metrics
metrics = {
    'requests': deque(maxlen=METRICS_WINDOW * THRESHOLD_RPS),
    'latencies': deque(maxlen=METRICS_WINDOW * THRESHOLD_RPS),
    'dropped': 0
}

def get_metrics():
    now = time.time()
    recent = [t for t in metrics['requests'] if now - t < METRICS_WINDOW]
    rps = len(recent) / METRICS_WINDOW
    avg_latency = mean(metrics['latencies']) if metrics['latencies'] else 0
    dropped = metrics['dropped']
    return rps, avg_latency, dropped

# Server logic
async def handle(request):
    start = time.time()
    # Simple detection: drop if too many requests
    rps, _, _ = get_metrics()
    if rps > THRESHOLD_RPS:
        metrics['dropped'] += 1
        return web.Response(status=429, text='Too Many Requests')
    metrics['requests'].append(time.time())
    latency = time.time() - start
    metrics['latencies'].append(latency)
    return web.Response(text='OK')

async def metrics_handler(request):
    rps, avg_latency, dropped = get_metrics()
    return web.json_response({
        'requests_per_second': rps,
        'average_latency': avg_latency,
        'dropped_requests': dropped
    })

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/metrics', metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, SERVER_HOST, SERVER_PORT)
    await site.start()
    logging.info(f"Server running at http://{SERVER_HOST}:{SERVER_PORT}")
    while True:
        await asyncio.sleep(3600)

# Simulated client logic
async def client_task(client_id):
    async with ClientSession() as session:
        for i in range(REQUESTS_PER_CLIENT):
            try:
                start = time.time()
                async with session.get(f'http://{SERVER_HOST}:{SERVER_PORT}/') as resp:
                    await resp.text()
                    latency = time.time() - start
                    logging.info(f"Client {client_id} request {i+1}: {resp.status}, latency: {latency:.4f}s")
            except Exception as e:
                logging.warning(f"Client {client_id} request {i+1} failed: {e}")
            await asyncio.sleep(1 / RATE_LIMIT)

async def run_clients():
    await asyncio.gather(*(client_task(i) for i in range(MAX_CLIENTS)))

async def main():
    server = asyncio.create_task(start_server())
    await asyncio.sleep(1)  # Give server time to start
    await run_clients()
    await asyncio.sleep(2)
    rps, avg_latency, dropped = get_metrics()
    logging.info(f"Final metrics: RPS={rps:.2f}, Avg Latency={avg_latency:.4f}s, Dropped={dropped}")
    server.cancel()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Simulation stopped.")
