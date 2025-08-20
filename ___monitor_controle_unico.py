#!/usr/bin/env python3
"""
Monitor e Controle Módulo Único - 25IOB16
Versão simplificada para uso com apenas um módulo físico
- Leitura contínua I/O a cada 50ms
- Controle manual das saídas via comandos simples
- Toggle por software nas entradas (detecção de bordas)
- Endereçamento simples: 1-16 (sem hierarquia)

CONFIGURAÇÕES HARDCODED:
- Gateway IP: 10.0.2.218
- Porta: 502
- Módulo: unit_id detectado automaticamente

COMANDOS SIMPLES:
- 1-16: Toggle manual de saída
- t1-t16: Ativar/desativar toggle entrada
- on1-on16: Ligar saída específica
- off1-off16: Desligar saída específica
- all_on/all_off: Controlar todas saídas
- status: Mostrar estado
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

class MonitorModuloUnico:
    def __init__(self):
        # CONFIGURAÇÕES HARDCODED DO AMBIENTE
        self.gateway_ip = "10.0.2.218"      # IP do gateway WAVESHARE
        self.gateway_porta = 502            # Porta Modbus TCP
        self.unit_id_candidatos = [1, 2, 3, 4]  # Possíveis unit_ids para detectar
        self.unit_id = None                 # unit_id detectado automaticamente
        self.modbus = None
        
        self.executando = True
        
        # Estados das I/O
        self.estado_anterior_entradas = [0] * 16
        self.estado_atual_entradas = [0] * 16
        self.estado_atual_saidas = [0] * 16
        
        # Configurações de toggle por software
        self.toggle_habilitado = [False] * 16
        self.estado_toggle_saidas = [False] * 16
        
        # Estatísticas
        self.contador_leituras = 0
        self.contador_comandos = 0
        self.contador_toggles = 0
        self.tempo_inicio = time.time()
        
        # Configurações
        self.intervalo_leitura = 0.05  # 50ms
        
        # Thread de comandos
        self.thread_comandos = None
        
        # Configura handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Detecta módulo automaticamente
        self._detectar_modulo()
    
    def _detectar_modulo(self):
        """Detecta automaticamente qual unit_id está ativo"""
        print("🔍 Detectando módulo 25IOB16...")
        
        for unit_id in self.unit_id_candidatos:
            print(f"   • Testando unit_id {unit_id}...", end=" ")
            
            # Cria conexão temporária
            modbus_temp = Modbus25IOB16Pymodbus(self.gateway_ip, self.gateway_porta, unit_id)
            
            try:
                if modbus_temp.connect():
                    # Testa leitura de um registrador conhecido (entradas)
                    entradas = modbus_temp.le_status_entradas()
                    if entradas is not None:
                        print("✅ ENCONTRADO")
                        self.unit_id = unit_id
                        self.modbus = Modbus25IOB16Pymodbus(self.gateway_ip, self.gateway_porta, unit_id)
                        modbus_temp.disconnect()
                        break
                    else:
                        print("❌ SEM RESPOSTA")
                else:
                    print("❌ CONEXÃO FALHOU")
            except Exception as e:
                print(f"❌ ERRO: {e}")
            finally:
                modbus_temp.disconnect()
        
        if self.unit_id is None:
            print("❌ Nenhum módulo detectado!")
            print("   Verifique:")
            print("   • Módulo energizado")
            print("   • Conexão RS485 (A/B)")
            print("   • Gateway funcionando")
            print("   • unit_id configurado (1, 2, 3 ou 4)")
        else:
            print(f"✅ Módulo detectado: unit_id = {self.unit_id}")
    
    def signal_handler(self, sig, frame):
        """Handler para Ctrl+C"""
        print("\n🛑 Interrompendo monitor...")
        self.executando = False
        if self.thread_comandos and self.thread_comandos.is_alive():
            self.thread_comandos.join(timeout=1)
    
    def conectar(self):
        """Estabelece conexão com o módulo"""
        if self.unit_id is None:
            print("❌ Nenhum módulo foi detectado!")
            return False
            
        print(f"🔌 Conectando ao módulo unit_id {self.unit_id}...")
        if self.modbus.connect():
            print("✅ Conectado com sucesso!")
            return True
        else:
            print("❌ Falha na conexão!")
            return False
    
    def desconectar(self):
        """Fecha conexão com o módulo"""
        if self.modbus and self.modbus.client and self.modbus.client.connected:
            self.modbus.disconnect()
        print("🔌 Conexão fechada")
    
    def formatar_tempo(self):
        """Formata timestamp atual"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def detectar_bordas_entradas(self, entradas_atual, entradas_anterior):
        """Detecta bordas de subida (LOW→HIGH) nas entradas"""
        bordas_subida = []
        
        for i in range(16):
            # Borda de subida: anterior=0, atual=1
            if entradas_anterior[i] == 0 and entradas_atual[i] == 1:
                bordas_subida.append(i + 1)  # Canal 1-16
        
        return bordas_subida
    
    def processar_toggle_entradas(self, bordas_subida):
        """Processa toggles nas entradas com bordas de subida detectadas"""
        comandos_executados = []
        
        for canal in bordas_subida:
            idx = canal - 1  # Índice 0-15
            
            # Verifica se toggle está habilitado para este canal
            if self.toggle_habilitado[idx]:
                # Inverte estado do toggle
                self.estado_toggle_saidas[idx] = not self.estado_toggle_saidas[idx]
                
                # Executa comando no hardware
                if self.estado_toggle_saidas[idx]:
                    sucesso = self.modbus.liga_canal(canal)
                    acao = "ON"
                else:
                    sucesso = self.modbus.desliga_canal(canal)
                    acao = "OFF"
                
                if sucesso:
                    comandos_executados.append(f"Toggle E{canal}→S{canal}: {acao}")
                    self.contador_toggles += 1
                else:
                    comandos_executados.append(f"Toggle E{canal}→S{canal}: ERRO")
        
        return comandos_executados
    
    def executar_comando(self, comando):
        """Executa comando manual do usuário"""
        comando = comando.strip().lower()
        
        try:
            # Comandos de toggle manual (1-16)
            if comando.isdigit() and 1 <= int(comando) <= 16:
                canal = int(comando)
                if self.modbus.toggle_canal(canal):
                    print(f"✅ Toggle manual S{canal} executado")
                    self.contador_comandos += 1
                    return True
                else:
                    print(f"❌ Erro no toggle S{canal}")
                    return False
            
            # Comandos de controle toggle (t1-t16)
            elif comando.startswith('t') and len(comando) <= 3:
                canal_str = comando[1:]
                if canal_str.isdigit() and 1 <= int(canal_str) <= 16:
                    canal = int(canal_str)
                    idx = canal - 1
                    self.toggle_habilitado[idx] = not self.toggle_habilitado[idx]
                    status = "HABILITADO" if self.toggle_habilitado[idx] else "DESABILITADO"
                    print(f"✅ Toggle entrada E{canal}: {status}")
                    return True
            
            # Comandos liga (on1-on16)
            elif comando.startswith('on') and len(comando) <= 4:
                canal_str = comando[2:]
                if canal_str.isdigit() and 1 <= int(canal_str) <= 16:
                    canal = int(canal_str)
                    if self.modbus.liga_canal(canal):
                        print(f"✅ Saída S{canal} LIGADA")
                        self.contador_comandos += 1
                        return True
                    else:
                        print(f"❌ Erro ao ligar S{canal}")
                        return False
            
            # Comandos desliga (off1-off16)
            elif comando.startswith('off') and len(comando) <= 5:
                canal_str = comando[3:]
                if canal_str.isdigit() and 1 <= int(canal_str) <= 16:
                    canal = int(canal_str)
                    if self.modbus.desliga_canal(canal):
                        print(f"✅ Saída S{canal} DESLIGADA")
                        self.contador_comandos += 1
                        return True
                    else:
                        print(f"❌ Erro ao desligar S{canal}")
                        return False
            
            # Comandos especiais
            elif comando == 'all_on':
                if self.modbus.liga_tudo():
                    print("✅ Todas as saídas LIGADAS")
                    self.contador_comandos += 1
                    return True
                else:
                    print("❌ Erro ao ligar todas saídas")
                    return False
            
            elif comando == 'all_off':
                if self.modbus.desliga_tudo():
                    print("✅ Todas as saídas DESLIGADAS")
                    self.contador_comandos += 1
                    return True
                else:
                    print("❌ Erro ao desligar todas saídas")
                    return False
            
            elif comando == 'status':
                self.mostrar_status_detalhado()
                return True
            
            elif comando == 'help':
                self.mostrar_ajuda()
                return True
            
            elif comando in ['quit', 'exit', 'q']:
                print("👋 Saindo do monitor...")
                self.executando = False
                return True
            
            else:
                print(f"❌ Comando inválido: '{comando}'. Digite 'help' para ajuda.")
                return False
                
        except ValueError:
            print(f"❌ Comando mal formado: '{comando}'. Digite 'help' para ajuda.")
            return False
        except Exception as e:
            print(f"❌ Erro ao executar comando: {e}")
            return False
    
    def mostrar_ajuda(self):
        """Mostra ajuda dos comandos disponíveis"""
        print("\n📋 COMANDOS DISPONÍVEIS:")
        print("┌─────────────────────────────────────────────────────────┐")
        print("│ CONTROLE DE SAÍDAS:                                     │")
        print("│   1-16        : Toggle manual de saída (S1-S16)        │")
        print("│   on1-on16    : Ligar saída específica                 │")
        print("│   off1-off16  : Desligar saída específica              │")
        print("│   all_on      : Ligar todas as saídas                  │")
        print("│   all_off     : Desligar todas as saídas               │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ CONFIGURAÇÃO TOGGLE:                                    │")
        print("│   t1-t16      : Ativar/desativar toggle entrada        │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ INFORMAÇÕES:                                            │")
        print("│   status      : Mostrar estado detalhado               │")
        print("│   help        : Mostrar esta ajuda                     │")
        print("│   quit        : Sair do programa                       │")
        print("└─────────────────────────────────────────────────────────┘")
        print(f"💡 Módulo: unit_id {self.unit_id}")
        print(f"💡 Gateway: {self.gateway_ip}:{self.gateway_porta}")
    
    def thread_interface_comandos(self):
        """Thread para interface de comandos em background"""
        while self.executando:
            try:
                comando = input().strip()
                if comando:
                    self.executar_comando(comando)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️ Erro na interface: {e}")
    
    def mostrar_status_detalhado(self):
        """Mostra status detalhado do sistema"""
        tempo_execucao = time.time() - self.tempo_inicio
        
        print(f"\n📊 STATUS DETALHADO ({self.formatar_tempo()})")
        print("=" * 60)
        
        # Estados das entradas
        entradas_ativas = [i+1 for i, x in enumerate(self.estado_atual_entradas) if x]
        print(f"🔍 ENTRADAS: {entradas_ativas if entradas_ativas else 'Nenhuma ativa'}")
        
        # Estados das saídas
        saidas_ativas = [i+1 for i, x in enumerate(self.estado_atual_saidas) if x]
        print(f"🔧 SAÍDAS: {saidas_ativas if saidas_ativas else 'Nenhuma ativa'}")
        
        # Toggle habilitado
        toggle_ativo = [i+1 for i, x in enumerate(self.toggle_habilitado) if x]
        print(f"🔄 TOGGLE HABILITADO: {toggle_ativo if toggle_ativo else 'Nenhum'}")
        
        # Estatísticas
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"   • Módulo: unit_id {self.unit_id}")
        print(f"   • Leituras: {self.contador_leituras}")
        print(f"   • Comandos manuais: {self.contador_comandos}")
        print(f"   • Toggles executados: {self.contador_toggles}")
        print(f"   • Tempo execução: {tempo_execucao:.1f}s")
        print(f"   • Taxa de leitura: {self.contador_leituras / tempo_execucao:.1f} Hz")
        print("=" * 60)
    
    def mostrar_mudancas(self, entradas_atual, saidas_atual, bordas_subida, toggles_executados):
        """Mostra mudanças detectadas nas I/O"""
        timestamp = self.formatar_tempo()
        
        print(f"\n⚡ MUDANÇAS DETECTADAS [{timestamp}]")
        
        # Mudanças nas entradas
        if bordas_subida:
            print(f"   🔍 Bordas ↗️: E{bordas_subida}")
        
        # Toggles executados
        if toggles_executados:
            for toggle in toggles_executados:
                print(f"   🔄 {toggle}")
        
        # Estados atuais
        entradas_ativas = [i+1 for i, x in enumerate(entradas_atual) if x]
        saidas_ativas = [i+1 for i, x in enumerate(saidas_atual) if x]
        
        print(f"   📊 E: {entradas_ativas if entradas_ativas else '□'} | S: {saidas_ativas if saidas_ativas else '□'}")
    
    def executar_ciclo_leitura(self):
        """Executa um ciclo completo de leitura e processamento"""
        try:
            # 1. Lê estado atual das entradas
            entradas_atual = self.modbus.le_status_entradas()
            if entradas_atual is None:
                print(f"⚠️ Erro ao ler entradas no ciclo #{self.contador_leituras + 1}")
                return False
            
            # 2. Lê estado atual das saídas
            saidas_digitais = self.modbus.le_status_saidas_digitais()
            if saidas_digitais is None:
                print(f"⚠️ Erro ao ler saídas no ciclo #{self.contador_leituras + 1}")
                return False
            
            # 3. Detecta bordas de subida nas entradas
            bordas_subida = self.detectar_bordas_entradas(entradas_atual, self.estado_anterior_entradas)
            
            # 4. Processa toggles por software
            toggles_executados = []
            if bordas_subida:
                toggles_executados = self.processar_toggle_entradas(bordas_subida)
            
            # 5. Verifica mudanças
            mudou_entradas = entradas_atual != self.estado_anterior_entradas
            mudou_saidas = saidas_digitais != self.estado_atual_saidas
            
            # 6. Mostra mudanças se houver
            if mudou_entradas or mudou_saidas or toggles_executados:
                self.mostrar_mudancas(entradas_atual, saidas_digitais, bordas_subida, toggles_executados)
            
            # 7. Atualiza estados
            self.estado_anterior_entradas = entradas_atual.copy()
            self.estado_atual_entradas = entradas_atual.copy()
            self.estado_atual_saidas = saidas_digitais.copy()
            
            # 8. Atualiza contador
            self.contador_leituras += 1
            
            return True
            
        except Exception as e:
            print(f"❌ Erro no ciclo #{self.contador_leituras + 1}: {e}")
            return False
    
    def executar_monitor(self):
        """Executa o monitor completo"""
        print("🚀 MONITOR MÓDULO ÚNICO - 25IOB16")
        print("=" * 60)
        print("📋 CONFIGURAÇÕES:")
        print(f"   • Gateway: {self.gateway_ip}:{self.gateway_porta}")
        print(f"   • Módulo: unit_id {self.unit_id}")
        print(f"   • Intervalo: {self.intervalo_leitura * 1000:.0f}ms")
        print("=" * 60)
        
        # Primeira leitura para estabelecer estado inicial
        print("📡 Fazendo primeira leitura...")
        entradas = self.modbus.le_status_entradas()
        saidas = self.modbus.le_status_saidas_digitais()
        
        if entradas is None or saidas is None:
            print("❌ Erro na primeira leitura!")
            return
        
        # Inicializa estados
        self.estado_anterior_entradas = entradas.copy()
        self.estado_atual_entradas = entradas.copy()
        self.estado_atual_saidas = saidas.copy()
        self.tempo_inicio = time.time()
        
        # Inicia thread de comandos
        print("⌨️ Iniciando interface de comandos...")
        self.thread_comandos = threading.Thread(target=self.thread_interface_comandos, daemon=True)
        self.thread_comandos.start()
        
        # Mostra estado inicial
        entradas_ativas = [i+1 for i, x in enumerate(entradas) if x]
        saidas_ativas = [i+1 for i, x in enumerate(saidas) if x]
        print(f"📊 ESTADO INICIAL - E: {entradas_ativas if entradas_ativas else '□'} | S: {saidas_ativas if saidas_ativas else '□'}")
        
        print("\n🔄 Monitor ativo! Digite comandos ou 'help' para ajuda")
        print("   💡 Pressione Ctrl+C para parar")
        
        # Loop principal de monitoramento
        while self.executando:
            try:
                # Executa ciclo de leitura e processamento
                sucesso = self.executar_ciclo_leitura()
                
                if not sucesso:
                    print(f"⚠️ Ciclo #{self.contador_leituras + 1} falhou, tentando novamente...")
                
                # Aguarda próximo ciclo
                time.sleep(self.intervalo_leitura)
                
            except KeyboardInterrupt:
                print("\n🛑 Interrupção via Ctrl+C")
                break
            except Exception as e:
                print(f"❌ Erro durante execução: {e}")
                time.sleep(0.1)
        
        # Estatísticas finais
        tempo_total = time.time() - self.tempo_inicio
        print(f"\n📊 MONITOR FINALIZADO")
        print(f"   • Leituras: {self.contador_leituras}")
        print(f"   • Comandos executados: {self.contador_comandos}")
        print(f"   • Toggles por software: {self.contador_toggles}")
        print(f"   • Tempo total: {tempo_total:.1f}s")
        print(f"   • Taxa média: {self.contador_leituras / tempo_total:.1f} Hz")

def main():
    """Função principal"""
    print("=" * 60)
    print("🔗 MONITOR MÓDULO ÚNICO - 25IOB16")
    print("   Detecção Automática + Controle Simples")
    print("=" * 60)
    
    monitor = MonitorModuloUnico()
    
    try:
        # Verifica se encontrou módulo na detecção
        if monitor.unit_id is None:
            print("❌ Nenhum módulo foi detectado!")
            print("\n🔍 SOLUÇÃO:")
            print("   1. Verifique se o módulo está energizado")
            print("   2. Confirme conexão RS485 (A/B)")
            print("   3. Verifique unit_id configurado no módulo (1-4)")
            print("   4. Teste gateway com outro software")
            return
            
        if monitor.conectar():
            monitor.executar_monitor()
        else:
            print("❌ Falha na conexão com o módulo")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        monitor.desconectar()
        print("\n👋 Monitor finalizado!")

if __name__ == "__main__":
    main()