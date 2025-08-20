https://asutp.org/news/eletechsup_23ioa08_23iob16_23ioc24_23iod32_23ioe48_manual_modbus_command/2023-07-10-220

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
- ✅ Retry automático com reconexão (3 tentativas) para estabilidade de rede

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
    saidas_brutas = modbus.le_status_saidas()         # Valores brutos dos registradores (0-15)
    saidas_digitais = modbus.le_status_saidas_digitais()  # Estados digitais [0,1] x16
    entradas = modbus.le_status_entradas()            # Estados das entradas [0,1] x16
    
    print(f"Status das saídas (digital): {saidas_digitais}")
    print(f"Status das entradas: {entradas}")
    print(f"Saídas ativas: {[i+1 for i, s in enumerate(saidas_digitais) if s]}")
    print(f"Entradas ativas: {[i+1 for i, s in enumerate(entradas) if s]}")
    
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
| `le_status_saidas()` | Lê valores brutos dos registradores (pymodbus) | 0-15 | Valores brutos |
| `le_status_saidas_digitais()` | Lê estados das saídas como lista 0/1 (pymodbus) | 0-15 | [0,1] x16 |
| `le_status_entradas()` | Lê estados das entradas como lista 0/1 (pymodbus) | 192 | [0,1] x16 |

## Mapeamento de Registradores

### Saídas Digitais (Operações de Escrita)
- **Registros 0-15**: Controle individual das saídas digitais (canais 1-16)
  - Registro 0 = Saída Canal 1
  - Registro 1 = Saída Canal 2
  - ...
  - Registro 15 = Saída Canal 16
  - Valores: 256 (LIGA), 512 (DESLIGA), 768 (ALTERNA), 1792 (LIGA TUDO), 2048 (DESLIGA TUDO)

### Entradas Digitais (Operações de Leitura)
- **Registro 192**: Todas as 16 entradas digitais
  - Bit 0 = Entrada Canal 1
  - Bit 1 = Entrada Canal 2
  - ...
  - Bit 15 = Entrada Canal 16
  - Cada bit: 1 = Ativo, 0 = Inativo

### Status das Saídas Digitais (Operações de Leitura)
- **Registros 0-15**: Leitura do status das saídas digitais
  - Mesmos registros usados para controle podem ser lidos para status
  - Valores não-zero indicam saída LIGADA
  - Valores zero indicam saída DESLIGADA

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

## Recursos de Confiabilidade (Versão Pymodbus)

### Retry Automático com Reconexão
A implementação pymodbus inclui funcionalidade de retry automático para melhor estabilidade de rede:

- **3 tentativas automáticas** para cada operação (leitura/escrita)
- **Reconexão automática** se a conexão for perdida
- **Delay de 1 segundo** entre tentativas de retry
- **Tratamento gracioso de erros** com mensagens detalhadas

Exemplo do comportamento de retry:
```python
# Se a conexão de rede falhar durante operação:
# Tentativa 1: Tenta operação -> Conexão perdida
# Tentativa 2: Reconecta + Tenta operação -> Erro Modbus
# Tentativa 3: Reconecta + Tenta operação -> Sucesso

modbus = Modbus25IOB16Pymodbus("10.0.2.218")
modbus.connect()

# Isso automaticamente tentará novamente se ocorrerem problemas de conexão
result = modbus.liga_canal(5)  # Operação robusta com retry
inputs = modbus.le_status_entradas()  # Leitura robusta com retry
```

### Recuperação de Erros
- **Erros de conexão**: Reconexão automática
- **Erros do protocolo Modbus**: Retry com conexão renovada
- **Timeouts de rede**: Timeout configurável (padrão: 5 segundos)

## Scripts de Teste

### Teste Completo de I/O
```bash
python3 teste_completo_io.py    # Menu interativo para teste abrangente
```

### Teste Rápido
```bash
python3 teste_final.py          # Teste rápido não-interativo
```

### Investigação do Mapeamento de Entradas
```bash
python3 investigar_entradas.py  # Para debug de problemas de mapeamento de entradas
```

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

Este projeto usa **Function Code 06 (Write Single Register)** para controle das saídas e **Function Code 03 (Read Holding Registers)** para leitura de status (tanto saídas quanto entradas).

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
