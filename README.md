# Eletechsup 25IOB16_NPN Control via Modbus TCP

This project implements Python control for the **Eletechsup 25IOB16_NPN** digital I/O module through a **WAVESHARE RS485 TO POE ETH (B)** gateway configured in Modbus TCP to RTU mode.

## Hardware

- **Gateway**: WAVESHARE RS485 TO POE ETH (B)
  - Configured as Modbus TCP Server (port 502)
  - Converts Modbus TCP to Modbus RTU via RS485
``` Network Settings > Work Mode > TCP Server
Device Port > 502
Serial Settings > Baud Rate 9600 8N1 
Multi-Host Settings > Protocol > Modbus TCP to RTU
```


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
- ✅ Automatic retry with reconnection (3 attempts) for network stability

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
    outputs_raw = modbus.le_status_saidas()         # Raw register values (0-15)
    outputs_digital = modbus.le_status_saidas_digitais()  # Digital states [0,1] x16
    inputs = modbus.le_status_entradas()            # Digital input states [0,1] x16
    
    print(f"Output states (digital): {outputs_digital}")
    print(f"Input states: {inputs}")
    print(f"Active outputs: {[i+1 for i, s in enumerate(outputs_digital) if s]}")
    print(f"Active inputs: {[i+1 for i, s in enumerate(inputs) if s]}")
    
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
| `le_status_saidas()` | Read raw output register values (pymodbus) | 0-15 | Raw values |
| `le_status_saidas_digitais()` | Read output states as 0/1 list (pymodbus) | 0-15 | [0,1] x16 |
| `le_status_entradas()` | Read input states as 0/1 list (pymodbus) | 192 | [0,1] x16 |

## Register Mapping

### Digital Outputs (Write Operations)
- **Registers 0-15**: Individual digital output control (channels 1-16)
  - Register 0 = Output Channel 1
  - Register 1 = Output Channel 2
  - ...
  - Register 15 = Output Channel 16
  - Values: 256 (ON), 512 (OFF), 768 (TOGGLE), 1792 (ALL ON), 2048 (ALL OFF)

### Digital Inputs (Read Operations)
- **Register 192**: All 16 digital input states
  - Bit 0 = Input Channel 1
  - Bit 1 = Input Channel 2
  - ...
  - Bit 15 = Input Channel 16
  - Each bit: 1 = Active, 0 = Inactive

### Digital Output Status (Read Operations)
- **Registers 0-15**: Digital output status reading
  - Same registers used for control can be read for status
  - Non-zero values indicate output is ON
  - Zero values indicate output is OFF

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

## Reliability Features (Pymodbus Version)

### Automatic Retry with Reconnection
The pymodbus implementation includes automatic retry functionality for improved network stability:

- **3 automatic attempts** for each operation (read/write)
- **Automatic reconnection** if connection is lost
- **1-second delay** between retry attempts
- **Graceful error handling** with detailed error messages

Example of retry behavior:
```python
# If network connection fails during operation:
# Attempt 1: Try operation -> Connection lost
# Attempt 2: Reconnect + Try operation -> Modbus error
# Attempt 3: Reconnect + Try operation -> Success

modbus = Modbus25IOB16Pymodbus("10.0.2.218")
modbus.connect()

# This will automatically retry if connection issues occur
result = modbus.liga_canal(5)  # Robust operation with retry
inputs = modbus.le_status_entradas()  # Robust reading with retry
```

### Error Recovery
- **Connection errors**: Automatic reconnection
- **Modbus protocol errors**: Retry with fresh connection
- **Network timeouts**: Configurable timeout (default: 5 seconds)

## Testing Scripts

### Complete I/O Test
```bash
python3 teste_completo_io.py    # Interactive menu for comprehensive testing
```

### Quick Test
```bash
python3 teste_final.py          # Non-interactive quick test
```

### Input Mapping Investigation
```bash
python3 investigar_entradas.py  # For debugging input mapping issues
```

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

This project uses **Function Code 06 (Write Single Register)** for output control and **Function Code 03 (Read Holding Registers)** for status reading (both outputs and inputs).

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
