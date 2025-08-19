# Controle do Módulo Eletechsup 25IOB16_NPN via Modbus TCP

Este projeto implementa controle Python para o módulo de I/O digital **Eletechsup 25IOB16_NPN** através de um gateway **WAVESHARE RS485 TO POE ETH (B)** configurado em modo Modbus TCP to RTU.

## Hardware

- **Gateway**: WAVESHARE RS485 TO POE ETH (B)
  - Configurado em modo Modbus TCP Server (porta 502)
  - Converte Modbus TCP para Modbus RTU via RS485
``` Network Settings > Work Mode > TCP Server
Device Port > 502
Serial Settings > Baud Rate 9600 8N1  
Multi-Host Settings > Protocol > Modbus TCP to RTU
```

- **Módulo I/O**: Eletechsup 25IOB16_NPN
  - 16 entradas digitais + 16 saídas digitais
  - Comunicação RS485 (A/B)
  - Endereço Modbus: 1 (padrão)

## Implementações Disponíveis

### 1. Socket Puro (`modbus_25iob16_socket.py`)
- ✅ Sem dependências externas
- ✅ Implementação direta dos frames Modbus TCP
- ✅ Mais leve e simples

### 2. Pymodbus (`modbus_25iob16_pymodbus.py`)
- ✅ Usa biblioteca pymodbus 3.11.1+
- ✅ Mais recursos (leitura de status, melhor tratamento de erros)
- ✅ Mais robusta para aplicações complexas

## Instalação

### Socket Puro (sem dependências)
```bash
# Nenhuma instalação necessária, apenas Python 3.6+
```

### Pymodbus
```bash
pip install pymodbus
```

## Uso Básico

### Socket Puro
```python
from modbus_25iob16_socket import Modbus25IOB16Socket

# Conecta ao gateway (IP do WAVESHARE)
modbus = Modbus25IOB16Socket("10.0.2.218")

# Comandos básicos
modbus.liga_tudo()           # Liga todas as 16 saídas
modbus.desliga_tudo()        # Desliga todas as saídas
modbus.liga_canal(5)         # Liga saída do canal 5 (1-16)
modbus.desliga_canal(5)      # Desliga saída do canal 5
modbus.toggle_canal(5)       # Alterna estado do canal 5
```

### Pymodbus
```python
from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus

# Conecta ao gateway
modbus = Modbus25IOB16Pymodbus("10.0.2.218")
modbus.connect()

try:
    # Comandos básicos
    modbus.liga_tudo()
    modbus.liga_canal(3)
    
    # Leitura de status
    saidas = modbus.le_status_saidas()      # Lista com status das 16 saídas
    entradas = modbus.le_status_entradas()  # Lista com status das 16 entradas
    
    print(f"Status das saídas: {saidas}")
    print(f"Status das entradas: {entradas}")
    
finally:
    modbus.disconnect()
```

## Funções Disponíveis

| Função | Descrição | Registro Modbus | Valor |
|--------|-----------|----------------|--------|
| `liga_tudo()` | Liga todas as 16 saídas | 0 | 1792 (0x0700) |
| `desliga_tudo()` | Desliga todas as 16 saídas | 0 | 2048 (0x0800) |
| `liga_canal(n)` | Liga saída do canal n (1-16) | n-1 | 256 (0x0100) |
| `desliga_canal(n)` | Desliga saída do canal n (1-16) | n-1 | 512 (0x0200) |
| `toggle_canal(n)` | Alterna estado do canal n (1-16) | n-1 | 768 (0x0300) |
| `le_status_saidas()` | Lê status das saídas (só pymodbus) | 0-15 | - |
| `le_status_entradas()` | Lê status das entradas (só pymodbus) | 16-31 | - |

## Mapeamento de Registradores

- **Registros 0-15**: Controle das saídas digitais (canais 1-16)
- **Registros 16-31**: Status das entradas digitais (canais 1-16)

## Exemplo Completo

Execute o arquivo de exemplo:
```bash
# Versão socket puro
python exemplo_uso_simples.py

# Versão pymodbus  
python exemplo_uso_simples.py pymodbus
```

## Configuração do Gateway WAVESHARE

O gateway deve estar configurado com:
- **Modo**: Modbus TCP Server
- **Porta**: 502
- **Baudrate RS485**: 9600 (padrão do 25IOB16)
- **Data bits**: 8
- **Parity**: None
- **Stop bits**: 1

## Troubleshooting

### Erro de Conexão
- Verifique se o IP do gateway está correto
- Teste conectividade: `ping IP_DO_GATEWAY`
- Verifique se a porta 502 está aberta: `telnet IP_DO_GATEWAY 502`

### Comandos não funcionam
- Confirme a configuração do gateway (TCP Server, porta 502)
- Verifique a ligação RS485 (A/B) entre gateway e módulo
- Teste com netcat: `printf "\x00\x01\x00\x00\x00\x06\x01\x06\x00\x00\x07\x00" | nc IP_GATEWAY 502`

### Versão Pymodbus
- Use pymodbus 3.11.1 ou superior
- Em versões antigas, substitua `device_id=` por `unit=` ou `slave=`

## Protocolo Modbus

Este projeto usa **Function Code 06 (Write Single Register)** para controle das saídas e **Function Code 03 (Read Holding Registers)** para leitura de status.

### Frame de exemplo (Liga todas as saídas):
```
00 01 00 00 00 06 01 06 00 00 07 00
└─┬─┘ └─┬─┘ └─┬─┘ ┌┘ ┌┘ └─┬─┘ └─┬─┘
  │    │    │   │  │   │    │
  │    │    │   │  │   │    └── Valor: 1792 (0x0700)
  │    │    │   │  │   └────── Registro: 0
  │    │    │   │  └───────── Function Code: 06
  │    │    │   └─────────── Unit ID: 1
  │    │    └────────────── Length: 6
  │    └────────────────── Protocol ID: 0
  └─────────────────────── Transaction ID: 1
```

## Licença

Projeto de uso livre. Desenvolvido para automação industrial com hardware WAVESHARE e Eletechsup.
