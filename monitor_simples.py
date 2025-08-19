#!/usr/bin/env python3
"""
Monitor Simples de Tempo Real - Módulo 25IOB16
Versão simplificada para monitoramento rápido
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import signal
import sys

class MonitorSimples:
    def __init__(self, ip_modbus):
        self.modbus = Modbus25IOB16Pymodbus(ip_modbus)
        self.executando = True
        self.estado_anterior_entradas = None
        self.estado_anterior_saidas = None
        
        # Handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        print("\n🛑 Parando...")
        self.executando = False
    
    def conectar(self):
        if self.modbus.connect():
            print("✅ Conectado!")
            return True
        else:
            print("❌ Falha na conexão!")
            return False
    
    def desconectar(self):
        if self.modbus.client and self.modbus.client.connected:
            self.modbus.disconnect()
    
    def mostrar_mudancas(self, tipo, estado_atual, estado_anterior):
        """Mostra mudanças de estado"""
        if estado_anterior is None:
            return
        
        mudancas = []
        for i in range(16):
            if estado_atual[i] != estado_anterior[i]:
                status = "ON" if estado_atual[i] else "OFF"
                mudancas.append(f"{tipo} {i+1}: {status}")
        
        if mudancas:
            timestamp = time.strftime("%H:%M:%S")
            print(f"\n[{timestamp}] MUDANÇA: {', '.join(mudancas)}")
    
    def monitorar(self):
        print("🚀 Monitor iniciado - 50ms intervalo")
        print("Pressione Ctrl+C para parar")
        print("-" * 40)
        
        # Primeira leitura
        entradas = self.modbus.le_status_entradas()
        saidas = self.modbus.le_status_saidas()
        
        if entradas is None or saidas is None:
            print("❌ Erro na primeira leitura!")
            return
        
        self.estado_anterior_entradas = entradas.copy()
        self.estado_anterior_saidas = saidas.copy()
        
        # Loop principal
        while self.executando:
            try:
                # Lê estados
                entradas_atual = self.modbus.le_status_entradas()
                saidas_atual = self.modbus.le_status_saidas()
                
                if entradas_atual is None or saidas_atual is None:
                    continue
                
                # Verifica mudanças
                self.mostrar_mudancas("Entrada", entradas_atual, self.estado_anterior_entradas)
                self.mostrar_mudancas("Saída", saidas_atual, self.estado_anterior_saidas)
                
                # Atualiza estados anteriores
                if entradas_atual != self.estado_anterior_entradas:
                    self.estado_anterior_entradas = entradas_atual.copy()
                if saidas_atual != self.estado_anterior_saidas:
                    self.estado_anterior_saidas = saidas_atual.copy()
                
                # Aguarda 50ms
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(0.1)

def main():
    ip_modbus = "10.0.2.218"
    
    print("🔍 MONITOR SIMPLES - 25IOB16")
    print("=" * 40)
    
    monitor = MonitorSimples(ip_modbus)
    
    try:
        if monitor.conectar():
            monitor.monitorar()
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        monitor.desconectar()
        print("👋 Finalizado!")

if __name__ == "__main__":
    main()
