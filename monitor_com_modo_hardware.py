#!/usr/bin/env python3
"""
Monitor com Integração ao Modo Hardware 1:1
Permite usar o modo hardware 1:1 do módulo + toggle por software em canais específicos

CENÁRIOS DE USO:
1. Modo Hardware 1:1 ativo + toggle software em alguns canais
2. Monitoramento puro com controle manual
3. Switch entre modos dinamicamente

FUNCIONALIDADES:
- Configuração automática do modo hardware 1:1
- Override de canais específicos para toggle software
- Monitoramento híbrido
- Switch dinâmico entre modos
"""

import sys
import os

# Adiciona diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time

# Importa as classes dos outros scripts no mesmo diretório
try:
    from configurar_logica_interna import ConfiguradorLogicaInterna
except ImportError:
    print("⚠️ Erro: Não foi possível importar ConfiguradorLogicaInterna")
    print("   Certifique-se que configurar_logica_interna.py está no mesmo diretório")
    sys.exit(1)

try:
    from monitor_controle_hibrido import MonitorControleHibrido
except ImportError:
    print("⚠️ Erro: Não foi possível importar MonitorControleHibrido")
    print("   Certifique-se que monitor_controle_hibrido.py está no mesmo diretório")
    sys.exit(1)

class MonitorModoHardware(MonitorControleHibrido):
    def __init__(self, ip_modbus):
        super().__init__(ip_modbus)
        self.configurador = ConfiguradorLogicaInterna(ip_modbus)
        self.modo_hardware_ativo = False
        self.canais_override = [False] * 16  # Canais que ignoram o modo hardware
    
    def configurar_modo_hardware_1_1(self):
        """Configura o módulo para modo hardware 1:1"""
        print("🔧 Configurando modo hardware 1:1...")
        
        if self.configurador.conectar():
            sucesso = self.configurador.ativar_mapeamento_1_para_1()
            
            if sucesso:
                self.modo_hardware_ativo = True
                print("✅ Modo hardware 1:1 ATIVO")
                print("   💡 Entradas agora controlam saídas automaticamente no hardware")
                return True
            else:
                print("❌ Falha ao configurar modo hardware")
                return False
        else:
            print("❌ Falha na conexão para configuração")
            return False
    
    def desativar_modo_hardware(self):
        """Desativa o modo hardware (volta ao controle manual)"""
        print("🛑 Desativando modo hardware...")
        
        if self.configurador.desativar_logica_interna():
            self.modo_hardware_ativo = False
            print("✅ Modo hardware DESATIVADO")
            print("   💡 Controle volta a ser totalmente manual/software")
            return True
        else:
            print("❌ Falha ao desativar modo hardware")
            return False
    
    def verificar_modo_atual(self):
        """Verifica o modo atual do módulo"""
        print("🔍 Verificando modo atual...")
        self.configurador.verificar_configuracao_atual()
    
    def processar_toggle_hibrido(self, bordas_subida):
        """Processa toggles considerando modo hardware + overrides"""
        comandos_executados = []
        
        for canal in bordas_subida:
            idx = canal - 1
            
            # Se modo hardware ativo E canal não tem override, pula
            if self.modo_hardware_ativo and not self.canais_override[idx]:
                # Hardware já está processando, não intervir
                continue
            
            # Processa toggle por software (override ou modo manual)
            if self.toggle_habilitado[idx]:
                self.estado_toggle_saidas[idx] = not self.estado_toggle_saidas[idx]
                
                if self.estado_toggle_saidas[idx]:
                    sucesso = self.modbus.liga_canal(canal)
                    acao = "ON"
                else:
                    sucesso = self.modbus.desliga_canal(canal)
                    acao = "OFF"
                
                if sucesso:
                    tipo = "Override" if self.canais_override[idx] else "Software"
                    comandos_executados.append(f"Toggle {tipo} E{canal}→S{canal}: {acao}")
                    self.contador_toggles += 1
                else:
                    comandos_executados.append(f"Toggle E{canal}→S{canal}: ERRO")
        
        return comandos_executados
    
    def executar_comando_hibrido(self, comando):
        """Executa comandos considerando modo hardware"""
        comando = comando.strip().lower()
        
        # Comandos específicos do modo hardware
        if comando == 'hw_on':
            return self.configurar_modo_hardware_1_1()
        
        elif comando == 'hw_off':
            return self.desativar_modo_hardware()
        
        elif comando == 'hw_status':
            self.verificar_modo_atual()
            return True
        
        # Comandos de override (o1-o16)
        elif comando.startswith('o') and len(comando) <= 3:
            canal_str = comando[1:]
            if canal_str.isdigit() and 1 <= int(canal_str) <= 16:
                canal = int(canal_str)
                idx = canal - 1
                self.canais_override[idx] = not self.canais_override[idx]
                status = "ATIVO" if self.canais_override[idx] else "INATIVO"
                print(f"✅ Override canal {canal}: {status}")
                print(f"   💡 Canal {canal} {'ignora' if self.canais_override[idx] else 'segue'} modo hardware")
                return True
        
        # Comandos normais
        else:
            return self.executar_comando(comando)
    
    def mostrar_ajuda_hibrida(self):
        """Mostra ajuda incluindo comandos de modo hardware"""
        print("\n📋 COMANDOS DISPONÍVEIS (MODO HÍBRIDO):")
        print("┌─────────────────────────────────────────────────────────┐")
        print("│ MODO HARDWARE:                                          │")
        print("│   hw_on       : Ativar modo hardware 1:1               │")
        print("│   hw_off      : Desativar modo hardware                │")
        print("│   hw_status   : Verificar modo atual                   │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ OVERRIDE HARDWARE:                                      │")
        print("│   o1-o16      : Toggle override canal (ignora hardware) │")
        print("├─────────────────────────────────────────────────────────┤")
        print("│ CONTROLE MANUAL: (mesmo que modo básico)               │")
        print("│   1-16, on1-on16, off1-off16, all_on, all_off         │")
        print("│   t1-t16      : Toggle software por entrada            │")
        print("│   status, help, quit                                   │")
        print("└─────────────────────────────────────────────────────────┘")
        print("💡 Hardware: Entrada controla saída automaticamente")
        print("💡 Override: Canal específico ignora hardware, usa software")
    
    def mostrar_status_hibrido(self):
        """Status considerando modo hardware"""
        self.mostrar_status_detalhado()
        
        print(f"🔧 MODO HARDWARE:")
        print(f"   • Status: {'ATIVO' if self.modo_hardware_ativo else 'INATIVO'}")
        
        if self.modo_hardware_ativo:
            overrides_ativos = [i+1 for i, x in enumerate(self.canais_override) if x]
            print(f"   • Overrides: {overrides_ativos if overrides_ativos else 'Nenhum'}")
        
        print("=" * 60)
    
    def thread_interface_comandos(self):
        """Thread de comandos adaptada para modo híbrido"""
        while self.executando:
            try:
                comando = input().strip()
                if comando:
                    if comando.lower() == 'help':
                        self.mostrar_ajuda_hibrida()
                    elif comando.lower() == 'status':
                        self.mostrar_status_hibrido()
                    else:
                        self.executar_comando_hibrido(comando)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️ Erro na interface: {e}")
    
    def executar_monitor_hibrido(self):
        """Monitor híbrido com suporte a modo hardware"""
        print("🚀 MONITOR HÍBRIDO COM MODO HARDWARE")
        print("=" * 60)
        print("📋 MODOS DISPONÍVEIS:")
        print("   1️⃣ Hardware 1:1 - Entrada controla saída automaticamente")
        print("   2️⃣ Toggle Software - Detecção de borda + toggle por software") 
        print("   3️⃣ Híbrido - Hardware + override em canais específicos")
        print("   4️⃣ Manual - Controle total via comandos")
        print("=" * 60)
        print("💡 Digite 'hw_on' para ativar modo hardware")
        print("💡 Digite 'help' para ver todos os comandos")
        print("=" * 60)
        
        # Executa monitor normal, mas com processamento híbrido
        super().executar_monitor_hibrido()

def main():
    """Função principal"""
    ip_modbus = "10.0.2.218"
    
    print("=" * 60)
    print("🔗 MONITOR HÍBRIDO COM MODO HARDWARE - 25IOB16")
    print("   Hardware 1:1 + Toggle Software + Controle Manual")
    print("=" * 60)
    
    monitor = MonitorModoHardware(ip_modbus)
    
    try:
        if monitor.conectar():
            monitor.executar_monitor_hibrido()
        else:
            print("❌ Não foi possível conectar ao módulo")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        monitor.desconectar()
        print("\n👋 Monitor híbrido finalizado!")

if __name__ == "__main__":
    main()