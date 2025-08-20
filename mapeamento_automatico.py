#!/usr/bin/env python3
"""
Mapeamento Automático: 16 Entradas → 16 Saídas
Mapeia automaticamente cada entrada para sua saída correspondente
Input: Switch (sem pulso) - Output: Estado correspondente
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import signal
import sys
from datetime import datetime

class MapeamentoAutomatico:
    def __init__(self, ip_modbus):
        self.modbus = Modbus25IOB16Pymodbus(ip_modbus)
        self.executando = True
        self.estado_anterior_entradas = None
        self.contador_ciclos = 0
        self.contador_acoes = 0
        
        # Configura handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handler para Ctrl+C"""
        print("\n🛑 Interrompendo mapeamento automático...")
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
    
    def mapear_entrada_para_saida(self, entrada, saida):
        """Mapeia uma entrada específica para sua saída correspondente"""
        try:
            if entrada:  # Se entrada está ON
                # Liga a saída correspondente
                if self.modbus.liga_canal(saida):
                    return True, "ON"
                else:
                    return False, "ERRO_LIGAR"
            else:  # Se entrada está OFF
                # Desliga a saída correspondente
                if self.modbus.desliga_canal(saida):
                    return True, "OFF"
                else:
                    return False, "ERRO_DESLIGAR"
        except Exception as e:
            return False, f"EXCEÇÃO: {e}"
    
    def executar_mapeamento(self, entradas_atual):
        """Executa o mapeamento de todas as entradas para saídas"""
        acoes_executadas = []
        
        for i in range(16):
            entrada_num = i + 1
            saida_num = i + 1
            estado_entrada = entradas_atual[i]
            
            # Mapeia entrada → saída
            sucesso, resultado = self.mapear_entrada_para_saida(estado_entrada, saida_num)
            
            if sucesso:
                acoes_executadas.append(f"E{entrada_num}→S{saida_num}: {resultado}")
            else:
                acoes_executadas.append(f"E{entrada_num}→S{saida_num}: {resultado}")
        
        return acoes_executadas
    
    def mostrar_status_mapeamento(self, entradas, saidas, acoes_executadas):
        """Mostra o status do mapeamento"""
        print(f"\n📊 MAPEAMENTO AUTOMÁTICO ({self.formatar_tempo()}) - Ciclo #{self.contador_ciclos}")
        
        # Status das entradas
        print("🔍 ENTRADAS (Switches):")
        entradas_ativas = []
        for i, status in enumerate(entradas):
            if status:
                entradas_ativas.append(i+1)
            print(f"  {i+1:2d}: {'🟢' if status else '⚪'}", end=" ")
            if (i + 1) % 8 == 0:
                print()
        
        if not entradas_ativas:
            print("  ⚪ Todas desativadas")
        else:
            print(f"  🟢 Ativas: {entradas_ativas}")
        
        # Status das saídas
        print("\n🔧 SAÍDAS (Mapeadas):")
        saidas_ativas = []
        for i, status in enumerate(saidas):
            if status:
                saidas_ativas.append(i+1)
            print(f"  {i+1:2d}: {'🟢' if status else '⚪'}", end=" ")
            if (i + 1) % 8 == 0:
                print()
        
        if not saidas_ativas:
            print("  ⚪ Todas desativadas")
        else:
            print(f"  🟢 Ativas: {saidas_ativas}")
        
        # Ações executadas
        if acoes_executadas:
            print(f"\n⚡ AÇÕES EXECUTADAS ({len(acoes_executadas)}):")
            for acao in acoes_executadas:
                print(f"  {acao}")
        
        # Estatísticas
        print(f"\n📈 ESTATÍSTICAS:")
        print(f"   • Total de ciclos: {self.contador_ciclos}")
        print(f"   • Total de ações: {self.contador_acoes}")
        print(f"   • Taxa de execução: {self.contador_ciclos / (time.time() - self.tempo_inicio + 1):.1f} Hz")
    
    def executar_ciclo_mapeamento(self):
        """Executa um ciclo completo de mapeamento"""
        try:
            # 1. Lê estado atual das entradas
            entradas_atual = self.modbus.le_status_entradas()
            if entradas_atual is None:
                print(f"⚠️  Erro ao ler entradas no ciclo #{self.contador_ciclos + 1}")
                return False
            
            # 2. Lê estado atual das saídas (para comparação)
            saidas_atual = self.modbus.le_status_saidas()
            if saidas_atual is None:
                print(f"⚠️  Erro ao ler saídas no ciclo #{self.contador_ciclos + 1}")
                return False
            
            # 3. Verifica se houve mudança nas entradas
            if entradas_atual != self.estado_anterior_entradas:
                print(f"\n🔄 MUDANÇA DETECTADA no ciclo #{self.contador_ciclos + 1}")
                
                # 4. Executa mapeamento automático
                acoes_executadas = self.executar_mapeamento(entradas_atual)
                
                # 5. Atualiza contadores
                self.contador_acoes += len(acoes_executadas)
                
                # 6. Mostra status detalhado
                self.mostrar_status_mapeamento(entradas_atual, saidas_atual, acoes_executadas)
                
                # 7. Atualiza estado anterior
                self.estado_anterior_entradas = entradas_atual.copy()
                
                return True
            else:
                # Sem mudanças - mostra status a cada 100 ciclos
                if self.contador_ciclos % 100 == 0:
                    self.mostrar_status_mapeamento(entradas_atual, saidas_atual, [])
                
                return True
                
        except Exception as e:
            print(f"❌ Erro no ciclo #{self.contador_ciclos + 1}: {e}")
            return False
    
    def executar_mapeamento_continuo(self):
        """Executa mapeamento automático contínuo"""
        print("🚀 Iniciando Mapeamento Automático: 16 Entradas → 16 Saídas")
        print("📋 Configuração:")
        print("   • Mapeamento: 1:1 (Entrada N → Saída N)")
        print("   • Tipo de Input: Switch (sem pulso)")
        print("   • Ciclo de execução: 50ms")
        print("   • Lógica: ON/OFF direto")
        print("   • Pressione Ctrl+C para parar")
        print("-" * 70)
        
        # Primeira leitura para estabelecer estado inicial
        print("📡 Fazendo primeira leitura...")
        entradas = self.modbus.le_status_entradas()
        saidas = self.modbus.le_status_saidas()
        
        if entradas is None or saidas is None:
            print("❌ Erro na primeira leitura!")
            return
        
        self.estado_anterior_entradas = entradas.copy()
        self.tempo_inicio = time.time()
        
        # Mostra status inicial
        print("📊 ESTADO INICIAL:")
        self.mostrar_status_mapeamento(entradas, saidas, [])
        print("\n🔄 Iniciando mapeamento automático contínuo...")
        
        # Loop principal
        while self.executando:
            try:
                # Executa ciclo de mapeamento
                sucesso = self.executar_ciclo_mapeamento()
                
                if sucesso:
                    self.contador_ciclos += 1
                else:
                    print(f"⚠️  Ciclo #{self.contador_ciclos + 1} falhou, tentando novamente...")
                
                # Aguarda próximo ciclo (50ms)
                time.sleep(0.05)
                
            except Exception as e:
                print(f"❌ Erro durante execução: {e}")
                time.sleep(0.1)
        
        # Estatísticas finais
        tempo_total = time.time() - self.tempo_inicio
        print(f"\n📊 MAPEAMENTO FINALIZADO")
        print(f"   • Total de ciclos: {self.contador_ciclos}")
        print(f"   • Total de ações: {self.contador_acoes}")
        print(f"   • Tempo total: {tempo_total:.1f}s")
        print(f"   • Taxa média: {self.contador_ciclos / tempo_total:.1f} Hz")

def main():
    """Função principal"""
    ip_modbus = "10.0.2.218"  # Ajuste conforme necessário
    
    print("=" * 70)
    print("🔗 MAPEAMENTO AUTOMÁTICO - MÓDULO 25IOB16")
    print("   16 Entradas (Switches) → 16 Saídas (Automático)")
    print("=" * 70)
    
    mapeador = MapeamentoAutomatico(ip_modbus)
    
    try:
        if mapeador.conectar():
            mapeador.executar_mapeamento_continuo()
        else:
            print("❌ Não foi possível conectar ao módulo")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        mapeador.desconectar()
        print("\n👋 Mapeamento automático finalizado!")

if __name__ == "__main__":
    main()
