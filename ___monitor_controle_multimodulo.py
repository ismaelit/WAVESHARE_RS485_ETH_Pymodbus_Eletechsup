#!/usr/bin/env python3
"""
Monitor e Controle Multi-Módulo - Suporte a Múltiplos Módulos 25IOB16
- Leitura otimizada: entradas automáticas a cada 100ms (registro 192)
- Saídas sob demanda: leitura apenas quando solicitado pelo usuário
- Redução de tráfego: 1 comando Modbus para todas as entradas
- Thread dedicada para entradas (não bloqueia interface)
- Controle de concorrência com locks

CONFIGURAÇÕES HARDCODED:
- Gateway IP: 10.0.2.218
- Porta: 502
- Módulos: Array de endereços Modbus unit_id

FUNCIONALIDADES:
- Monitoramento I/O multi-módulo com leitura otimizada de entradas
- Saídas sob demanda: leitura apenas quando solicitado
- Toggle configurável por entrada (software)
- Controle manual simultâneo das saídas
- Interface de comandos hierárquica
- Estatísticas e log em tempo real por módulo

COMANDOS HIERÁRQUICOS:
- 1.5: Toggle manual de saída 5 do módulo 1
- t2.3: Ativar/desativar toggle entrada 3 do módulo 2
- on3.7: Ligar saída 7 do módulo 3
- off1.12: Desligar saída 12 do módulo 1
- all_on.2: Ligar todas saídas do módulo 2
- read1: Ler todas saídas do módulo 1 (sob demanda)
- read1.5: Ler saída 5 do módulo 1 (sob demanda)
- status: Mostrar estado de todos módulos
- help: Mostrar ajuda
- quit: Sair
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import signal
import sys
import threading
import queue
from datetime import datetime
import os

# =============================================================================
# CONFIGURAÇÕES GLOBAIS DE TEMPO - LEITURA OTIMIZADA
# =============================================================================
# CONFIGURAÇÕES OTIMIZADAS PARA ELETECHSUP 25IOB16
INTERVALO_LEITURA_ENTRADAS = 0.5             # 500ms - leitura automática das entradas
# SAÍDAS: LEITURA SOB DEMANDA (não há polling automático)
TIMEOUT_THREAD_COMANDOS = 8.0                # Timeout para comandos
TIMEOUT_ERRO_EXECUCAO = 2.0                  # Timeout para recuperação
MAX_TENTATIVAS_RETRY = 3                     # Máximo de tentativas por operação
# =============================================================================

class MonitorMultiModulo:
    def __init__(self):
        # CONFIGURAÇÕES HARDCODED DO AMBIENTE
        self.gateway_ip = "10.0.2.217"      # IP do gateway WAVESHARE
        self.gateway_porta = 502            # Porta Modbus TCP
        self.modulos_candidatos = [1, 2]  # Possíveis unit_ids para detectar
        self.modulos_enderecos = []         # Módulos ativos (detectados automaticamente)
        
        # Inicializa conexões para cada módulo
        self.modulos = {}
        self.executando = True
        
        # Estados das I/O por módulo
        self.estados_anteriores_entradas = {}
        self.estados_atuais_entradas = {}
        self.estados_atuais_saidas = {}
        
        # Configurações de toggle por software por módulo
        self.toggle_habilitado = {}
        self.estado_toggle_saidas = {}
        
        # Estatísticas por módulo
        self.contadores_leituras = {}
        self.contadores_comandos = {}
        self.contadores_toggles = {}
        self.tempo_inicio = time.time()
        
        # Configurações gerais
        self.mostrar_detalhado = True
        
        # Controle de frequência de leitura das entradas
        self.ultima_leitura_entradas = {}
        
        # Controle de polling sob demanda por módulo
        self.polling_entradas_habilitado = {}    # True/False para cada módulo
        self.polling_saidas_habilitado = {}      # True/False para cada módulo  
        self.polling_saidas_intervalo = {}       # Intervalo para polling de saídas por módulo
        self.ultima_leitura_saidas = {}          # Timestamp da última leitura de saídas
        
        # Thread de comandos e leitura de entradas
        self.comando_queue = queue.Queue()
        self.thread_comandos = None
        self.thread_leitura_entradas = None
        
        # Locks para controle de concorrência
        self.lock_estados = threading.Lock()
        self.lock_modulos = threading.Lock()
        
        # Configura handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Configurações específicas por módulo (portas disponíveis)
        self.configuracoes_modulos = {
            1: {'max_portas': 16, 'tem_entradas': True},   # Módulo 1: 16 portas com entradas
            2: {'max_portas': 4, 'tem_entradas': False}    # Módulo 2: 4 portas sem entradas
        }
        
        # Detecta e inicializa módulos disponíveis
        self._detectar_e_inicializar_modulos()
        
    def habilitar_debug_modulo(self, unit_id=None):
        """Habilita logs de diagnóstico detalhado para um módulo específico ou todos"""
        if unit_id is None:
            # Habilita para todos os módulos
            for modulo in self.modulos.values():
                modulo.enable_debug_logging()
            print("🔍 Debug habilitado para todos os módulos")
        elif unit_id in self.modulos:
            self.modulos[unit_id].enable_debug_logging()
            print(f"🔍 Debug habilitado para módulo {unit_id}")
        else:
            print(f"❌ Módulo {unit_id} não encontrado")
            
    def mostrar_stats_performance(self):
        """Mostra estatísticas de performance de todos os módulos"""
        print("\n📊 ESTATÍSTICAS DE PERFORMANCE:")
        print("=" * 60)
        
        for unit_id in self.modulos_enderecos:
            stats = self.modulos[unit_id].get_performance_stats()
            print(f"🔧 MÓDULO {unit_id}:")
            print(f"   • Tentativas conexão: {stats['connection_attempts']}")
            print(f"   • Leituras bem-sucedidas: {stats['successful_reads']}")
            print(f"   • Leituras falharam: {stats['failed_reads']}")
            print(f"   • Taxa de sucesso: {stats['success_rate']:.1f}%")
            if stats['last_successful_read']:
                import datetime
                last_read = datetime.datetime.fromtimestamp(stats['last_successful_read'])
                print(f"   • Última leitura: {last_read.strftime('%H:%M:%S')}")
            print()
    
    def _detectar_modulos_disponiveis(self):
        """Detecta automaticamente quais módulos estão conectados"""
        print("🔍 Detectando módulos disponíveis...")
        modulos_encontrados = []
        
        for unit_id in self.modulos_candidatos:
            print(f"   • Testando módulo {unit_id}...", end=" ")
            
            # Cria conexão temporária com timeout otimizado
            modbus_temp = Modbus25IOB16Pymodbus(self.gateway_ip, self.gateway_porta, unit_id, timeout=15)
            
            try:
                if modbus_temp.connect():
                    # Testa leitura de um registrador conhecido (entradas)
                    entradas = modbus_temp.le_status_entradas()
                    if entradas is not None:
                        print("✅ ATIVO")
                        modulos_encontrados.append(unit_id)
                    else:
                        print("❌ SEM RESPOSTA")
                else:
                    print("❌ CONEXÃO FALHOU")
            except Exception as e:
                print(f"❌ ERRO: {e}")
            finally:
                modbus_temp.disconnect()
        
        return modulos_encontrados
    
    def _detectar_e_inicializar_modulos(self):
        """Detecta e inicializa apenas módulos disponíveis"""
        # Detecta módulos ativos
        self.modulos_enderecos = self._detectar_modulos_disponiveis()
        
        if not self.modulos_enderecos:
            print("❌ Nenhum módulo detectado!")
            print("   Verifique:")
            print("   • Conexão física RS485")
            print("   • Configuração unit_id nos módulos")
            print("   • Gateway funcionando")
            return False
        
        print(f"✅ Módulos detectados: {self.modulos_enderecos}")
        
        # Inicializa estruturas apenas para módulos encontrados
        for unit_id in self.modulos_enderecos:
            # Cria conexão Modbus para cada módulo com configurações otimizadas
            modulo = Modbus25IOB16Pymodbus(
                self.gateway_ip, 
                self.gateway_porta, 
                unit_id,
                timeout=15  # Timeout otimizado para Eletechsup 25IOB16
            )
            
            # Configura timing customizado baseado nas especificações do dispositivo
            modulo.set_custom_timing(
                retry_count=2,      # Menos tentativas para evitar sobrecarga
                retry_delay=1.0,    # Delay maior entre tentativas
                backoff_multiplier=1.5  # Backoff mais conservador
            )
            
            self.modulos[unit_id] = modulo
            
            # Inicializa estados I/O
            self.estados_anteriores_entradas[unit_id] = [0] * 16
            self.estados_atuais_entradas[unit_id] = [0] * 16
            self.estados_atuais_saidas[unit_id] = [0] * 16
            
            # Inicializa configurações toggle
            self.toggle_habilitado[unit_id] = [False] * 16
            self.estado_toggle_saidas[unit_id] = [False] * 16
            
            # Inicializa contadores
            self.contadores_leituras[unit_id] = 0
            self.contadores_comandos[unit_id] = 0
            self.contadores_toggles[unit_id] = 0
            
            # Inicializa timestamp de leitura das entradas
            self.ultima_leitura_entradas[unit_id] = time.time()  # Inicializa com tempo atual
            print(f"   ⏰ M{unit_id} - Timestamp inicializado: {self.ultima_leitura_entradas[unit_id]}")
            
            # Inicializa controles de polling
            config = self.configuracoes_modulos.get(unit_id, {'max_portas': 16, 'tem_entradas': True})
            self.polling_entradas_habilitado[unit_id] = config['tem_entradas']  # Habilitado por padrão se tem entradas
            self.polling_saidas_habilitado[unit_id] = False  # Desabilitado por padrão
            self.polling_saidas_intervalo[unit_id] = 1.0     # 1 segundo por padrão
            self.ultima_leitura_saidas[unit_id] = time.time()
            print(f"   🔄 M{unit_id} - Polling entradas: {'ON' if self.polling_entradas_habilitado[unit_id] else 'OFF'}")
            print(f"   🔄 M{unit_id} - Polling saídas: {'ON' if self.polling_saidas_habilitado[unit_id] else 'OFF'}")
        
        return True
    
    def signal_handler(self, sig, frame):
        """Handler para Ctrl+C"""
        print("\n🛑 Interrompendo monitor multi-módulo...")
        self.executando = False
        if self.thread_comandos and self.thread_comandos.is_alive():
            self.thread_comandos.join(timeout=TIMEOUT_THREAD_COMANDOS)
        if self.thread_leitura_entradas and self.thread_leitura_entradas.is_alive():
            self.thread_leitura_entradas.join(timeout=TIMEOUT_THREAD_COMANDOS)
    
    def conectar_todos(self):
        """Estabelece conexão com módulos detectados"""
        if not self.modulos_enderecos:
            print("❌ Nenhum módulo foi detectado na inicialização!")
            return False
            
        print(f"🔌 Conectando aos módulos detectados...")
        print(f"   Gateway: {self.gateway_ip}:{self.gateway_porta}")
        
        conectados = []
        falharam = []
        
        for unit_id in self.modulos_enderecos:
            print(f"   • Módulo {unit_id}...", end=" ")
            if self.modulos[unit_id].connect():
                print("✅")
                conectados.append(unit_id)
            else:
                print("❌")
                falharam.append(unit_id)
        
        if conectados:
            print(f"✅ Conectados: Módulos {conectados}")
        if falharam:
            print(f"❌ Falharam: Módulos {falharam}")
            # Remove módulos que falharam na conexão
            for unit_id in falharam:
                if unit_id in self.modulos_enderecos:
                    self.modulos_enderecos.remove(unit_id)
            
        return len(conectados) > 0
    
    def desconectar_todos(self):
        """Fecha conexão com todos os módulos"""
        for unit_id, modbus in self.modulos.items():
            if modbus.client and modbus.client.connected:
                modbus.disconnect()
        print("🔌 Todas conexões fechadas")
    
    def formatar_tempo(self):
        """Formata timestamp atual"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def parsear_comando_hierarquico(self, comando):
        """
        Parseia comandos hierárquicos no formato módulo.porta
        Retorna: (comando_base, modulo, porta) ou (None, None, None) se inválido
        
        Exemplos:
        - "1.5" -> ("", 1, 5)
        - "t2.3" -> ("t", 2, 3)  
        - "on3.7" -> ("on", 3, 7)
        - "all_on.2" -> ("all_on", 2, None)
        """
        try:
            # Handle commands without dot like 'read1', 'read2'
            if "." not in comando:
                # Check for commands like 'read1', 'read2'
                import re
                match = re.match(r'^([a-z_]+)(\d+)$', comando)
                if match:
                    prefixo, modulo_str = match.groups()
                    if prefixo == 'read':
                        modulo = int(modulo_str)
                        return prefixo, modulo, None
                return None, None, None
            
            # Separa comando e endereço hierárquico
            # Primeiro verifica comandos com 2 pontos: "polling.1.in", "polling.1.out"
            if comando.count('.') == 2:
                import re
                match_special = re.match(r'^([a-z_]+)\.(\d+)\.([a-z]+)$', comando)
                if match_special:
                    prefixo, modulo_str, tipo = match_special.groups()
                    if prefixo == 'polling':
                        modulo = int(modulo_str)
                        return f"{prefixo}.{tipo}", modulo, None  # Ex: "polling.in", modulo, None
            
            elif comando.count('.') == 1:
                # Casos: "1.5", "all_on.2"
                parte1, parte2 = comando.split('.')
                
                # Verifica se parte1 é número (comando direto) ou texto+número
                if parte1.isdigit():
                    # Comando direto: "1.5" = toggle módulo 1 porta 5
                    modulo = int(parte1)
                    porta = int(parte2)
                    return "", modulo, porta
                else:
                    # Comando com prefixo: "all_on.2", "t2.3", "on3.7", "test_polling.1"
                    # Extrai prefixo e números
                    import re
                    
                    # Verifica comandos normais: "t2.3", "on3.7", "test_polling.1"
                    match = re.match(r'^([a-z_]+)(\d*)\.(\d+)$', comando)
                    if match:
                        prefixo, modulo_str, porta_str = match.groups()
                        
                        if prefixo in ['all_on', 'all_off']:
                            # Comandos globais: "all_on.2"
                            modulo = int(porta_str)  # Na verdade é o módulo
                            return prefixo, modulo, None
                        elif prefixo == 'test_polling':
                            # Comando test_polling.1
                            modulo = int(porta_str)  # Na verdade é o módulo
                            return prefixo, modulo, None
                        else:
                            # Comandos com módulo: "t2.3", "on3.7"
                            if modulo_str:
                                modulo = int(modulo_str)
                                porta = int(porta_str)
                                return prefixo, modulo, porta
            
            return None, None, None
            
        except (ValueError, AttributeError):
            return None, None, None
    
    def detectar_bordas_entradas(self, unit_id, entradas_atual, entradas_anterior):
        """Detecta bordas de subida (LOW→HIGH) nas entradas de um módulo"""
        bordas_subida = []
        
        for i in range(16):
            # Borda de subida: anterior=0, atual=1
            if entradas_anterior[i] == 0 and entradas_atual[i] == 1:
                bordas_subida.append(i + 1)  # Canal 1-16
        
        return bordas_subida
    
    def processar_toggle_entradas(self, unit_id, bordas_subida):
        """Processa toggles nas entradas com bordas de subida detectadas"""
        comandos_executados = []
        
        for canal in bordas_subida:
            idx = canal - 1  # Índice 0-15
            
            # Verifica se toggle está habilitado para este canal
            if self.toggle_habilitado[unit_id][idx]:
                # Inverte estado do toggle
                self.estado_toggle_saidas[unit_id][idx] = not self.estado_toggle_saidas[unit_id][idx]
                
                # Executa comando no hardware (já dentro do lock do ciclo de leitura)
                if self.estado_toggle_saidas[unit_id][idx]:
                    sucesso = self.modulos[unit_id].liga_canal(canal)
                    acao = "ON"
                else:
                    sucesso = self.modulos[unit_id].desliga_canal(canal)
                    acao = "OFF"
                
                if sucesso:
                    comandos_executados.append(f"Toggle M{unit_id} E{canal}→S{canal}: {acao}")
                    self.contadores_toggles[unit_id] += 1
                else:
                    comandos_executados.append(f"Toggle M{unit_id} E{canal}→S{canal}: ERRO")
        
        return comandos_executados
    
    def executar_comando_hierarquico(self, comando):
        """Executa comando manual com endereçamento hierárquico"""
        comando = comando.strip().lower()
        
        try:
            # Parse do comando hierárquico
            cmd_base, modulo, porta = self.parsear_comando_hierarquico(comando)
            print(f"🔍 DEBUG: comando='{comando}' -> cmd_base='{cmd_base}', modulo={modulo}, porta={porta}")
            
            if cmd_base is None:
                # Comandos globais sem hierarquia
                if comando == 'status':
                    self.mostrar_status_todos_modulos()
                    return True
                elif comando == 'help':
                    self.mostrar_ajuda()
                    return True
                elif comando == 'stats':
                    self.mostrar_stats_performance()
                    return True
                elif comando.startswith('debug'):
                    # Comando debug pode ser: "debug" (todos) ou "debug.1" (módulo específico)
                    if '.' in comando:
                        try:
                            unit_id = int(comando.split('.')[1])
                            self.habilitar_debug_modulo(unit_id)
                        except (ValueError, IndexError):
                            print("❌ Formato inválido. Use 'debug.1' para módulo específico")
                    else:
                        self.habilitar_debug_modulo()
                    return True
                elif comando in ['quit', 'exit', 'q']:
                    print("👋 Saindo do monitor multi-módulo...")
                    self.executando = False
                    return True
                else:
                    print(f"❌ Comando inválido: '{comando}'. Use formato 'módulo.porta' ou 'help'")
                    return False
            
            # Valida módulo
            if modulo not in self.modulos_enderecos:
                print(f"❌ Módulo {modulo} não existe. Módulos disponíveis: {self.modulos_enderecos}")
                return False
                
            # Pega configurações do módulo
            config = self.configuracoes_modulos.get(modulo, {'max_portas': 16, 'tem_entradas': True})
            
            # Executa comandos específicos
            if cmd_base == "":
                # Toggle manual direto: "1.5"
                if 1 <= porta <= config['max_portas']:
                    if self.modulos[modulo].toggle_canal(porta):
                        print(f"✅ Toggle manual M{modulo}.S{porta} executado")
                        self.contadores_comandos[modulo] += 1
                        return True
                    else:
                        print(f"❌ Erro no toggle M{modulo}.S{porta}")
                        return False
                else:
                    print(f"❌ Porta {porta} inválida para módulo {modulo}. Máximo: {config['max_portas']}")
                    return False
            
            elif cmd_base == "t":
                # Toggle configuração: "t2.3"
                if not config['tem_entradas']:
                    print(f"❌ Módulo {modulo} não possui entradas digitais")
                    return False
                if 1 <= porta <= 16:
                    idx = porta - 1
                    self.toggle_habilitado[modulo][idx] = not self.toggle_habilitado[modulo][idx]
                    status = "HABILITADO" if self.toggle_habilitado[modulo][idx] else "DESABILITADO"
                    print(f"✅ Toggle entrada M{modulo}.E{porta}: {status}")
                    return True
            
            elif cmd_base == "on":
                # Ligar saída: "on3.7"
                if 1 <= porta <= config['max_portas']:
                    if self.modulos[modulo].liga_canal(porta):
                        print(f"✅ Saída M{modulo}.S{porta} LIGADA")
                        self.contadores_comandos[modulo] += 1
                        return True
                    else:
                        print(f"❌ Erro ao ligar M{modulo}.S{porta}")
                        return False
                else:
                    print(f"❌ Porta {porta} inválida para módulo {modulo}. Máximo: {config['max_portas']}")
                    return False
            
            elif cmd_base == "off":
                # Desligar saída: "off1.12"
                if 1 <= porta <= config['max_portas']:
                    if self.modulos[modulo].desliga_canal(porta):
                        print(f"✅ Saída M{modulo}.S{porta} DESLIGADA")
                        self.contadores_comandos[modulo] += 1
                        return True
                    else:
                        print(f"❌ Erro ao desligar M{modulo}.S{porta}")
                        return False
                else:
                    print(f"❌ Porta {porta} inválida para módulo {modulo}. Máximo: {config['max_portas']}")
                    return False
            
            elif cmd_base == "all_on":
                # Ligar todas: "all_on.2"
                if self.modulos[modulo].liga_tudo():
                    print(f"✅ Todas saídas do módulo {modulo} LIGADAS")
                    self.contadores_comandos[modulo] += 1
                    return True
                else:
                    print(f"❌ Erro ao ligar todas saídas do módulo {modulo}")
                    return False
            
            elif cmd_base == "all_off":
                # Desligar todas: "all_off.2"
                if self.modulos[modulo].desliga_tudo():
                    print(f"✅ Todas saídas do módulo {modulo} DESLIGADAS")
                    self.contadores_comandos[modulo] += 1
                    return True
                else:
                    print(f"❌ Erro ao desligar todas saídas do módulo {modulo}")
                    return False
            
            elif cmd_base == "test_polling":
                # Testa o polling das entradas
                print(f"🧪 Testando polling do módulo {modulo}...")
                tempo_atual = time.time()
                
                # Teste entradas
                config = self.configuracoes_modulos.get(modulo, {'max_portas': 16, 'tem_entradas': True})
                if config['tem_entradas']:
                    tempo_desde_ultima = tempo_atual - self.ultima_leitura_entradas[modulo]
                    print(f"   📥 ENTRADAS:")
                    print(f"      • Status: {'HABILITADO' if self.polling_entradas_habilitado[modulo] else 'DESABILITADO'}")
                    print(f"      • Tempo desde última leitura: {tempo_desde_ultima:.3f}s")
                    print(f"      • Intervalo configurado: {INTERVALO_LEITURA_ENTRADAS:.3f}s")
                    print(f"      • Deve ler agora: {tempo_desde_ultima >= INTERVALO_LEITURA_ENTRADAS}")
                else:
                    print(f"   📥 ENTRADAS: Módulo {modulo} não possui entradas")
                    
                # Teste saídas
                tempo_desde_ultima_saidas = tempo_atual - self.ultima_leitura_saidas[modulo]
                print(f"   📤 SAÍDAS:")
                print(f"      • Status: {'HABILITADO' if self.polling_saidas_habilitado[modulo] else 'DESABILITADO'}")
                print(f"      • Tempo desde última leitura: {tempo_desde_ultima_saidas:.3f}s")
                print(f"      • Intervalo configurado: {self.polling_saidas_intervalo[modulo]:.3f}s")
                print(f"      • Deve ler agora: {tempo_desde_ultima_saidas >= self.polling_saidas_intervalo[modulo]}")
                return True
                
            elif cmd_base == "polling.in":
                # Controla polling de entradas: polling.1.in
                config = self.configuracoes_modulos.get(modulo, {'max_portas': 16, 'tem_entradas': True})
                if not config['tem_entradas']:
                    print(f"❌ Módulo {modulo} não possui entradas digitais")
                    return False
                    
                # Toggle do estado do polling de entradas
                self.polling_entradas_habilitado[modulo] = not self.polling_entradas_habilitado[modulo]
                status = "HABILITADO" if self.polling_entradas_habilitado[modulo] else "DESABILITADO"
                print(f"✅ Polling de entradas M{modulo}: {status}")
                return True
                
            elif cmd_base == "polling.out":
                # Controla polling de saídas: polling.1.out
                self.polling_saidas_habilitado[modulo] = not self.polling_saidas_habilitado[modulo]
                status = "HABILITADO" if self.polling_saidas_habilitado[modulo] else "DESABILITADO"
                print(f"✅ Polling de saídas M{modulo}: {status}")
                if self.polling_saidas_habilitado[modulo]:
                    print(f"   • Intervalo: {self.polling_saidas_intervalo[modulo]:.1f}s")
                return True
                
            elif cmd_base == "read":
                # Ler saídas sob demanda: "read1" ou "read1.5"
                if porta is None:
                    # Lê todas as saídas do módulo de uma vez (otimizado)
                    print(f"📡 M{modulo} - Lendo todas as saídas...")
                    saidas = self.modulos[modulo].le_status_saidas_digitais()
                    if saidas is not None:
                        # Atualiza estado atual das saídas
                        self.estados_atuais_saidas[modulo] = saidas.copy()
                        max_portas = self.configuracoes_modulos[modulo]['max_portas']
                        
                        # Mostra todas as saídas de uma vez
                        print(f"📊 M{modulo} - Status de todas as saídas:")
                        for i in range(max_portas):
                            estado = "LIGADA" if saidas[i] > 0 else "DESLIGADA"
                            print(f"   • Saída {i+1}: {estado}")
                        
                        saidas_ativas = [i+1 for i, x in enumerate(saidas[:max_portas]) if x]
                        print(f"📡 M{modulo} - Resumo: {saidas_ativas if saidas_ativas else 'Nenhuma'} ativa(s)")
                        return True
                    else:
                        print(f"❌ Erro ao ler saídas do módulo {modulo}")
                        return False
                else:
                    # Lê saída específica (otimizado - lê apenas 1 registrador)
                    print(f"📡 M{modulo}.S{porta} - Lendo registrador específico...")
                    status = self.modulos[modulo].le_status_saida_especifica(porta)
                    if status is not None:
                        # Atualiza apenas a saída específica no estado atual
                        if hasattr(self, 'estados_atuais_saidas') and modulo in self.estados_atuais_saidas:
                            self.estados_atuais_saidas[modulo][porta-1] = status
                        estado = "LIGADA" if status > 0 else "DESLIGADA"
                        print(f"📡 M{modulo}.S{porta} - Estado: {estado}")
                        return True
                    else:
                        print(f"❌ Erro ao ler saída {porta} do módulo {modulo}")
                        return False
            
            print(f"❌ Comando não reconhecido: '{comando}'")
            return False
                
        except ValueError:
            print(f"❌ Formato inválido: '{comando}'. Use 'help' para ver exemplos")
            return False
        except Exception as e:
            print(f"❌ Erro ao executar comando: {e}")
            return False
    
    def mostrar_ajuda(self):
        """Mostra ajuda dos comandos hierárquicos disponíveis"""
        print("\n📋 COMANDOS HIERÁRQUICOS DISPONÍVEIS:")
        print("┌─────────────────────────────────────────────────────────┐")
        print("│ FORMATO: módulo.porta (ex: 1.5 = módulo 1, porta 5)    │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ CONTROLE DE SAÍDAS:                                     │")
        print("│   1.5         : Toggle manual saída 5 do módulo 1      │")
        print("│   on2.3       : Ligar saída 3 do módulo 2              │")
        print("│   off1.12     : Desligar saída 12 do módulo 1          │")
        print("│   all_on.2    : Ligar todas saídas do módulo 2         │")
        print("│   all_off.1   : Desligar todas saídas do módulo 1      │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ LEITURA DE SAÍDAS (SOB DEMANDA):                       │")
        print("│   read1       : Ler todas saídas do módulo 1           │")
        print("│   read1.5     : Ler saída 5 do módulo 1               │")
        print("│   read2       : Ler todas saídas do módulo 2           │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ CONTROLE DE POLLING:                                   │")
        print("│   polling.1.in   : Toggle polling entradas módulo 1    │")
        print("│   polling.1.out  : Toggle polling saídas módulo 1      │")
        print("│   polling.2.out  : Toggle polling saídas módulo 2      │")
        print("│   test_polling.1 : Status polling do módulo 1          │")
        print("│   test_polling.2 : Status polling do módulo 2          │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ CONFIGURAÇÃO TOGGLE:                                    │")
        print("│   t1.3        : Toggle entrada 3 do módulo 1           │")
        print("│   t2.7        : Toggle entrada 7 do módulo 2           │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ DIAGNÓSTICO E INFORMAÇÕES:                              │")
        print("│   status      : Status de todos módulos                │")
        print("│   stats       : Estatísticas de performance            │")
        print("│   debug       : Habilitar logs debug (todos módulos)   │")
        print("│   debug.1     : Habilitar logs debug (módulo 1)        │")
        print("│   help        : Mostrar esta ajuda                     │")
        print("│   quit        : Sair do programa                       │")
        print("└─────────────────────────────────────────────────────────┘")
        print(f"💡 Módulos disponíveis: {self.modulos_enderecos}")
        print(f"💡 Gateway: {self.gateway_ip}:{self.gateway_porta}")
    
    def thread_interface_comandos(self):
        """Thread para interface de comandos em background"""
        while self.executando:
            try:
                comando = input().strip()
                if comando:
                    self.executar_comando_hierarquico(comando)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️ Erro na interface: {e}")
    
    def mostrar_status_todos_modulos(self):
        """Mostra status detalhado de todos os módulos"""
        tempo_execucao = time.time() - self.tempo_inicio
        
        print(f"\n📊 STATUS MULTI-MÓDULO ({self.formatar_tempo()})")
        print("=" * 70)
        
        for unit_id in self.modulos_enderecos:
            print(f"\n🔧 MÓDULO {unit_id}:")
            
            # Estados das entradas
            entradas_ativas = [i+1 for i, x in enumerate(self.estados_atuais_entradas[unit_id]) if x]
            print(f"   🔍 ENTRADAS: {entradas_ativas if entradas_ativas else 'Nenhuma'}")
            
            # Estados das saídas
            saidas_ativas = [i+1 for i, x in enumerate(self.estados_atuais_saidas[unit_id]) if x]
            print(f"   🔧 SAÍDAS: {saidas_ativas if saidas_ativas else 'Nenhuma'}")
            
            # Toggle habilitado
            toggle_ativo = [i+1 for i, x in enumerate(self.toggle_habilitado[unit_id]) if x]
            print(f"   🔄 TOGGLE: {toggle_ativo if toggle_ativo else 'Nenhum'}")
            
            # Status do polling
            config = self.configuracoes_modulos.get(unit_id, {'max_portas': 16, 'tem_entradas': True})
            polling_in = "ON" if (config['tem_entradas'] and self.polling_entradas_habilitado[unit_id]) else "OFF"
            polling_out = "ON" if self.polling_saidas_habilitado[unit_id] else "OFF"
            print(f"   🔄 POLLING: IN:{polling_in} | OUT:{polling_out}")
            
            # Estatísticas por módulo
            print(f"   📈 STATS: L:{self.contadores_leituras[unit_id]} | C:{self.contadores_comandos[unit_id]} | T:{self.contadores_toggles[unit_id]}")
        
        # Estatísticas globais
        total_leituras = sum(self.contadores_leituras.values())
        total_comandos = sum(self.contadores_comandos.values())
        total_toggles = sum(self.contadores_toggles.values())
        
        print(f"\n🌐 TOTAIS:")
        print(f"   • Tempo execução: {tempo_execucao:.1f}s")
        print(f"   • Leituras totais: {total_leituras}")
        print(f"   • Comandos totais: {total_comandos}")
        print(f"   • Toggles totais: {total_toggles}")
        print(f"   • Taxa média: {total_leituras / tempo_execucao:.1f} Hz")
        print("=" * 70)
    
    def mostrar_mudancas(self, mudancas_por_modulo):
        """Mostra mudanças detectadas em todos os módulos"""
        timestamp = self.formatar_tempo()
        
        print(f"\n⚡ MUDANÇAS DETECTADAS [{timestamp}]")
        
        for unit_id, dados in mudancas_por_modulo.items():
            bordas = dados['bordas_subida']
            toggles = dados['toggles_executados'] 
            entradas = dados['entradas_ativas']
            saidas = dados['saidas_ativas']
            
            if bordas or toggles:
                print(f"   🔧 MÓDULO {unit_id}:")
                
                if bordas:
                    print(f"      🔍 Bordas ↗️: E{bordas}")
                
                if toggles:
                    for toggle in toggles:
                        print(f"      🔄 {toggle}")
                
                print(f"      📊 E: {entradas if entradas else '□'} | S: {saidas if saidas else '□'}")
    
    def executar_ciclo_leitura_modulo(self, unit_id):
        """Executa um ciclo de leitura para um módulo específico com retry robusto"""
        try:
            # Verifica configurações do módulo
            config = self.configuracoes_modulos.get(unit_id, {'max_portas': 16, 'tem_entradas': True})
            
            tempo_atual = time.time()
            
            # 1. Lê estado atual das entradas (apenas se o módulo tem entradas e tempo suficiente)
            entradas_atual = None
            tempo_desde_ultima = tempo_atual - self.ultima_leitura_entradas[unit_id]
            print(f"   ⏰ M{unit_id} - Tempo desde última leitura: {tempo_desde_ultima:.3f}s (limite: {INTERVALO_LEITURA_ENTRADAS:.3f}s)")
            
            if (config['tem_entradas'] and 
                self.polling_entradas_habilitado[unit_id] and 
                tempo_desde_ultima >= INTERVALO_LEITURA_ENTRADAS):
                print(f"   ✅ M{unit_id} - Hora de ler entradas!")
                # Retry robusto para leitura de entradas - REGISTRO 192 (OTIMIZADO!)
                for tentativa in range(MAX_TENTATIVAS_RETRY):
                    try:
                        entradas_atual = self.modulos[unit_id].le_status_entradas()
                        if entradas_atual is not None:
                            self.ultima_leitura_entradas[unit_id] = tempo_atual
                            print(f"📡 M{unit_id} - Entradas lidas (reg 192): {entradas_atual}")
                            break
                        time.sleep(0.1)  # Pequeno delay entre tentativas
                    except Exception as e:
                        if tentativa == MAX_TENTATIVAS_RETRY - 1:
                            print(f"❌ Falha na leitura de entradas M{unit_id} após {MAX_TENTATIVAS_RETRY} tentativas: {e}")
                            return None
                        time.sleep(0.2)
                
                if entradas_atual is None:
                    return None
            else:
                # Módulo sem entradas ou ainda não é hora de ler - usa estado anterior
                print(f"   ⏭️ M{unit_id} - Ainda não é hora de ler entradas")
                entradas_atual = self.estados_atuais_entradas[unit_id].copy()
            
            # 2. SAÍDAS: Lê automaticamente apenas se polling estiver habilitado
            saidas_digitais = None
            if self.polling_saidas_habilitado[unit_id]:
                tempo_desde_ultima_saidas = tempo_atual - self.ultima_leitura_saidas[unit_id]
                if tempo_desde_ultima_saidas >= self.polling_saidas_intervalo[unit_id]:
                    print(f"   ✅ M{unit_id} - Hora de ler saídas!")
                    for tentativa in range(MAX_TENTATIVAS_RETRY):
                        try:
                            saidas_digitais = self.modulos[unit_id].le_status_saidas_digitais()
                            if saidas_digitais is not None:
                                self.ultima_leitura_saidas[unit_id] = tempo_atual
                                print(f"📡 M{unit_id} - Saídas lidas: {saidas_digitais}")
                                break
                            time.sleep(0.1)
                        except Exception as e:
                            if tentativa == MAX_TENTATIVAS_RETRY - 1:
                                print(f"❌ Falha na leitura de saídas M{unit_id} após {MAX_TENTATIVAS_RETRY} tentativas: {e}")
                            time.sleep(0.2)
            
            # Se não leu saídas agora, mantém estado anterior
            if saidas_digitais is None:
                saidas_digitais = self.estados_atuais_saidas[unit_id].copy()
            
            # Ajusta tamanho do array de saídas conforme o módulo
            max_portas = config['max_portas']
            if len(saidas_digitais) > max_portas:
                saidas_digitais = saidas_digitais[:max_portas]
            
            # Preenche com zeros se necessário para manter compatibilidade
            while len(saidas_digitais) < 16:
                saidas_digitais.append(0)
            
            # 3. Detecta bordas de subida nas entradas
            bordas_subida = self.detectar_bordas_entradas(
                unit_id, entradas_atual, self.estados_anteriores_entradas[unit_id]
            )
            
            # 4. Processa toggles por software
            toggles_executados = []
            if bordas_subida:
                toggles_executados = self.processar_toggle_entradas(unit_id, bordas_subida)
            
            # 5. Atualiza estados com lock para controle de concorrência
            with self.lock_estados:
                self.estados_anteriores_entradas[unit_id] = entradas_atual.copy()
                self.estados_atuais_entradas[unit_id] = entradas_atual.copy()
                self.estados_atuais_saidas[unit_id] = saidas_digitais.copy()
            
            # 6. Atualiza contador
            self.contadores_leituras[unit_id] += 1
            
            # 7. Retorna dados de mudanças (apenas entradas)
            mudou_entradas = entradas_atual != self.estados_anteriores_entradas[unit_id]
            mudou_toggles = len(toggles_executados) > 0
            
            print(f"   🔍 M{unit_id} - Análise de mudanças:")
            print(f"      • Entradas mudaram: {mudou_entradas}")
            print(f"      • Toggles executados: {mudou_toggles}")
            print(f"      • Estado anterior: {self.estados_anteriores_entradas[unit_id]}")
            print(f"      • Estado atual: {entradas_atual}")
            
            return {
                'bordas_subida': bordas_subida,
                'toggles_executados': toggles_executados,
                'entradas_ativas': [i+1 for i, x in enumerate(entradas_atual) if x],
                'saidas_ativas': [i+1 for i, x in enumerate(saidas_digitais) if x],
                'mudou': (mudou_entradas or mudou_toggles)  # Não considera mudanças nas saídas
            }
            
        except Exception as e:
            print(f"❌ Erro no módulo {unit_id}: {e}")
            return None
    
    def thread_leitura_entradas(self):
        """Thread dedicada para leitura automática das entradas dos módulos"""
        print("🔄 Thread de leitura de entradas iniciada")
        ciclo = 0
        
        while self.executando:
            try:
                ciclo += 1
                print(f"🔄 Ciclo de leitura #{ciclo} - {self.formatar_tempo()}")
                
                mudancas_por_modulo = {}
                houve_mudancas = False
                
                # Lê todos os módulos com controle de concorrência
                with self.lock_modulos:
                    for unit_id in self.modulos_enderecos:
                        print(f"   📡 Lendo módulo {unit_id}...")
                        resultado = self.executar_ciclo_leitura_modulo(unit_id)
                        
                        if resultado is not None:
                            mudancas_por_modulo[unit_id] = resultado
                            if resultado['mudou']:
                                houve_mudancas = True
                                print(f"   ✅ Módulo {unit_id} - Mudanças detectadas!")
                            else:
                                print(f"   ⏭️ Módulo {unit_id} - Sem mudanças")
                        else:
                            print(f"   ❌ Falha na leitura do módulo {unit_id}")
                
                # Mostra mudanças se houver
                if houve_mudancas:
                    print(f"   🔄 Mostrando mudanças...")
                    self.mostrar_mudancas(mudancas_por_modulo)
                else:
                    print(f"   📊 Nenhuma mudança detectada neste ciclo")
                
                # Aguarda próximo ciclo de leitura de entradas
                print(f"   ⏰ Aguardando {INTERVALO_LEITURA_ENTRADAS*1000:.0f}ms para próximo ciclo...")
                time.sleep(INTERVALO_LEITURA_ENTRADAS)
                
            except Exception as e:
                print(f"❌ Erro na thread de leitura: {e}")
                time.sleep(TIMEOUT_ERRO_EXECUCAO)
        
        print("🔄 Thread de leitura de entradas finalizada")
    
    def executar_monitor_multimodulo(self):
        """Executa o monitor multi-módulo completo com leitura otimizada"""
        print("🚀 MONITOR MULTI-MÓDULO - 25IOB16 (LEITURA OTIMIZADA)")
        print("=" * 70)
        print("📋 CONFIGURAÇÕES:")
        print(f"   • Gateway: {self.gateway_ip}:{self.gateway_porta}")
        print(f"   • Módulos: {self.modulos_enderecos}")
        print(f"   • Intervalo entradas: {INTERVALO_LEITURA_ENTRADAS*1000:.0f}ms (automático)")
        print(f"   • Saídas: Leitura sob demanda (comando 'read')")
        print(f"   • Endereçamento: módulo.porta (ex: 1.5, 2.3)")
        print("=" * 70)
        
        # Primeira leitura de todos os módulos
        print("📡 Fazendo primeira leitura de todos módulos...")
        for unit_id in self.modulos_enderecos:
            config = self.configuracoes_modulos.get(unit_id, {'max_portas': 16, 'tem_entradas': True})
            
            # Lê entradas apenas se o módulo tem entradas
            if config['tem_entradas']:
                entradas = self.modulos[unit_id].le_status_entradas()
            else:
                entradas = [0] * 16  # Módulo sem entradas
                
            saidas = self.modulos[unit_id].le_status_saidas_digitais()
            
            if entradas is not None and saidas is not None:
                # Ajusta tamanho das saídas conforme o módulo
                max_portas = config['max_portas']
                if len(saidas) > max_portas:
                    saidas = saidas[:max_portas]
                while len(saidas) < 16:
                    saidas.append(0)
                
                self.estados_anteriores_entradas[unit_id] = entradas.copy()
                self.estados_atuais_entradas[unit_id] = entradas.copy()
                self.estados_atuais_saidas[unit_id] = saidas.copy()
                
                entradas_ativas = [i+1 for i, x in enumerate(entradas) if x] if config['tem_entradas'] else []
                saidas_ativas = [i+1 for i, x in enumerate(saidas[:max_portas]) if x]
                print(f"   📊 M{unit_id} - E: {entradas_ativas if entradas_ativas else '□'} | S: {saidas_ativas if saidas_ativas else '□'}")
                print(f"   💾 Estados salvos - Anterior: {self.estados_anteriores_entradas[unit_id]}")
                print(f"   💾 Estados salvos - Atual: {self.estados_atuais_entradas[unit_id]}")
            else:
                print(f"   ❌ Módulo {unit_id}: Erro na primeira leitura")
        
        self.tempo_inicio = time.time()
        
        # Inicia thread de comandos
        print("\n⌨️ Iniciando interface de comandos hierárquicos...")
        self.thread_comandos = threading.Thread(target=self.thread_interface_comandos, daemon=True)
        self.thread_comandos.start()
        
        # Inicia thread de leitura de entradas
        print("🔄 Iniciando thread de leitura de entradas...")
        self.thread_leitura_entradas = threading.Thread(target=self.thread_leitura_entradas, daemon=True, name="Thread_Leitura_Entradas")
        self.thread_leitura_entradas.start()
        print(f"✅ Thread de leitura iniciada: {self.thread_leitura_entradas.name}")
        
        print("\n🔄 Monitor multi-módulo ativo! Digite comandos ou 'help' para ajuda")
        print("   💡 Formato: módulo.porta (ex: 1.5 = toggle saída 5 do módulo 1)")
        print("   💡 Pressione Ctrl+C para parar")
        
        # Loop principal aguarda threads
        try:
            while self.executando:
                time.sleep(0.1)  # Loop leve para não bloquear
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupção via Ctrl+C")
        
        # Estatísticas finais
        tempo_total = time.time() - self.tempo_inicio
        total_leituras = sum(self.contadores_leituras.values())
        total_comandos = sum(self.contadores_comandos.values())
        total_toggles = sum(self.contadores_toggles.values())
        
        print(f"\n📊 MONITOR MULTI-MÓDULO FINALIZADO")
        print(f"   • Módulos monitorados: {len(self.modulos_enderecos)}")
        print(f"   • Leituras totais: {total_leituras}")
        print(f"   • Comandos executados: {total_comandos}")
        print(f"   • Toggles por software: {total_toggles}")
        print(f"   • Tempo total: {tempo_total:.1f}s")
        print(f"   • Taxa média: {total_leituras / tempo_total:.1f} Hz")

def main():
    """Função principal"""
    print("=" * 70)
    print("🔗 MONITOR MULTI-MÓDULO - 25IOB16 (LEITURA OTIMIZADA)")
    print("   Controle Hierárquico: módulo.porta")
    print("=" * 70)
    
    monitor = MonitorMultiModulo()
    
    try:
        # Verifica se encontrou módulos na detecção
        if not monitor.modulos_enderecos:
            print("❌ Nenhum módulo foi detectado!")
            print("\n🔍 SOLUÇÃO:")
            print("   1. Verifique se o módulo está energizado")
            print("   2. Confirme conexão RS485 (A/B)")
            print("   3. Verifique unit_id configurado no módulo")
            print("   4. Teste gateway com outro software")
            return
            
        if monitor.conectar_todos():
            monitor.executar_monitor_multimodulo()
        else:
            print("❌ Falha na conexão com os módulos")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        monitor.desconectar_todos()
        print("\n👋 Monitor multi-módulo finalizado!")

if __name__ == "__main__":
    main()
