# Eletechsup 25IOB16_NPN Control via Modbus TCP

This project implements Python control for the **Eletechsup 25IOB16_NPN** digital I/O module through a **WAVESHARE RS485 TO POE ETH (B)** gateway configured in Modbus TCP to RTU mode.

## Hardware

- **Gateway**: WAVESHARE RS485 TO POE ETH (B)
  - Configured as Modbus TCP Server (port 502)
  - Converts Modbus TCP to Modbus RTU via RS485
- **I/O Module**: Eletechsup 25IOB16_NPN
  - 16 digital inputs + 16 digital outputs
  - RS485 communication (A/B)
  - Default Modbus address: 1

## Available Implementations

### 1. Pure Socket (`modbus_25iob16_socket.py`)
- ✅ No external dependencies
- ✅ Direct Modbus TCP frame implementation
- ✅ Lightweight and simple

### 2. Pymodbus (`modbus_25iob16_pymodbus.py`)
- ✅ Uses pymodbus 3.11.1+ library
- ✅ More features (status reading, better error handling)
- ✅ More robust for complex applications

## Installation

### Pure Socket (no dependencies)
```bash
# No installation required, just Python 3.6+
```

### Pymodbus
```bash
pip install pymodbus
```

## Basic Usage

### Pure Socket
```python
from modbus_25iob16_socket import Modbus25IOB16Socket

# Connect to gateway (WAVESHARE IP)
modbus = Modbus25IOB16Socket("10.0.2.218")

# Basic commands
modbus.liga_tudo()           # Turn ON all 16 outputs
modbus.desliga_tudo()        # Turn OFF all outputs
modbus.liga_canal(5)         # Turn ON channel 5 output (1-16)
modbus.desliga_canal(5)      # Turn OFF channel 5 output
modbus.toggle_canal(5)       # Toggle channel 5 state
```

### Pymodbus
```python
from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus

# Connect to gateway
modbus = Modbus25IOB16Pymodbus("10.0.2.218")
modbus.connect()

try:
    # Basic commands
    modbus.liga_tudo()
    modbus.liga_canal(3)
    
    # Status reading
    outputs = modbus.le_status_saidas()     # List with 16 output states
    inputs = modbus.le_status_entradas()    # List with 16 input states
    
    print(f"Output states: {outputs}")
    print(f"Input states: {inputs}")
    
finally:
    modbus.disconnect()
```

## Available Functions

| Function | Description | Modbus Register | Value |
|----------|-------------|----------------|--------|
| `liga_tudo()` | Turn ON all 16 outputs | 0 | 1792 (0x0700) |
| `desliga_tudo()` | Turn OFF all 16 outputs | 0 | 2048 (0x0800) |
| `liga_canal(n)` | Turn ON channel n output (1-16) | n-1 | 256 (0x0100) |
| `desliga_canal(n)` | Turn OFF channel n output (1-16) | n-1 | 512 (0x0200) |
| `toggle_canal(n)` | Toggle channel n state (1-16) | n-1 | 768 (0x0300) |
| `le_status_saidas()` | Read output states (pymodbus only) | 0-15 | - |
| `le_status_entradas()` | Read input states (pymodbus only) | 16-31 | - |

## Register Mapping

- **Registers 0-15**: Digital output control (channels 1-16)
- **Registers 16-31**: Digital input status (channels 1-16)

## Complete Example

Run the example file:
```bash
# Pure socket version
python exemplo_uso_simples.py

# Pymodbus version  
python exemplo_uso_simples.py pymodbus
```

## WAVESHARE Gateway Configuration

The gateway should be configured with:
- **Mode**: Modbus TCP Server
- **Port**: 502
- **RS485 Baudrate**: 9600 (25IOB16 default)
- **Data bits**: 8
- **Parity**: None
- **Stop bits**: 1

## Troubleshooting

### Connection Error
- Check if the gateway IP is correct
- Test connectivity: `ping GATEWAY_IP`
- Check if port 502 is open: `telnet GATEWAY_IP 502`

### Commands not working
- Confirm gateway configuration (TCP Server, port 502)
- Check RS485 wiring (A/B) between gateway and module
- Test with netcat: `printf "\x00\x01\x00\x00\x00\x06\x01\x06\x00\x00\x07\x00" | nc GATEWAY_IP 502`

### Pymodbus Version
- Use pymodbus 3.11.1 or higher
- In older versions, replace `device_id=` with `unit=` or `slave=`

## Modbus Protocol

This project uses **Function Code 06 (Write Single Register)** for output control and **Function Code 03 (Read Holding Registers)** for status reading.

### Example frame (Turn ON all outputs):
```
00 01 00 00 00 06 01 06 00 00 07 00
└─┬─┘ └─┬─┘ └─┬─┘ ┌┘ ┌┘ └─┬─┘ └─┬─┘
  │    │    │   │  │   │    │
  │    │    │   │  │   │    └── Value: 1792 (0x0700)
  │    │    │   │  │   └────── Register: 0
  │    │    │   │  └───────── Function Code: 06
  │    │    │   └─────────── Unit ID: 1
  │    │    └────────────── Length: 6
  │    └────────────────── Protocol ID: 0
  └─────────────────────── Transaction ID: 1
```

## Documentation

- [Portuguese README](README_PT.md) - Documentação em português

## License

Free to use project. Developed for industrial automation with WAVESHARE and Eletechsup hardware.