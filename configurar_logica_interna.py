#!/usr/bin/env python3
"""
Configuração da Lógica Interna da Placa 25IOB16
Configura mapeamento automático entrada→saída diretamente na placa usando registrador oficial

REGISTRADORES CORRIGIDOS:
- Registrador 250 (0x00FA): Controle de lógica interna (baseado na documentação EletechSup)

MODOS SUPORTADOS:
- 0x0000: Desabilitado (sem relação)
- 0x0001: Auto-travamento (self-locking)
- 0x0002: Intertravamento (todos canais)
- 0x0003: Momentâneo
- 0x0004: Intertravamento (2 canais)
- 0x0005: Mapeamento 1:1 (Output = Input)

FUNCIONALIDADES:
- Configuração de lógica interna no hardware (sem necessidade de scripts externos)
- Backup/restore de configurações
- Detecção automática do modo atual
- Interface simplificada com todos os modos oficiais
- Testes integrados de funcionamento

AUTOR: Script corrigido com registradores oficiais da documentação EletechSup
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class ConfiguradorLogicaInterna:
    def __init__(self, ip_modbus, porta=502, unit_id=1):
        self.modbus = Modbus25IOB16Pymodbus(ip_modbus, porta, unit_id)
        self.ip = ip_modbus
        self.porta = porta
        self.unit_id = unit_id
        
        # Registrador oficial de configuração da lógica interna (baseado na documentação EletechSup)
        self.REG_LOGICA_INTERNA = 250  # 0x00FA - Controla modos de relacionamento entrada-saída
        
        # Modos oficiais suportados pelo módulo 25IOB16
        self.MODOS = {
            'desabilitado': 0x0000,    # Sem relação (padrão)
            'auto_travamento': 0x0001, # Self-locking
            'inter_todos': 0x0002,     # Interlocking (todos canais)
            'momentaneo': 0x0003,      # Momentary
            'inter_2canais': 0x0004,   # Interlocking (2 canais)
            'mapeamento_1_1': 0x0005   # Output = Input (mapeamento direto 1:1)
        }
        
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
    
    def ler_modo_atual(self):
        """Lê o modo de lógica interna atual do módulo"""
        try:
            result = self.modbus.client.read_holding_registers(self.REG_LOGICA_INTERNA, count=1, device_id=self.modbus.unit_id)
            if not result.isError():
                modo_valor = result.registers[0]
                
                # Converte valor numérico para nome do modo
                for nome, valor in self.MODOS.items():
                    if valor == modo_valor:
                        return nome, modo_valor
                
                return 'desconhecido', modo_valor
            else:
                print(f"❌ Erro ao ler modo atual: {result}")
                return None, None
        except Exception as e:
            print(f"❌ Exceção ao ler modo atual: {e}")
            return None, None
    
    def configurar_modo(self, modo_nome):
        """Configura o modo de lógica interna do módulo"""
        if modo_nome not in self.MODOS:
            print(f"❌ Modo '{modo_nome}' não suportado!")
            print(f"   Modos disponíveis: {list(self.MODOS.keys())}")
            return False
            
        try:
            modo_valor = self.MODOS[modo_nome]
            result = self.modbus.client.write_register(self.REG_LOGICA_INTERNA, modo_valor, device_id=self.modbus.unit_id)
            if not result.isError():
                return True
            else:
                print(f"❌ Erro ao configurar modo '{modo_nome}': {result}")
                return False
        except Exception as e:
            print(f"❌ Exceção ao configurar modo '{modo_nome}': {e}")
            return False
    
    def ativar_mapeamento_1_para_1(self):
        """Ativa mapeamento 1:1 usando o modo oficial do módulo"""
        print("\n🔧 Ativando Mapeamento 1:1 (Entrada N → Saída N)...")
        print("   • Usando modo oficial do hardware: 'mapeamento_1_1'")
        print("   • Sem necessidade de script externo!")
        
        if self.configurar_modo('mapeamento_1_1'):
            print("   ✅ Mapeamento automático 1:1 ATIVADO no hardware!")
            print("   ℹ️ O módulo agora funciona independentemente de software")
            return True
        else:
            print("   ❌ Falha ao ativar mapeamento 1:1")
            return False
    
    def listar_modos_disponiveis(self):
        """Lista todos os modos de lógica interna disponíveis"""
        print("\n📝 MODOS DE LÓGICA INTERNA DISPONÍVEIS:")
        
        descricoes = {
            'desabilitado': 'Sem relação entre entradas e saídas (controle manual)',
            'auto_travamento': 'Entrada ativa trava a saída correspondente (self-locking)',
            'inter_todos': 'Entradas controlam saídas com intertravamento global',
            'momentaneo': 'Saídas ativas apenas enquanto entradas estiverem ativas',
            'inter_2canais': 'Intertravamento entre pares de canais',
            'mapeamento_1_1': 'Mapeamento direto 1:1 - Entrada N controla Saída N'
        }
        
        for i, (modo, valor) in enumerate(self.MODOS.items(), 1):
            descricao = descricoes.get(modo, 'Descrição não disponível')
            print(f"   {i}. {modo.upper().replace('_', ' ')}") 
            print(f"      • Valor: 0x{valor:04X}")
            print(f"      • {descricao}")
            print()
    
    def verificar_configuracao_atual(self):
        """Verifica o modo atual de lógica interna do módulo"""
        print("\n🔍 Verificando Configuração Atual...")
        
        modo_nome, modo_valor = self.ler_modo_atual()
        
        if modo_nome is None:
            print("   ❌ Não foi possível ler a configuração atual")
            return
            
        print(f"   • Modo ativo: {modo_nome.upper().replace('_', ' ')}")
        print(f"   • Valor do registrador: 0x{modo_valor:04X} ({modo_valor})")
        print(f"   • Registrador usado: {self.REG_LOGICA_INTERNA} (0x{self.REG_LOGICA_INTERNA:02X})")
        
        # Explicação do modo atual
        explicacoes = {
            'desabilitado': 'Lógica interna desativada - controle manual das saídas',
            'auto_travamento': 'Entradas travam as saídas correspondentes',
            'inter_todos': 'Sistema de intertravamento ativo em todos canais',
            'momentaneo': 'Saídas ativas apenas com entradas ativas',
            'inter_2canais': 'Intertravamento por pares de canais',
            'mapeamento_1_1': 'MAPEAMENTO AUTOMÁTICO 1:1 ATIVO - Hardware controla as saídas',
            'desconhecido': 'Modo não reconhecido - verifique o valor'
        }
        
        explicacao = explicacoes.get(modo_nome, 'Modo não documentado')
        print(f"   ℹ️ Status: {explicacao}")
    
    def desativar_logica_interna(self):
        """Desativa a lógica interna (volta ao modo manual)"""
        print("\n🛑 Desativando Lógica Interna...")
        print("   • Retornando ao modo manual (sem relação)")
        
        if self.configurar_modo('desabilitado'):
            print("   ✅ Lógica interna DESATIVADA")
            print("   ℹ️ Saídas agora devem ser controladas manualmente")
            return True
        else:
            print("   ❌ Falha ao desativar lógica interna")
            return False
    
    def testar_logica_interna(self):
        """Testa se a lógica interna está funcionando corretamente"""
        print("\n🧪 Testando Lógica Interna...")
        
        # Verifica modo atual
        modo_atual, _ = self.ler_modo_atual()
        if modo_atual is None:
            print("   ❌ Não foi possível verificar o modo atual")
            return
            
        print(f"   • Modo ativo: {modo_atual.upper().replace('_', ' ')}")
        
        if modo_atual == 'desabilitado':
            print("   ⚠️  Lógica interna desabilitada - ative um modo primeiro")
            return
            
        print("   • Instrucões para teste:")
        
        if modo_atual == 'mapeamento_1_1':
            print("     1. Ative uma entrada fisicamente")
            print("     2. A saída correspondente deve ligar automaticamente")
            print("     3. Desative a entrada - a saída deve desligar")
        elif modo_atual == 'momentaneo':
            print("     1. Mantenha uma entrada ativada")
            print("     2. Saída deve ficar ativa enquanto entrada estiver ativa")
            print("     3. Solte a entrada - saída deve desativar imediatamente")
        else:
            print(f"     1. Teste apropriado para modo '{modo_atual}'")
            print("     2. Consulte manual para detalhes do comportamento")
            
        print("\n   • Pressione Enter para verificar estados atuais...")
        input()
        
        # Lê e mostra estados atuais
        entradas = self.modbus.le_status_entradas()
        saidas_digitais = self.modbus.le_status_saidas_digitais()
        
        if entradas is not None and saidas_digitais is not None:
            print(f"\n   📡 ESTADOS ATUAIS:")
            
            entradas_ativas = [i+1 for i, x in enumerate(entradas) if x]
            saidas_ativas = [i+1 for i, x in enumerate(saidas_digitais) if x]
            
            print(f"   • Entradas ativas: {entradas_ativas if entradas_ativas else 'Nenhuma'}")
            print(f"   • Saídas ativas: {saidas_ativas if saidas_ativas else 'Nenhuma'}")
            
            if modo_atual == 'mapeamento_1_1':
                correspondencias = sum(1 for i in range(16) if entradas[i] == saidas_digitais[i])
                print(f"   • Correspondências 1:1: {correspondencias}/16")
                
                if correspondencias == 16:
                    print("   ✅ Mapeamento 1:1 funcionando perfeitamente!")
                elif correspondencias > 12:
                    print("   ✅ Mapeamento funcionando bem")
                else:
                    print("   ⚠️  Verifique se o modo está configurado corretamente")
        else:
            print("   ❌ Erro ao ler estados das entradas/saídas")
    
    def backup_configuracao(self):
        """Faz backup da configuração atual"""
        import time
        
        print("\n💾 Fazendo Backup da Configuração...")
        
        modo_atual, modo_valor = self.ler_modo_atual()
        if modo_atual is not None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup = {
                'timestamp': timestamp,
                'modo': modo_atual,
                'valor': modo_valor,
                'registrador': self.REG_LOGICA_INTERNA,
                'descricao': f"Backup do módulo 25IOB16 em {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            filename = f"backup_25iob16_{timestamp}.json"
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(backup, f, indent=2)
                print(f"   ✅ Backup salvo em: {filename}")
                print(f"   • Modo salvo: {modo_atual}")
                print(f"   • Valor: 0x{modo_valor:04X}")
                return filename
            except Exception as e:
                print(f"   ❌ Erro ao salvar backup: {e}")
                return None
        else:
            print("   ❌ Não foi possível fazer backup - erro ao ler configuração atual")
            return None
    
    def restaurar_configuracao(self, arquivo_backup):
        """Restaura configuração de um arquivo de backup"""
        print(f"\n🔄 Restaurando Configuração de {arquivo_backup}...")
        
        try:
            import json
            with open(arquivo_backup, 'r') as f:
                backup = json.load(f)
            
            modo = backup['modo']
            valor_original = backup.get('valor', 0)
            
            print(f"   • Modo no backup: {modo.upper().replace('_', ' ')}")
            print(f"   • Valor original: 0x{valor_original:04X}")
            print(f"   • Data do backup: {backup.get('timestamp', 'N/A')}")
            
            if self.configurar_modo(modo):
                print("   ✅ Configuração restaurada com sucesso!")
                
                # Verifica se foi aplicado corretamente
                modo_verificacao, valor_verificacao = self.ler_modo_atual()
                if modo_verificacao == modo:
                    print("   ✅ Verificação: Modo aplicado corretamente")
                else:
                    print(f"   ⚠️  Verificação: Modo atual é '{modo_verificacao}', esperado '{modo}'")
                
                return True
            else:
                print("   ❌ Falha ao restaurar configuração")
                return False
                
        except FileNotFoundError:
            print(f"   ❌ Arquivo de backup não encontrado: {arquivo_backup}")
            return False
        except json.JSONDecodeError:
            print(f"   ❌ Arquivo de backup corrompido ou inválido")
            return False
        except Exception as e:
            print(f"   ❌ Erro ao restaurar backup: {e}")
            return False

def main():
    """Função principal"""
    # CONFIGURAÇÕES CARREGADAS DO .env
    ip_modbus = os.getenv("MODBUS_IP", "10.0.2.70")           # IP do gateway WAVESHARE RS485-ETH
    porta_modbus = int(os.getenv("MODBUS_PORT", "502"))       # Porta padrão Modbus TCP
    endereco_modbus = int(os.getenv("MODBUS_UNIT_ID", "1"))   # Endereço do módulo 25IOB16 (unit_id)
    
    print("=" * 70)
    print("🔧 CONFIGURADOR DE LÓGICA INTERNA - MÓDULO 25IOB16")
    print("   Configura mapeamento automático entrada→saída na placa")
    print(f"   Gateway: {ip_modbus}:{porta_modbus} | Módulo: {endereco_modbus}")
    print("=" * 70)
    
    configurador = ConfiguradorLogicaInterna(ip_modbus, porta_modbus, endereco_modbus)
    
    try:
        if not configurador.conectar():
            return
        
        while True:
            print("\n📋 OPÇÕES DISPONÍVEIS:")
            print("1. Ativar mapeamento 1:1 (Entrada N → Saída N)")
            print("2. Listar todos os modos disponíveis")
            print("3. Configurar modo específico")
            print("4. Verificar configuração atual")
            print("5. Testar lógica interna")
            print("6. Desativar lógica interna")
            print("7. Backup da configuração")
            print("8. Restaurar configuração")
            print("0. Sair")
            
            opcao = input("\nEscolha uma opção (0-8): ").strip()
            
            if opcao == "1":
                if configurador.ativar_mapeamento_1_para_1():
                    print("\n✅ Mapeamento 1:1 ativado com sucesso!")
                    print("   🎯 A placa agora funciona independentemente de software!")
                    print("   📝 Cada entrada controla automaticamente sua saída correspondente")
                else:
                    print("\n❌ Falha na ativação do mapeamento 1:1")
            
            elif opcao == "2":
                configurador.listar_modos_disponiveis()
            
            elif opcao == "3":
                print("\n🔧 CONFIGURAÇÃO DE MODO ESPECÍFICO")
                print("Modos disponíveis:")
                for i, modo in enumerate(configurador.MODOS.keys(), 1):
                    print(f"   {i}. {modo.replace('_', ' ').title()}")
                
                try:
                    escolha = input("\nDigite o nome do modo ou número (1-6): ").strip().lower()
                    
                    # Permite escolha por número ou nome
                    if escolha.isdigit():
                        idx = int(escolha) - 1
                        if 0 <= idx < len(configurador.MODOS):
                            modo_escolhido = list(configurador.MODOS.keys())[idx]
                        else:
                            print("   ❌ Número inválido!")
                            continue
                    else:
                        # Procura por nome (permite nomes parciais)
                        modo_escolhido = None
                        for modo in configurador.MODOS.keys():
                            if escolha in modo.lower() or escolha.replace(' ', '_') == modo:
                                modo_escolhido = modo
                                break
                        
                        if modo_escolhido is None:
                            print("   ❌ Modo não encontrado!")
                            continue
                    
                    if configurador.configurar_modo(modo_escolhido):
                        print(f"\n✅ Modo '{modo_escolhido.replace('_', ' ').title()}' configurado com sucesso!")
                    else:
                        print(f"\n❌ Falha ao configurar modo '{modo_escolhido}'")
                        
                except ValueError:
                    print("   ❌ Entrada inválida!")
                except KeyboardInterrupt:
                    print("\n   Operação cancelada pelo usuário")
            
            elif opcao == "4":
                configurador.verificar_configuracao_atual()
            
            elif opcao == "5":
                configurador.testar_logica_interna()
            
            elif opcao == "6":
                if configurador.desativar_logica_interna():
                    print("\n✅ Lógica interna desativada com sucesso!")
                else:
                    print("\n❌ Falha ao desativar lógica interna")
            
            elif opcao == "7":
                arquivo_backup = configurador.backup_configuracao()
                if arquivo_backup:
                    print(f"\n💾 Backup criado: {arquivo_backup}")
            
            elif opcao == "8":
                import glob
                arquivos_backup = glob.glob("backup_25iob16_*.json")
                
                if not arquivos_backup:
                    print("\n❌ Nenhum arquivo de backup encontrado")
                else:
                    print("\n📁 ARQUIVOS DE BACKUP DISPONÍVEIS:")
                    for i, arquivo in enumerate(arquivos_backup, 1):
                        print(f"   {i}. {arquivo}")
                    
                    try:
                        escolha = input("\nEscolha o número do backup ou digite o nome: ").strip()
                        
                        if escolha.isdigit():
                            idx = int(escolha) - 1
                            if 0 <= idx < len(arquivos_backup):
                                arquivo_escolhido = arquivos_backup[idx]
                            else:
                                print("   ❌ Número inválido!")
                                continue
                        else:
                            arquivo_escolhido = escolha
                        
                        if configurador.restaurar_configuracao(arquivo_escolhido):
                            print("\n🔄 Configuração restaurada!")
                    
                    except ValueError:
                        print("   ❌ Entrada inválida!")
                    except KeyboardInterrupt:
                        print("\n   Operação cancelada pelo usuário")
            
            elif opcao == "0":
                print("\n👋 Saindo...")
                break
            
            else:
                print("\n❌ Opção inválida! Digite um número de 0 a 8.")
            
            input("\n⏸️  Pressione Enter para continuar...")
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        configurador.desconectar()
        print("\n🔌 Conexão fechada")

if __name__ == "__main__":
    main()
