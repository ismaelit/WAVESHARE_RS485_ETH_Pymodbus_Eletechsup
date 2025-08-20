# 📋 INSTRUÇÕES DE INSTALAÇÃO - GATEWAY WAVESHARE RS485-TO-ETH-B

## 🎯 Objetivo
Configurar o gateway Waveshare RS485-TO-ETH-B para monitorar automaticamente os módulos 25IOB16 via Modbus RTU e publicar dados via MQTT em formato JSON.

## 📦 Arquivos de Configuração Gerados
- `gateway_config_modulo1.json` - Configuração específica para Módulo 1 (16 portas)
- `gateway_config_modulo2.json` - Configuração específica para Módulo 2 (4 portas)
- `gateway_config_completo.json` - Configuração consolidada para ambos os módulos

## 🔧 Configurações do Sistema Atual
- **Gateway IP:** 10.0.2.217
- **Porta Modbus TCP:** 502
- **Módulo 1:** Unit ID 1, 16 portas (entradas + saídas)
- **Módulo 2:** Unit ID 2, 4 portas (apenas saídas)

## 📡 Configurações MQTT
- **Servidor:** 172.9.2.11:1883
- **Usuário:** choppers
- **Senha:** ismaisma
- **Tópicos:**
  - `modbus/modulo1/status` - Status do módulo 1
  - `modbus/modulo2/status` - Status do módulo 2
  - `modbus/modulo1/control` - Controle do módulo 1
  - `modbus/modulo2/control` - Controle do módulo 2

## 🚀 Passos de Instalação

### 1. Preparação do Hardware
```
[Servidor MQTT] ←→ [Gateway Waveshare RS485-TO-ETH-B] ←→ [Módulos 25IOB16 via RS485]
```

### 2. Configuração do Gateway via Vircom
1. **Conectar ao gateway** via software Vircom
2. **Editar dispositivo** → Firmware and Configuration
3. **Web Directory Download** → Selecionar diretório vazio
4. **Clear All** → Limpar configurações anteriores

### 3. Configuração MQTT
1. **MQTT Configuration** → Configurar:
   - Server IP: 172.9.2.11
   - Server Port: 1883
   - Username: choppers
   - Password: ismaisma
   - Client ID: modulo1_gateway (para módulo 1)
   - Publish Topic: modbus/modulo1/status
   - Subscribe Topic: modbus/modulo1/control

### 4. Configuração JSON para Módulo 1
1. **JSON Configuration** → Add/View
2. **Configurar cada nó JSON:**

#### Entradas Digitais (Registro 192)
- **JSON Key:** entradas_digitais
- **Data Source:** Modbus RTU
- **Slave Address:** 1
- **Function Code:** 03
- **Register Address:** 192
- **Data Length:** 2 bytes
- **Data Format:** Unsigned Int
- **Decimal Places:** 0
- **Serial Port Polling Time:** 100ms

#### Saídas Digitais (Registros 0-15)
- **JSON Key:** saida_1 até saida_16
- **Data Source:** Modbus RTU
- **Slave Address:** 1
- **Function Code:** 03
- **Register Address:** 0, 1, 2... 15
- **Data Length:** 2 bytes
- **Data Format:** Unsigned Int
- **Decimal Places:** 0
- **Serial Port Polling Time:** 100ms

### 5. Configuração JSON para Módulo 2
1. **Repetir processo** para módulo 2
2. **Slave Address:** 2
3. **Apenas 4 saídas** (registros 0-3)
4. **Polling mais lento:** 500ms

### 6. Salvar e Baixar
1. **Save JSON Settings** para cada módulo
2. **Save MQTT Settings**
3. **Download** → Aplicar configurações ao gateway

## 🔍 Verificação da Instalação

### 1. Teste de Conexão MQTT
```bash
# Verificar se o gateway está conectado
mosquitto_sub -h 172.9.2.11 -t "modbus/+/status" -v
```

### 2. Monitoramento dos Dados
```bash
# Monitorar dados do módulo 1
mosquitto_sub -h 172.9.2.11 -t "modbus/modulo1/status" -v

# Monitorar dados do módulo 2
mosquitto_sub -h 172.9.2.11 -t "modbus/modulo2/status" -v
```

### 3. Exemplo de Dados Recebidos
```json
{
  "device_id": "modulo1_25iob16",
  "timestamp": "2024-12-19 15:30:45",
  "entradas_digitais": 12345,
  "saida_1": 256,
  "saida_2": 0,
  "saida_3": 256,
  "saida_4": 0,
  "saida_5": 256,
  "saida_6": 0,
  "saida_7": 256,
  "saida_8": 0,
  "saida_9": 256,
  "saida_10": 0,
  "saida_11": 256,
  "saida_12": 0,
  "saida_13": 256,
  "saida_14": 0,
  "saida_15": 256,
  "saida_16": 0
}
```

## ⚡ Otimizações Implementadas

### 1. Frequências de Leitura Separadas
- **Entradas:** 100ms (alta prioridade)
- **Saídas:** 500ms (menor prioridade)
- **Módulo 2:** 500ms (apenas saídas)

### 2. Estrutura JSON Otimizada
- **Timestamp automático** via NTP
- **Device ID único** para cada módulo
- **Dados agrupados** em um único pacote MQTT

### 3. Redução de Tráfego
- **Antes:** 1 comando Modbus por porta
- **Depois:** 1 pacote JSON com todas as portas
- **Redução estimada:** 80-90% do tráfego

## 🛠️ Solução de Problemas

### 1. Gateway não conecta ao MQTT
- Verificar IP e porta do servidor MQTT
- Confirmar credenciais de usuário
- Verificar firewall e conectividade de rede

### 2. Dados não são recebidos
- Verificar tópicos MQTT configurados
- Confirmar endereços Modbus dos módulos
- Verificar conexão RS485 (A/B)

### 3. Dados incorretos
- Verificar registros Modbus configurados
- Confirmar function codes (03 para Holding Registers)
- Verificar formato de dados (unsigned int, 2 bytes)

## 📊 Benefícios da Implementação

1. **Monitoramento automático** 24/7
2. **Redução significativa** do tráfego de rede
3. **Dados estruturados** em formato JSON
4. **Integração fácil** com sistemas SCADA/IIoT
5. **Manutenção reduzida** (sem necessidade de polling manual)
6. **Escalabilidade** para adicionar mais módulos

## 🔗 Próximos Passos

1. **Implementar servidor MQTT** (Mosquitto, HiveMQ, etc.)
2. **Desenvolver cliente MQTT** para processar dados
3. **Integrar com banco de dados** para histórico
4. **Implementar dashboard** para visualização
5. **Configurar alertas** baseados em mudanças de estado

---

**📞 Suporte:** Em caso de dúvidas, consulte o manual do gateway Waveshare ou entre em contato com o suporte técnico.
