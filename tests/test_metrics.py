import pytest
from simulator import ddos_simulator

def test_get_metrics_initial():
    # Reset metrics
    ddos_simulator.metrics['requests'].clear()
    ddos_simulator.metrics['latencies'].clear()
    ddos_simulator.metrics['dropped'] = 0
    rps, avg_latency, dropped = ddos_simulator.get_metrics()
    assert rps == 0
    assert avg_latency == 0
    assert dropped == 0
