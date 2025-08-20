#!/usr/bin/env python3
"""
Controle do módulo Eletechsup 25IOB16 via Modbus TCP usando pymodbus
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import time
import logging

class Modbus25IOB16Pymodbus:
    # Client compartilhado entre todas as instâncias (best practice pymodbus)
    _shared_client = None
    _shared_client_config = None
    
    # Configurações de retry e timing otimizadas para Eletechsup 25IOB16
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 0.5
    DEFAULT_BACKOFF_MULTIPLIER = 2.0
    MAX_RETRY_DELAY = 5.0
    
    def __init__(self, host, port=502, unit_id=1, timeout=12):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        
        # Configurações de retry específicas para este dispositivo
        self.retry_count = self.DEFAULT_RETRY_COUNT
        self.retry_delay = self.DEFAULT_RETRY_DELAY
        self.backoff_multiplier = self.DEFAULT_BACKOFF_MULTIPLIER
        
        # Logs para diagnóstico
        self.logger = logging.getLogger(f'Modbus25IOB16_{unit_id}')
        self.logger.setLevel(logging.WARNING)  # Apenas warnings e erros por padrão
        
        # Estatísticas de performance
        self.connection_attempts = 0
        self.successful_reads = 0
        self.failed_reads = 0
        self.last_successful_read = None
        
        # Usa client compartilhado se configuração for a mesma
        if (Modbus25IOB16Pymodbus._shared_client_config == (host, port) and 
            Modbus25IOB16Pymodbus._shared_client is not None):
            self.client = Modbus25IOB16Pymodbus._shared_client
        else:
            # Cria novo client compartilhado
            self.client = None
            Modbus25IOB16Pymodbus._shared_client = None
            Modbus25IOB16Pymodbus._shared_client_config = (host, port)
    
    def connect(self):
        """Estabelece conexão compartilhada com o gateway com retry automático"""
        self.connection_attempts += 1
        
        for attempt in range(self.retry_count + 1):
            try:
                # Se já existe um client compartilhado conectado, usa ele
                if (Modbus25IOB16Pymodbus._shared_client is not None and 
                    Modbus25IOB16Pymodbus._shared_client.connected):
                    self.client = Modbus25IOB16Pymodbus._shared_client
                    return True
                    
                # Cria nova conexão compartilhada
                if Modbus25IOB16Pymodbus._shared_client:
                    Modbus25IOB16Pymodbus._shared_client.close()
                    
                # Configurações otimizadas para Eletechsup 25IOB16
                Modbus25IOB16Pymodbus._shared_client = ModbusTcpClient(
                    self.host, 
                    port=self.port, 
                    timeout=self.timeout
                )
                
                if Modbus25IOB16Pymodbus._shared_client.connect():
                    self.client = Modbus25IOB16Pymodbus._shared_client
                    self.logger.info(f"Conexão estabelecida com {self.host}:{self.port} (tentativa {attempt + 1})")
                    return True
                else:
                    if attempt < self.retry_count:
                        delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                        self.logger.warning(f"Falha na conexão unit_id {self.unit_id}, tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        self.logger.error(f"Falha definitiva na conexão unit_id {self.unit_id} após {self.retry_count + 1} tentativas")
                        return False
                    
            except Exception as e:
                if attempt < self.retry_count:
                    delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                    self.logger.warning(f"Erro na conexão unit_id {self.unit_id}: {e}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"Erro definitivo na conexão unit_id {self.unit_id}: {e}")
                    print(f"Erro na conexão unit_id {self.unit_id}: {e}")
                    return False
        
        return False
    
    def disconnect(self):
        """Fecha conexão"""
        if self.client:
            self.client.close()
    
    def _write_register(self, register, value):
        """Escreve valor em registrador usando Function Code 06 com retry automático"""
        for attempt in range(self.retry_count + 1):
            if not self.client or not self.client.connected:
                if not self.connect():
                    continue
            
            try:
                start_time = time.time()
                result = self.client.write_register(register, value, device_id=self.unit_id)
                elapsed_time = time.time() - start_time
                
                if result.isError():
                    if attempt < self.retry_count:
                        delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                        self.logger.warning(f"Erro na escrita unit_id {self.unit_id} reg {register}: {result}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Erro definitivo na escrita unit_id {self.unit_id} reg {register}: {result}")
                        print(f"Erro na escrita para unit_id {self.unit_id}: {result}")
                        self.failed_reads += 1
                        return False
                
                self.successful_reads += 1
                self.last_successful_read = time.time()
                self.logger.debug(f"Escrita bem-sucedida unit_id {self.unit_id} reg {register} = {value} ({elapsed_time:.3f}s)")
                return True
                
            except Exception as e:
                if attempt < self.retry_count:
                    delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                    self.logger.warning(f"Erro na comunicação unit_id {self.unit_id}: {e}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"Erro definitivo na comunicação unit_id {self.unit_id}: {e}")
                    print(f"Erro na comunicação unit_id {self.unit_id}: {e}")
                    self.failed_reads += 1
                    return False
        
        return False
    
    def liga_tudo(self):
        """Liga todas as saídas (reg 0 = 1792 = 0x0700)"""
        return self._write_register(0, 1792)
    
    def desliga_tudo(self):
        """Desliga todas as saídas (reg 0 = 2048 = 0x0800)"""
        return self._write_register(0, 2048)
    
    def toggle_canal(self, canal):
        """Toggle do canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1  # Canal 1 = reg 0, canal 2 = reg 1, etc.
        return self._write_register(register, 768)  # 0x0300
    
    def liga_canal(self, canal):
        """Liga canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1
        return self._write_register(register, 256)  # 0x0100
    
    def desliga_canal(self, canal):
        """Desliga canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1
        return self._write_register(register, 512)  # 0x0200
    
    def le_status_entradas(self):
        """Lê status das entradas digitais (registrador 192) com retry automático"""
        for attempt in range(self.retry_count + 1):
            if not self.client or not self.client.connected:
                if not self.connect():
                    continue
            
            try:
                start_time = time.time()
                result_192 = self.client.read_holding_registers(192, count=1, device_id=self.unit_id)
                elapsed_time = time.time() - start_time
                
                if not result_192.isError():
                    valor_192 = result_192.registers[0]
                    
                    # Constrói a lista de 16 entradas
                    entradas = [0] * 16
                    
                    # Processa todos os 16 bits do registrador 192
                    for bit in range(16):
                        if valor_192 & (1 << bit):
                            entradas[bit] = 1  # bit N = entrada N+1
                    
                    self.successful_reads += 1
                    self.last_successful_read = time.time()
                    self.logger.debug(f"Leitura entradas unit_id {self.unit_id} bem-sucedida ({elapsed_time:.3f}s)")
                    return entradas
                else:
                    if attempt < self.retry_count:
                        delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                        self.logger.warning(f"Erro ao ler entradas unit_id {self.unit_id}: {result_192}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Erro definitivo ao ler entradas unit_id {self.unit_id}: {result_192}")
                        print(f"Erro ao ler entradas unit_id {self.unit_id}: {result_192}")
                        self.failed_reads += 1
                        return None
                        
            except Exception as e:
                if attempt < self.retry_count:
                    delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                    self.logger.warning(f"Erro na leitura das entradas unit_id {self.unit_id}: {e}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"Erro definitivo na leitura das entradas unit_id {self.unit_id}: {e}")
                    print(f"Erro na leitura das entradas unit_id {self.unit_id}: {e}")
                    self.failed_reads += 1
                    return None
        
        return None
    
    def le_status_saidas(self):
        """Lê status das saídas digitais (registradores 0-15) - retorna registradores brutos"""
        if not self.client or not self.client.connected:
            if not self.connect():
                return None
        
        try:
            # Lê 16 registradores a partir do 0 (saídas)
            result = self.client.read_holding_registers(0, count=16, device_id=self.unit_id)
            if not result.isError():
                return result.registers
            else:
                print(f"Erro ao ler saídas: {result}")
                return None
        except Exception as e:
            print(f"Erro na leitura: {e}")
            return None
    
    def le_status_saida_especifica(self, canal):
        """Lê status de uma saída específica (1-16) - lê apenas 1 registrador"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
            
        register = canal - 1  # Canal 1 = reg 0, canal 2 = reg 1, etc.
        
        for attempt in range(self.retry_count + 1):
            if not self.client or not self.client.connected:
                if not self.connect():
                    continue
            
            try:
                start_time = time.time()
                # Lê apenas 1 registrador específico
                result = self.client.read_holding_registers(register, count=1, device_id=self.unit_id)
                elapsed_time = time.time() - start_time
                
                if not result.isError():
                    valor = result.registers[0]
                    status = 1 if valor > 0 else 0
                    
                    self.successful_reads += 1
                    self.last_successful_read = time.time()
                    self.logger.debug(f"Leitura saída {canal} unit_id {self.unit_id} bem-sucedida ({elapsed_time:.3f}s): {status}")
                    return status
                else:
                    if attempt < self.retry_count:
                        delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                        self.logger.warning(f"Erro ao ler saída {canal} unit_id {self.unit_id}: {result}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Erro definitivo ao ler saída {canal} unit_id {self.unit_id}: {result}")
                        print(f"Erro ao ler saída {canal} unit_id {self.unit_id}: {result}")
                        self.failed_reads += 1
                        return None
                        
            except Exception as e:
                if attempt < self.retry_count:
                    delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                    self.logger.warning(f"Erro na leitura saída {canal} unit_id {self.unit_id}: {e}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"Erro definitivo na leitura saída {canal} unit_id {self.unit_id}: {e}")
                    print(f"Erro na leitura saída {canal} unit_id {self.unit_id}: {e}")
                    self.failed_reads += 1
                    return None
        
        return None

    def le_status_saidas_digitais(self):
        """Lê status das saídas como lista de 0/1 (16 saídas) com retry automático"""
        for attempt in range(self.retry_count + 1):
            if not self.client or not self.client.connected:
                if not self.connect():
                    continue
            
            try:
                start_time = time.time()
                # Lê 16 registradores a partir do 0 (saídas)
                result = self.client.read_holding_registers(0, count=16, device_id=self.unit_id)
                elapsed_time = time.time() - start_time
                
                if not result.isError():
                    registradores = result.registers
                    saidas = [0] * 16
                    
                    # Converte registradores para status digital
                    # Cada registrador representa uma saída
                    # Valores típicos: 0 = OFF, >0 = ON
                    for i, valor in enumerate(registradores):
                        if i < 16:  # Apenas as primeiras 16 saídas
                            saidas[i] = 1 if valor > 0 else 0
                    
                    self.successful_reads += 1
                    self.last_successful_read = time.time()
                    self.logger.debug(f"Leitura saídas unit_id {self.unit_id} bem-sucedida ({elapsed_time:.3f}s)")
                    return saidas
                else:
                    if attempt < self.retry_count:
                        delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                        self.logger.warning(f"Erro ao ler saídas unit_id {self.unit_id}: {result}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Erro definitivo ao ler saídas unit_id {self.unit_id}: {result}")
                        print(f"Erro ao ler saídas unit_id {self.unit_id}: {result}")
                        self.failed_reads += 1
                        return None
                        
            except Exception as e:
                if attempt < self.retry_count:
                    delay = min(self.retry_delay * (self.backoff_multiplier ** attempt), self.MAX_RETRY_DELAY)
                    self.logger.warning(f"Erro na leitura unit_id {self.unit_id}: {e}. Tentativa {attempt + 1}/{self.retry_count + 1}. Aguardando {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    self.logger.error(f"Erro definitivo na leitura unit_id {self.unit_id}: {e}")
                    print(f"Erro na leitura unit_id {self.unit_id}: {e}")
                    self.failed_reads += 1
                    return None
        
        return None
    
    def get_performance_stats(self):
        """Retorna estatísticas de performance da conexão"""
        success_rate = 0
        if self.successful_reads + self.failed_reads > 0:
            success_rate = (self.successful_reads / (self.successful_reads + self.failed_reads)) * 100
        
        return {
            'unit_id': self.unit_id,
            'connection_attempts': self.connection_attempts,
            'successful_reads': self.successful_reads,
            'failed_reads': self.failed_reads,
            'success_rate': success_rate,
            'last_successful_read': self.last_successful_read
        }
    
    def enable_debug_logging(self):
        """Habilita logs detalhados para diagnóstico"""
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def set_custom_timing(self, retry_count=None, retry_delay=None, backoff_multiplier=None):
        """Permite configurar tempos customizados por dispositivo"""
        if retry_count is not None:
            self.retry_count = retry_count
        if retry_delay is not None:
            self.retry_delay = retry_delay
        if backoff_multiplier is not None:
            self.backoff_multiplier = backoff_multiplier


# Exemplo de uso otimizado para Eletechsup 25IOB16
if __name__ == "__main__":
    print("🚀 TESTE OTIMIZADO - Eletechsup 25IOB16 com timeouts ajustados")
    print("=" * 60)
    
    # Configura conexão com IP correto do problema relatado
    modbus = Modbus25IOB16Pymodbus("10.0.2.217", timeout=15)  # Timeout aumentado
    
    # Habilita logs de diagnóstico para análise
    modbus.enable_debug_logging()
    
    # Testa diferentes configurações de timing se necessário
    print("⚙️ Configurando timing conservador para testes iniciais...")
    modbus.set_custom_timing(
        retry_count=2,      # 2 tentativas extras
        retry_delay=1.5,    # Delay inicial de 1.5s
        backoff_multiplier=1.5  # Multiplicador conservador
    )
    
    print(f"🔌 Conectando ao dispositivo {modbus.host}...")
    
    # Conecta
    if not modbus.connect():
        print("❌ Erro ao conectar após todas as tentativas!")
        print("\n💡 SUGESTÕES:")
        print("   • Verifique se o dispositivo está energizado")
        print("   • Confirme o IP do gateway (atual: 10.0.2.217)")
        print("   • Teste com unit_id diferente (atual: 1)")
        print("   • Verifique conexão RS485 A/B")
        exit(1)
    
    print("✅ Conexão estabelecida com sucesso!")
    
    try:
        # Teste prioritário: leitura das entradas (interruptores de luz - crítico)
        print("\n🔍 TESTE CRÍTICO - Lendo status das entradas (interruptores)...")
        start_time = time.time()
        entradas = modbus.le_status_entradas()
        elapsed = time.time() - start_time
        
        if entradas:
            entradas_ativas = [i+1 for i, x in enumerate(entradas) if x]
            print(f"✅ Entradas lidas em {elapsed:.3f}s: {entradas_ativas if entradas_ativas else 'Nenhuma ativa'}")
        else:
            print(f"❌ Falha na leitura das entradas após {elapsed:.3f}s")
        
        # Teste secundário: leitura das saídas (menos crítico)
        print("\n🔧 TESTE SECUNDÁRIO - Lendo status das saídas...")
        start_time = time.time()
        saidas = modbus.le_status_saidas_digitais()
        elapsed = time.time() - start_time
        
        if saidas:
            saidas_ativas = [i+1 for i, x in enumerate(saidas) if x]
            print(f"✅ Saídas lidas em {elapsed:.3f}s: {saidas_ativas if saidas_ativas else 'Nenhuma ativa'}")
        else:
            print(f"❌ Falha na leitura das saídas após {elapsed:.3f}s")
        
        # Teste de escrita conservador
        print("\n⚡ TESTE DE ESCRITA - Liga canal 1...")
        start_time = time.time()
        if modbus.liga_canal(1):
            elapsed = time.time() - start_time
            print(f"✅ Comando executado em {elapsed:.3f}s")
            
            # Aguarda tempo adequado antes da próxima operação
            print("⏳ Aguardando 2s para estabilização...")
            time.sleep(2)
            
            # Verifica se funcionou
            print("🔍 Verificando resultado...")
            saidas_verificacao = modbus.le_status_saidas_digitais()
            if saidas_verificacao and saidas_verificacao[0] == 1:
                print("✅ Canal 1 confirmado como LIGADO")
            else:
                print("⚠️ Canal 1 pode não ter sido ligado corretamente")
        else:
            elapsed = time.time() - start_time
            print(f"❌ Falha no comando após {elapsed:.3f}s")
    
    finally:
        # Mostra estatísticas finais
        print("\n📊 ESTATÍSTICAS DA SESSÃO:")
        stats = modbus.get_performance_stats()
        print(f"   • Tentativas de conexão: {stats['connection_attempts']}")
        print(f"   • Operações bem-sucedidas: {stats['successful_reads']}")
        print(f"   • Operações falharam: {stats['failed_reads']}")
        print(f"   • Taxa de sucesso: {stats['success_rate']:.1f}%")
        
        modbus.disconnect()
        print("\n🔌 Conexão fechada.")
        print("\n💡 PRÓXIMOS PASSOS:")
        print("   • Se ainda houver erros, tente unit_id=2 ou outro valor")
        print("   • Use o monitor multi-módulo com intervalos otimizados")
        print("   • Execute 'stats' no monitor para acompanhar performance")