#!/usr/bin/env python3
"""
Monitor de Tempo Real para Entradas e Saídas do Módulo 25IOB16
Monitora continuamente o estado das entradas e saídas com intervalo de 50ms
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import signal
import sys
from datetime import datetime

class MonitorTempoReal:
    def __init__(self, ip_modbus):
        self.modbus = Modbus25IOB16Pymodbus(ip_modbus)
        self.executando = True
        self.estado_anterior_entradas = None
        self.estado_anterior_saidas = None
        self.contador_leituras = 0
        self.ultima_mudanca = time.time()
        
        # Configura handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handler para Ctrl+C"""
        print("\n🛑 Interrompendo monitoramento...")
        self.executando = False
    
    def conectar(self):
        """Estabelece conexão com o módulo"""
        print("🔌 Conectando ao módulo 25IOB16...")
        if self.modbus.connect():
            print("✅ Conectado com sucesso!")
            return True
        else:
            print("❌ Falha na conexão!")
            return False
    
    def desconectar(self):
        """Fecha conexão com o módulo"""
        if self.modbus.client and self.modbus.client.connected:
            self.modbus.disconnect()
            print("🔌 Conexão fechada")
    
    def formatar_tempo(self):
        """Formata timestamp atual"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def mostrar_mudancas_entradas(self, entradas_atual, entradas_anterior):
        """Mostra mudanças nas entradas"""
        if entradas_anterior is None:
            return
        
        mudancas = []
        for i in range(16):
            if entradas_atual[i] != entradas_anterior[i]:
                status = "🟢 ON" if entradas_atual[i] else "⚪ OFF"
                mudancas.append(f"Entrada {i+1:2d}: {status}")
        
        if mudancas:
            print(f"\n🔍 MUDANÇA NAS ENTRADAS ({self.formatar_tempo()}):")
            for mudanca in mudancas:
                print(f"  {mudanca}")
    
    def mostrar_mudancas_saidas(self, saidas_atual, saidas_anterior):
        """Mostra mudanças nas saídas"""
        if saidas_anterior is None:
            return
        
        mudancas = []
        for i in range(16):
            if saidas_atual[i] != saidas_anterior[i]:
                status = "🟢 ON" if saidas_atual[i] else "⚪ OFF"
                mudancas.append(f"Saída {i+1:2d}: {status}")
        
        if mudancas:
            print(f"\n🔧 MUDANÇA NAS SAÍDAS ({self.formatar_tempo()}):")
            for mudanca in mudancas:
                print(f"  {mudanca}")
    
    def mostrar_status_completo(self, entradas, saidas):
        """Mostra status completo das entradas e saídas"""
        print(f"\n📊 STATUS COMPLETO ({self.formatar_tempo()}) - Leitura #{self.contador_leituras}")
        
        # Status das entradas
        print("🔍 ENTRADAS:")
        entradas_ativas = []
        for i, status in enumerate(entradas):
            if status:
                entradas_ativas.append(i+1)
            print(f"  {i+1:2d}: {'🟢' if status else '⚪'}", end=" ")
            if (i + 1) % 8 == 0:
                print()  # Nova linha a cada 8 entradas
        
        if not entradas_ativas:
            print("  ⚪ Todas desativadas")
        else:
            print(f"  🟢 Ativas: {entradas_ativas}")
        
        # Status das saídas
        print("\n🔧 SAÍDAS:")
        saidas_ativas = []
        for i, status in enumerate(saidas):
            if status:
                saidas_ativas.append(i+1)
            print(f"  {i+1:2d}: {'🟢' if status else '⚪'}", end=" ")
            if (i + 1) % 8 == 0:
                print()  # Nova linha a cada 8 saídas
        
        if not saidas_ativas:
            print("  ⚪ Todas desativadas")
        else:
            print(f"  🟢 Ativas: {saidas_ativas}")
    
    def monitorar(self):
        """Loop principal de monitoramento"""
        print("🚀 Iniciando monitoramento em tempo real...")
        print("📋 Configuração:")
        print("   • Intervalo: 50ms (20 leituras/segundo)")
        print("   • Entradas: 16 canais digitais")
        print("   • Saídas: 16 canais digitais")
        print("   • Pressione Ctrl+C para parar")
        print("-" * 60)
        
        # Primeira leitura para estabelecer estado inicial
        print("📡 Fazendo primeira leitura...")
        entradas = self.modbus.le_status_entradas()
        saidas = self.modbus.le_status_saidas()
        
        if entradas is None or saidas is None:
            print("❌ Erro na primeira leitura!")
            return
        
        self.estado_anterior_entradas = entradas.copy()
        self.estado_anterior_saidas = saidas.copy()
        
        # Mostra status inicial
        self.mostrar_status_completo(entradas, saidas)
        print("\n🔄 Iniciando monitoramento contínuo...")
        
        # Loop principal
        while self.executando:
            try:
                # Lê estados atuais
                entradas_atual = self.modbus.le_status_entradas()
                saidas_atual = self.modbus.le_status_saidas()
                
                if entradas_atual is None or saidas_atual is None:
                    print(f"⚠️  Erro na leitura #{self.contador_leituras + 1}, tentando novamente...")
                    time.sleep(0.1)
                    continue
                
                self.contador_leituras += 1
                
                # Verifica mudanças nas entradas
                if entradas_atual != self.estado_anterior_entradas:
                    self.mostrar_mudancas_entradas(entradas_atual, self.estado_anterior_entradas)
                    self.estado_anterior_entradas = entradas_atual.copy()
                    self.ultima_mudanca = time.time()
                
                # Verifica mudanças nas saídas
                if saidas_atual != self.estado_anterior_saidas:
                    self.mostrar_mudancas_saidas(saidas_atual, self.estado_anterior_saidas)
                    self.estado_anterior_saidas = saidas_atual.copy()
                    self.ultima_mudanca = time.time()
                
                # Mostra status a cada 100 leituras (5 segundos)
                if self.contador_leituras % 100 == 0:
                    self.mostrar_status_completo(entradas_atual, saidas_atual)
                    
                    # Estatísticas
                    tempo_sem_mudanca = time.time() - self.ultima_mudanca
                    print(f"📈 Estatísticas:")
                    print(f"   • Total de leituras: {self.contador_leituras}")
                    print(f"   • Tempo sem mudanças: {tempo_sem_mudanca:.1f}s")
                    print(f"   • Taxa de leitura: {self.contador_leituras / (time.time() - self.ultima_mudanca + 1):.1f} Hz")
                
                # Aguarda próximo ciclo (50ms)
                time.sleep(0.05)
                
            except Exception as e:
                print(f"❌ Erro durante monitoramento: {e}")
                time.sleep(0.1)
        
        # Estatísticas finais
        print(f"\n📊 MONITORAMENTO FINALIZADO")
        print(f"   • Total de leituras: {self.contador_leituras}")
        print(f"   • Tempo total: {(time.time() - self.ultima_mudanca + 1):.1f}s")

def main():
    """Função principal"""
    ip_modbus = "10.0.2.218"  # Ajuste conforme necessário
    
    print("=" * 60)
    print("🔍 MONITOR DE TEMPO REAL - MÓDULO 25IOB16")
    print("=" * 60)
    
    monitor = MonitorTempoReal(ip_modbus)
    
    try:
        if monitor.conectar():
            monitor.monitorar()
        else:
            print("❌ Não foi possível conectar ao módulo")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        monitor.desconectar()
        print("\n👋 Monitoramento finalizado!")

if __name__ == "__main__":
    main()
