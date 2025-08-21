#!/usr/bin/env python3
"""
Monitor e Controle Multi-Módulo - 25IOB16
Sistema simplificado para controle de múltiplos módulos Eletechsup via Modbus TCP

COMANDOS PRINCIPAIS:
- 1.5: Toggle saída 5 do módulo 1
- on2.3: Ligar saída 3 do módulo 2  
- off1.12: Desligar saída 12 do módulo 1
- all_on.2: Ligar todas saídas do módulo 2
- out1: Ler todas saídas do módulo 1
- out1.5: Ler saída 5 do módulo 1
- in1: Ler todas entradas do módulo 1
- status: Status de todos módulos
- help: Mostrar ajuda
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import signal
import threading
import queue
from datetime import datetime

# Configurações globais
INTERVALO_LEITURA = 0.5          # 500ms para leitura automática das entradas
INTERVALO_POLLING_IN1 = 0.2      # 200ms para polling específico do módulo 1
POLLING_IN1_ATIVO = True         # Ativa polling específico para entradas M1
MAX_TENTATIVAS = 3               # Tentativas de retry para operações Modbus
TIMEOUT_COMANDOS = 8.0           # Timeout para threads

class MonitorMultiModulo:
    def __init__(self):
        # Configurações de rede
        self.gateway_ip = "10.0.2.217"
        self.gateway_porta = 502
        
        # Configuração dos módulos (considerados sempre existentes)
        self.configuracoes_modulos = {
            1: {'max_portas': 16, 'tem_entradas': True},   # Módulo 1: 16 portas com entradas
            2: {'max_portas': 4, 'tem_entradas': False},    # Módulo 2: 4 portas sem entradas
            # 3: {'max_portas': 4, 'tem_entradas': False}    # Módulo 3: 4 portas sem entradas
        }
        
        self.modulos_enderecos = list(self.configuracoes_modulos.keys())
        self.modulos = {}
        self.executando = True
        
        # Estados atuais das I/O
        self.estados_entradas = {}
        self.estados_saidas = {}
        self.toggle_habilitado = {}
        self.estado_polling_in1 = [0] * 16  # Estado para polling específico M1
        
        # Contadores e estatísticas
        self.contadores = {modulo: {'leituras': 0, 'comandos': 0, 'toggles': 0} 
                          for modulo in self.modulos_enderecos}
        self.tempo_inicio = time.time()
        
        # Threads e controles
        self.threads = {}
        self.locks = {'estados': threading.Lock(), 'modulos': threading.Lock()}
        
        # Handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Inicializa módulos
        self._inicializar_modulos()

    def signal_handler(self, sig, frame):
        """Encerra threads ao receber Ctrl+C"""
        print("\n🛑 Encerrando monitor...")
        self.executando = False
        for thread in self.threads.values():
            if thread and thread.is_alive():
                thread.join(timeout=TIMEOUT_COMANDOS)

    def _inicializar_modulos(self):
        """Inicializa conexões e estados dos módulos configurados"""
        print(f"🔌 Inicializando módulos: {self.modulos_enderecos}")
        
        for unit_id in self.modulos_enderecos:
            # Cria conexão Modbus
            modulo = Modbus25IOB16Pymodbus(self.gateway_ip, self.gateway_porta, unit_id, timeout=15)
            modulo.set_custom_timing(retry_count=2, retry_delay=1.0, backoff_multiplier=1.5)
            self.modulos[unit_id] = modulo
            
            # Inicializa estados
            self.estados_entradas[unit_id] = [0] * 16
            self.estados_saidas[unit_id] = [0] * 16
            self.toggle_habilitado[unit_id] = [False] * 16
            
            print(f"   ✅ M{unit_id} configurado")

    def conectar_todos(self):
        """Conecta aos módulos e faz leitura inicial do estado das portas"""
        print(f"🔌 Conectando ao gateway {self.gateway_ip}:{self.gateway_porta}")
        
        conectados = []
        for unit_id in self.modulos_enderecos:
            print(f"   • M{unit_id}...", end=" ")
            if self.modulos[unit_id].connect():
                print("✅")
                conectados.append(unit_id)
                self._ler_estado_inicial(unit_id)
            else:
                print("❌")
        
        if conectados:
            print(f"✅ Conectados: {conectados}")
            return True
        else:
            print("❌ Nenhum módulo conectado")
            return False

    def _ler_estado_inicial(self, unit_id):
        """Lê estado inicial de todas as portas do módulo"""
        config = self.configuracoes_modulos[unit_id]
        
        # Lê entradas se o módulo as possui
        if config['tem_entradas']:
            entradas = self.modulos[unit_id].le_status_entradas()
            if entradas:
                self.estados_entradas[unit_id] = entradas
                entradas_ativas = [i+1 for i, x in enumerate(entradas) if x]
                print(f"      📥 Entradas: {entradas_ativas if entradas_ativas else 'Nenhuma'}")
        
        # Lê saídas
        saidas = self.modulos[unit_id].le_status_saidas_digitais()
        if saidas:
            self.estados_saidas[unit_id] = saidas[:config['max_portas']]
            saidas_ativas = [i+1 for i, x in enumerate(saidas[:config['max_portas']]) if x]
            print(f"      📤 Saídas: {saidas_ativas if saidas_ativas else 'Nenhuma'}")

    def parsear_comando(self, comando):
        """Converte comando em (prefixo, modulo, porta)"""
        import re
        
        # Comandos sem ponto: out1, in1, in2
        if "." not in comando:
            match = re.match(r'^([a-z_]+)(\d+)$', comando)
            if match:
                prefixo, modulo_str = match.groups()
                if prefixo in ['out', 'in']:
                    return prefixo, int(modulo_str), None
            return None, None, None
        
        # Comandos com ponto: 1.5, on2.3, all_on.2
        if comando.count('.') == 1:
            parte1, parte2 = comando.split('.')
            
            # Comando direto: "1.5" = toggle módulo 1 porta 5
            if parte1.isdigit():
                return "", int(parte1), int(parte2)
            
            # Comando com prefixo
            match = re.match(r'^([a-z_]+)(\d*)\.(\d+)$', comando)
            if match:
                prefixo, modulo_str, porta_str = match.groups()
                
                if prefixo in ['all_on', 'all_off']:
                    return prefixo, int(porta_str), None
                elif modulo_str:
                    return prefixo, int(modulo_str), int(porta_str)
        
        return None, None, None

    def executar_comando(self, comando):
        """Executa comando do usuário"""
        comando = comando.strip().lower()
        
        # Parse do comando
        cmd_base, modulo, porta = self.parsear_comando(comando)
        
        # Comandos globais
        if cmd_base is None:
            if comando == 'status':
                self.mostrar_status()
                return True
            elif comando == 'help':
                self.mostrar_ajuda()
                return True
            elif comando == 'stats':
                self.mostrar_estatisticas()
                return True
            elif comando in ['quit', 'exit', 'q']:
                self.executando = False
                return True
            else:
                print(f"❌ Comando inválido: '{comando}'. Digite 'help' para ajuda")
                return False
        
        # Valida módulo
        if modulo not in self.modulos_enderecos:
            print(f"❌ Módulo {modulo} não existe. Disponíveis: {self.modulos_enderecos}")
            return False
        
        # Executa comandos específicos
        try:
            return self._executar_comando_modulo(cmd_base, modulo, porta)
        except Exception as e:
            print(f"❌ Erro ao executar comando: {e}")
            return False

    def _executar_comando_modulo(self, cmd_base, modulo, porta):
        """Executa comando específico em um módulo"""
        config = self.configuracoes_modulos[modulo]
        
        # Toggle manual direto: "1.5"
        if cmd_base == "":
            if 1 <= porta <= config['max_portas']:
                if self.modulos[modulo].toggle_canal(porta):
                    print(f"✅ Toggle M{modulo}.S{porta}")
                    self.contadores[modulo]['comandos'] += 1
                    return True
                else:
                    print(f"❌ Erro toggle M{modulo}.S{porta}")
                    return False
        
        # Ligar saída: "on2.3"
        elif cmd_base == "on":
            if 1 <= porta <= config['max_portas']:
                if self.modulos[modulo].liga_canal(porta):
                    print(f"✅ M{modulo}.S{porta} LIGADA")
                    self.contadores[modulo]['comandos'] += 1
                    return True
                else:
                    print(f"❌ Erro ao ligar M{modulo}.S{porta}")
                    return False
        
        # Desligar saída: "off1.12"
        elif cmd_base == "off":
            if 1 <= porta <= config['max_portas']:
                if self.modulos[modulo].desliga_canal(porta):
                    print(f"✅ M{modulo}.S{porta} DESLIGADA")
                    self.contadores[modulo]['comandos'] += 1
                    return True
                else:
                    print(f"❌ Erro ao desligar M{modulo}.S{porta}")
                    return False
        
        # Ligar todas: "all_on.2"
        elif cmd_base == "all_on":
            if self.modulos[modulo].liga_tudo():
                print(f"✅ Todas saídas M{modulo} LIGADAS")
                self.contadores[modulo]['comandos'] += 1
                return True
            else:
                print(f"❌ Erro ao ligar todas M{modulo}")
                return False
        
        # Desligar todas: "all_off.1"
        elif cmd_base == "all_off":
            if self.modulos[modulo].desliga_tudo():
                print(f"✅ Todas saídas M{modulo} DESLIGADAS")
                self.contadores[modulo]['comandos'] += 1
                return True
            else:
                print(f"❌ Erro ao desligar todas M{modulo}")
                return False
        
        # Ler entradas: "in1"
        elif cmd_base == "in":
            if not config['tem_entradas']:
                print(f"❌ M{modulo} não possui entradas")
                return False
            
            entradas = self.modulos[modulo].le_status_entradas()
            if entradas:
                self.estados_entradas[modulo] = entradas
                entradas_ativas = [i+1 for i, x in enumerate(entradas) if x]
                print(f"📥 M{modulo} Entradas: {entradas_ativas if entradas_ativas else 'Nenhuma'}")
                return True
            else:
                print(f"❌ Erro ao ler entradas M{modulo}")
                return False
        
        # Ler saídas: "out1" ou "out1.5"
        elif cmd_base == "out":
            if porta is None:
                # Lê todas as saídas
                saidas = self.modulos[modulo].le_status_saidas_digitais()
                if saidas:
                    self.estados_saidas[modulo] = saidas[:config['max_portas']]
                    saidas_ativas = [i+1 for i, x in enumerate(saidas[:config['max_portas']]) if x]
                    print(f"📤 M{modulo} Saídas: {saidas_ativas if saidas_ativas else 'Nenhuma'}")
                    return True
                else:
                    print(f"❌ Erro ao ler saídas M{modulo}")
                    return False
            else:
                # Lê saída específica
                status = self.modulos[modulo].le_status_saida_especifica(porta)
                if status is not None:
                    estado = "ON" if status else "OFF"
                    print(f"📤 M{modulo}.S{porta}: {estado}")
                    return True
                else:
                    print(f"❌ Erro ao ler saída M{modulo}.S{porta}")
                    return False
        
        # Toggle configuração: "t2.3"
        elif cmd_base == "t":
            if not config['tem_entradas']:
                print(f"❌ M{modulo} não possui entradas")
                return False
            if 1 <= porta <= 16:
                idx = porta - 1
                self.toggle_habilitado[modulo][idx] = not self.toggle_habilitado[modulo][idx]
                status = "HABILITADO" if self.toggle_habilitado[modulo][idx] else "DESABILITADO"
                print(f"✅ Toggle M{modulo}.E{porta}: {status}")
                return True
        
        print(f"❌ Comando não reconhecido: '{cmd_base}'")
        return False

    def processar_toggle_entradas(self, unit_id, entradas_atual, entradas_anterior):
        """Processa toggles automáticos baseados em mudanças nas entradas"""
        toggles_executados = []
        
        for i in range(16):
            # Detecta borda de subida (0→1)
            if entradas_anterior[i] == 0 and entradas_atual[i] == 1:
                canal = i + 1
                if self.toggle_habilitado[unit_id][i]:
                    # Executa toggle na saída correspondente
                    if self.modulos[unit_id].toggle_canal(canal):
                        toggles_executados.append(f"Toggle M{unit_id} E{canal}→S{canal}")
                        self.contadores[unit_id]['toggles'] += 1
                    else:
                        toggles_executados.append(f"ERRO Toggle M{unit_id} E{canal}→S{canal}")
        
        return toggles_executados

    def thread_leitura_geral(self):
        """Thread para leitura periódica de todos os módulos"""
        print("🔄 Thread leitura geral iniciada")
        ciclo = 0
        
        while self.executando:
            try:
                ciclo += 1
                # print(f"\n🔄 Ciclo #{ciclo} - {datetime.now().strftime('%H:%M:%S')}")
                
                with self.locks['modulos']:
                    for unit_id in self.modulos_enderecos:
                        self._ler_modulo(unit_id)
                
                time.sleep(INTERVALO_LEITURA)
                
            except Exception as e:
                print(f"❌ Erro na thread leitura: {e}")
                time.sleep(2)
        
        print("🔄 Thread leitura finalizada")

    def thread_polling_in1(self):
        """Thread específica para polling rápido das entradas do módulo 1"""
        if not POLLING_IN1_ATIVO or 1 not in self.modulos_enderecos:
            return
        
        print("🔄 Polling M1 iniciado")
        
        while self.executando:
            try:
                with self.locks['modulos']:
                    entradas_atual = self.modulos[1].le_status_entradas()
                    if entradas_atual and entradas_atual != self.estado_polling_in1:
                        entradas_ativas = [i+1 for i, x in enumerate(entradas_atual) if x]
                        print(f"🔄 M1 Mudança: {entradas_ativas if entradas_ativas else 'Nenhuma'}")
                        
                        # Processa toggles automáticos
                        toggles = self.processar_toggle_entradas(1, entradas_atual, self.estado_polling_in1)
                        for toggle in toggles:
                            print(f"   {toggle}")
                        
                        self.estado_polling_in1 = entradas_atual[:]
                        self.estados_entradas[1] = entradas_atual[:]
                
                time.sleep(INTERVALO_POLLING_IN1)
                
            except Exception as e:
                print(f"❌ Erro polling M1: {e}")
                time.sleep(1)
        
        print("🔄 Polling M1 finalizado")

    def _ler_modulo(self, unit_id):
        """Lê estado atual de um módulo específico"""
        config = self.configuracoes_modulos[unit_id]
        
        # Lê entradas (se tiver)
        if config['tem_entradas'] and unit_id != 1:  # M1 tem polling próprio
            entradas = self.modulos[unit_id].le_status_entradas()
            if entradas:
                self.estados_entradas[unit_id] = entradas
                self.contadores[unit_id]['leituras'] += 1

    def thread_interface_comandos(self):
        """Thread para capturar comandos do usuário"""
        while self.executando:
            try:
                comando = input().strip()
                if comando:
                    self.executar_comando(comando)
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"❌ Erro na interface: {e}")

    def mostrar_status(self):
        """Mostra status atual de todos os módulos"""
        tempo_execucao = time.time() - self.tempo_inicio
        
        print(f"\n📊 STATUS MULTI-MÓDULO ({datetime.now().strftime('%H:%M:%S')})")
        print("=" * 60)
        
        for unit_id in self.modulos_enderecos:
            config = self.configuracoes_modulos[unit_id]
            print(f"\n🔧 MÓDULO {unit_id}:")
            
            # Entradas
            if config['tem_entradas']:
                entradas_ativas = [i+1 for i, x in enumerate(self.estados_entradas[unit_id]) if x]
                print(f"   📥 Entradas: {entradas_ativas if entradas_ativas else 'Nenhuma'}")
                
                toggle_ativo = [i+1 for i, x in enumerate(self.toggle_habilitado[unit_id]) if x]
                print(f"   🔄 Toggle: {toggle_ativo if toggle_ativo else 'Nenhum'}")
            else:
                print(f"   📥 Entradas: N/A")
            
            # Saídas
            saidas_ativas = [i+1 for i, x in enumerate(self.estados_saidas[unit_id]) if x]
            print(f"   📤 Saídas: {saidas_ativas if saidas_ativas else 'Nenhuma'}")
            
            # Estatísticas
            stats = self.contadores[unit_id]
            print(f"   📈 Stats: L:{stats['leituras']} C:{stats['comandos']} T:{stats['toggles']}")
        
        print(f"\n⏱️  Tempo execução: {tempo_execucao:.1f}s")
        print("=" * 60)

    def mostrar_estatisticas(self):
        """Mostra estatísticas detalhadas de performance"""
        print("\n📊 ESTATÍSTICAS DE PERFORMANCE:")
        print("=" * 50)
        
        for unit_id in self.modulos_enderecos:
            stats = self.modulos[unit_id].get_performance_stats()
            print(f"🔧 MÓDULO {unit_id}:")
            print(f"   • Tentativas conexão: {stats['connection_attempts']}")
            print(f"   • Operações bem-sucedidas: {stats['successful_reads']}")
            print(f"   • Operações falharam: {stats['failed_reads']}")
            print(f"   • Taxa de sucesso: {stats['success_rate']:.1f}%")
            print()

    def mostrar_ajuda(self):
        """Mostra comandos disponíveis"""
        print("\n📋 COMANDOS DISPONÍVEIS:")
        print("┌─────────────────────────────────────────────────────┐")
        print("│ CONTROLE DE SAÍDAS:                                 │")
        print("│   1.5         : Toggle saída 5 do módulo 1         │")
        print("│   on2.3       : Ligar saída 3 do módulo 2          │")
        print("│   off1.12     : Desligar saída 12 do módulo 1      │")
        print("│   all_on.2    : Ligar todas saídas do módulo 2     │")
        print("│   all_off.1   : Desligar todas saídas do módulo 1  │")
        print("├─────────────────────────────────────────────────────┤")
        print("│ LEITURA:                                            │")
        print("│   out1        : Ler todas saídas do módulo 1       │")
        print("│   out1.5      : Ler saída 5 do módulo 1            │")
        print("│   in1         : Ler entradas do módulo 1           │")
        print("├─────────────────────────────────────────────────────┤")
        print("│ CONFIGURAÇÃO:                                       │")
        print("│   t1.3        : Toggle entrada 3 do módulo 1       │")
        print("├─────────────────────────────────────────────────────┤")
        print("│ INFORMAÇÕES:                                        │")
        print("│   status      : Status de todos módulos            │")
        print("│   stats       : Estatísticas de performance        │")
        print("│   help        : Esta ajuda                         │")
        print("│   quit        : Sair                               │")
        print("└─────────────────────────────────────────────────────┘")
        print(f"💡 Módulos: {self.modulos_enderecos}")
        print(f"💡 Gateway: {self.gateway_ip}:{self.gateway_porta}")

    def executar_monitor(self):
        """Inicia o monitor multi-módulo"""
        print("🚀 MONITOR MULTI-MÓDULO - 25IOB16")
        print("=" * 50)
        print("📋 CONFIGURAÇÕES:")
        print(f"   • Gateway: {self.gateway_ip}:{self.gateway_porta}")
        print(f"   • Módulos: {self.modulos_enderecos}")
        print(f"   • Intervalo leitura: {INTERVALO_LEITURA*1000:.0f}ms")
        if POLLING_IN1_ATIVO:
            print(f"   • Polling M1: {INTERVALO_POLLING_IN1*1000:.0f}ms")
        print("=" * 50)
        
        # Conecta aos módulos
        if not self.conectar_todos():
            print("❌ Falha na conexão")
            return
        
        self.tempo_inicio = time.time()
        
        # Inicia threads
        self.threads['comandos'] = threading.Thread(target=self.thread_interface_comandos, daemon=True)
        self.threads['comandos'].start()
        
        self.threads['leitura'] = threading.Thread(target=self.thread_leitura_geral, daemon=True)
        self.threads['leitura'].start()
        
        if POLLING_IN1_ATIVO:
            self.threads['polling_in1'] = threading.Thread(target=self.thread_polling_in1, daemon=True)
            self.threads['polling_in1'].start()
        
        print("\n🔄 Monitor ativo! Digite 'help' para comandos")
        print("💡 Pressione Ctrl+C para parar")
        
        # Loop principal
        try:
            while self.executando:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Interrompido pelo usuário")
        
        # Estatísticas finais
        tempo_total = time.time() - self.tempo_inicio
        total_comandos = sum(stats['comandos'] for stats in self.contadores.values())
        total_toggles = sum(stats['toggles'] for stats in self.contadores.values())
        
        print(f"\n📊 SESSÃO FINALIZADA")
        print(f"   • Tempo total: {tempo_total:.1f}s")
        print(f"   • Comandos executados: {total_comandos}")
        print(f"   • Toggles automáticos: {total_toggles}")

    def desconectar_todos(self):
        """Fecha conexões com todos os módulos"""
        for modulo in self.modulos.values():
            if modulo.client and modulo.client.connected:
                modulo.disconnect()
        print("🔌 Conexões fechadas")

def main():
    """Função principal"""
    print("=" * 50)
    print("🔗 MONITOR MULTI-MÓDULO 25IOB16")
    print("=" * 50)
    
    monitor = MonitorMultiModulo()
    
    try:
        monitor.executar_monitor()
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        monitor.desconectar_todos()
        print("\n👋 Monitor finalizado!")

if __name__ == "__main__":
    main()