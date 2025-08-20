#!/usr/bin/env python3
"""
Mapeamento Simples: Entradas → Saídas
Versão simplificada para mapeamento automático 1:1
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import signal

class MapeamentoSimples:
    def __init__(self, ip_modbus):
        self.modbus = Modbus25IOB16Pymodbus(ip_modbus)
        self.executando = True
        self.estado_anterior = None
        
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
    
    def executar_mapeamento(self, entradas):
        """Executa mapeamento 1:1 das entradas para saídas"""
        for i in range(16):
            entrada_num = i + 1
            saida_num = i + 1
            estado = entradas[i]
            
            if estado:  # Entrada ON
                self.modbus.liga_canal(saida_num)
            else:  # Entrada OFF
                self.modbus.desliga_canal(saida_num)
    
    def monitorar_e_mapear(self):
        """Monitora entradas e mapeia para saídas"""
        print("🚀 Mapeamento automático iniciado - 50ms intervalo")
        print("Pressione Ctrl+C para parar")
        print("-" * 40)
        
        # Primeira leitura
        entradas = self.modbus.le_status_entradas()
        if entradas is None:
            print("❌ Erro na primeira leitura!")
            return
        
        self.estado_anterior = entradas.copy()
        
        # Aplica mapeamento inicial
        self.executar_mapeamento(entradas)
        print(f"📡 Estado inicial aplicado: {entradas}")
        
        # Loop principal
        while self.executando:
            try:
                # Lê entradas
                entradas_atual = self.modbus.le_status_entradas()
                if entradas_atual is None:
                    continue
                
                # Verifica mudanças
                if entradas_atual != self.estado_anterior:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"\n[{timestamp}] MUDANÇA DETECTADA!")
                    
                    # Mostra mudanças
                    for i in range(16):
                        if entradas_atual[i] != self.estado_anterior[i]:
                            status = "ON" if entradas_atual[i] else "OFF"
                            print(f"  Entrada {i+1}: {status}")
                    
                    # Executa mapeamento
                    self.executar_mapeamento(entradas_atual)
                    print(f"  Mapeamento aplicado: {entradas_atual}")
                    
                    # Atualiza estado anterior
                    self.estado_anterior = entradas_atual.copy()
                
                # Aguarda 50ms
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Erro: {e}")
                time.sleep(0.1)

def main():
    ip_modbus = "10.0.2.218"
    
    print("🔗 MAPEAMENTO SIMPLES - 25IOB16")
    print("=" * 40)
    
    mapeador = MapeamentoSimples(ip_modbus)
    
    try:
        if mapeador.conectar():
            mapeador.monitorar_e_mapear()
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        mapeador.desconectar()
        print("👋 Finalizado!")

if __name__ == "__main__":
    main()
