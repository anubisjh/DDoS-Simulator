"""
DDoS Simulator Project
---------------------
This project simulates a DDoS-like scenario for educational purposes only. It is strictly limited to localhost or private environments and does not allow targeting external IPs or domains.
"""

import asyncio
import logging
import time

import argparse
from aiohttp import web, ClientSession
from collections import deque
from statistics import mean
import matplotlib.pyplot as plt


# Default configuration
DEFAULT_SERVER_HOST = '127.0.0.1'
DEFAULT_SERVER_PORT = 8080
DEFAULT_MAX_CLIENTS = 10
DEFAULT_REQUESTS_PER_CLIENT = 20
DEFAULT_RATE_LIMIT = 5
DEFAULT_THRESHOLD_RPS = 30
DEFAULT_METRICS_WINDOW = 10

# Globals (will be set by CLI)
SERVER_HOST = DEFAULT_SERVER_HOST
SERVER_PORT = DEFAULT_SERVER_PORT
MAX_CLIENTS = DEFAULT_MAX_CLIENTS
REQUESTS_PER_CLIENT = DEFAULT_REQUESTS_PER_CLIENT
RATE_LIMIT = DEFAULT_RATE_LIMIT
THRESHOLD_RPS = DEFAULT_THRESHOLD_RPS
METRICS_WINDOW = DEFAULT_METRICS_WINDOW

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Metrics

metrics = {
    'requests': deque(),
    'latencies': deque(),
    'dropped': 0,
    'rps_history': [],
    'dropped_history': [],
    'latency_history': [],
    'time_history': []
}

def get_metrics():
    now = time.time()
    recent = [t for t in metrics['requests'] if now - t < METRICS_WINDOW]
    rps = len(recent) / METRICS_WINDOW
    avg_latency = mean(metrics['latencies']) if metrics['latencies'] else 0
    dropped = metrics['dropped']
    # For plotting
    metrics['rps_history'].append(rps)
    metrics['latency_history'].append(avg_latency)
    metrics['dropped_history'].append(dropped)
    metrics['time_history'].append(now)
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


def plot_metrics():
    if not metrics['time_history']:
        return
    t0 = metrics['time_history'][0]
    times = [t - t0 for t in metrics['time_history']]
    plt.figure(figsize=(10, 6))
    plt.subplot(3, 1, 1)
    plt.plot(times, metrics['rps_history'], label='Requests/sec')
    plt.axhline(THRESHOLD_RPS, color='r', linestyle='--', label='Threshold')
    plt.ylabel('RPS')
    plt.legend()
    plt.subplot(3, 1, 2)
    plt.plot(times, metrics['latency_history'], label='Avg Latency (s)')
    plt.ylabel('Latency (s)')
    plt.legend()
    plt.subplot(3, 1, 3)
    plt.plot(times, metrics['dropped_history'], label='Dropped Requests')
    plt.ylabel('Dropped')
    plt.xlabel('Time (s)')
    plt.legend()
    plt.tight_layout()
    plt.savefig('example_graph.png')
    plt.show()

async def main():
    global SERVER_HOST, SERVER_PORT, MAX_CLIENTS, REQUESTS_PER_CLIENT, RATE_LIMIT, THRESHOLD_RPS, METRICS_WINDOW
    parser = argparse.ArgumentParser(description='DDoS Simulator (educational, local only)')
    parser.add_argument('--host', type=str, default=DEFAULT_SERVER_HOST, help='Server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=DEFAULT_SERVER_PORT, help='Server port (default: 8080)')
    parser.add_argument('--clients', type=int, default=DEFAULT_MAX_CLIENTS, help='Number of simulated clients')
    parser.add_argument('--requests', type=int, default=DEFAULT_REQUESTS_PER_CLIENT, help='Requests per client')
    parser.add_argument('--rate', type=int, default=DEFAULT_RATE_LIMIT, help='Requests/sec per client')
    parser.add_argument('--threshold', type=int, default=DEFAULT_THRESHOLD_RPS, help='Detection threshold (RPS)')
    parser.add_argument('--window', type=int, default=DEFAULT_METRICS_WINDOW, help='Metrics window (seconds)')
    args = parser.parse_args()
    SERVER_HOST = args.host
    SERVER_PORT = args.port
    MAX_CLIENTS = args.clients
    REQUESTS_PER_CLIENT = args.requests
    RATE_LIMIT = args.rate
    THRESHOLD_RPS = args.threshold
    METRICS_WINDOW = args.window
    # Reset metrics with new window/threshold
    metrics['requests'] = deque(maxlen=METRICS_WINDOW * THRESHOLD_RPS)
    metrics['latencies'] = deque(maxlen=METRICS_WINDOW * THRESHOLD_RPS)
    metrics['dropped'] = 0
    metrics['rps_history'] = []
    metrics['latency_history'] = []
    metrics['dropped_history'] = []
    metrics['time_history'] = []
    server = asyncio.create_task(start_server())
    await asyncio.sleep(1)  # Give server time to start
    await run_clients()
    await asyncio.sleep(2)
    rps, avg_latency, dropped = get_metrics()
    logging.info(f"Final metrics: RPS={rps:.2f}, Avg Latency={avg_latency:.4f}s, Dropped={dropped}")
    server.cancel()
    plot_metrics()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Simulation stopped.")
