#!/usr/bin/env python3
"""
Script para investigar o mapeamento real das entradas digitais
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time

def investigar_registradores(modbus):
    """Investiga uma faixa ampla de registradores para encontrar as entradas"""
    print("🔍 Investigando registradores 0-300...")
    
    registradores_com_dados = []
    
    for reg in range(0, 301):
        try:
            result = modbus.client.read_holding_registers(reg, count=1, device_id=modbus.unit_id)
            if not result.isError():
                valor = result.registers[0]
                if valor != 0:  # Só registradores com dados
                    registradores_com_dados.append((reg, valor))
                    print(f"Reg {reg:3d}: {valor:5d} (0x{valor:04X})")
                    
                    # Analisa bits se o valor parece ser entrada digital
                    if 0 < valor < 65536:
                        bits_ativos = []
                        for bit in range(16):
                            if valor & (1 << bit):
                                bits_ativos.append(bit)
                        if bits_ativos:
                            print(f"         Bits ativos: {bits_ativos}")
            
            time.sleep(0.01)  # Evita sobrecarregar
            
        except Exception as e:
            pass  # Ignora erros e continua
    
    return registradores_com_dados

def testar_entradas_conhecidas(modbus):
    """Testa registradores que sabemos que podem conter entradas"""
    print("\n🧪 Testando registradores específicos...")
    
    # Lista de registradores para testar
    regs_teste = [16, 17, 18, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256]
    
    for reg in regs_teste:
        try:
            result = modbus.client.read_holding_registers(reg, count=1, device_id=modbus.unit_id)
            if not result.isError():
                valor = result.registers[0]
                print(f"Reg {reg:3d}: {valor:5d} (0x{valor:04X})", end="")
                
                if valor != 0:
                    bits_ativos = []
                    for bit in range(16):
                        if valor & (1 << bit):
                            bits_ativos.append(bit + 1)
                    if bits_ativos:
                        print(f" - Bits: {bits_ativos}")
                    else:
                        print()
                else:
                    print()
        except Exception as e:
            print(f"Reg {reg:3d}: ERRO - {e}")

def comparar_antes_depois(modbus):
    """Compara valores antes e depois da mudança da entrada"""
    print("\n⚠️  IMPORTANTE: Mantenha APENAS a entrada 7 ativa agora!")
    input("Pressione Enter quando entrada 7 estiver ativa...")
    
    # Lê estado inicial
    estado_inicial = {}
    regs_interesse = list(range(0, 21)) + [16, 17, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256]
    
    print("\nLendo estado inicial...")
    for reg in regs_interesse:
        try:
            result = modbus.client.read_holding_registers(reg, count=1, device_id=modbus.unit_id)
            if not result.isError():
                estado_inicial[reg] = result.registers[0]
        except:
            pass
    
    print("\n⚠️  Agora mude para APENAS a entrada 9 ativa!")
    input("Pressione Enter quando entrada 9 estiver ativa...")
    
    # Lê estado final
    print("\nLendo estado final...")
    mudancas = []
    for reg in regs_interesse:
        try:
            result = modbus.client.read_holding_registers(reg, count=1, device_id=modbus.unit_id)
            if not result.isError():
                valor_final = result.registers[0]
                valor_inicial = estado_inicial.get(reg, 0)
                
                if valor_inicial != valor_final:
                    mudancas.append((reg, valor_inicial, valor_final))
                    print(f"🔄 Reg {reg:3d}: {valor_inicial:5d} → {valor_final:5d} (0x{valor_inicial:04X} → 0x{valor_final:04X})")
        except:
            pass
    
    if mudancas:
        print(f"\n✅ Encontradas {len(mudancas)} mudanças!")
        print("\nANÁLISE DAS MUDANÇAS:")
        for reg, antes, depois in mudancas:
            print(f"\nRegistrador {reg}:")
            print(f"  Antes: {antes:5d} (0x{antes:04X})")
            print(f"  Depois: {depois:5d} (0x{depois:04X})")
            
            # Analisa mudanças de bits
            bits_antes = []
            bits_depois = []
            for bit in range(16):
                if antes & (1 << bit):
                    bits_antes.append(bit + 1)
                if depois & (1 << bit):
                    bits_depois.append(bit + 1)
            
            print(f"  Bits antes: {bits_antes}")
            print(f"  Bits depois: {bits_depois}")
    else:
        print("\n❌ Nenhuma mudança detectada!")

def main():
    print("="*60)
    print("      INVESTIGAÇÃO DAS ENTRADAS DIGITAIS")
    print("="*60)
    
    modbus = Modbus25IOB16Pymodbus("10.0.2.218")
    
    if not modbus.connect():
        print("❌ Erro ao conectar!")
        return
    
    try:
        print("✅ Conectado com sucesso")
        
        # Primeiro desliga todas as saídas para não confundir
        print("\n🔧 Desligando todas as saídas...")
        modbus.desliga_tudo()
        time.sleep(1)
        
        # Investiga registradores
        print("\n" + "="*50)
        registradores = investigar_registradores(modbus)
        
        # Testa registradores específicos
        print("\n" + "="*50)
        testar_entradas_conhecidas(modbus)
        
        # Comparação antes/depois
        print("\n" + "="*50)
        comparar_antes_depois(modbus)
        
    finally:
        modbus.disconnect()
        print("\n🔌 Conexão fechada")

if __name__ == "__main__":
    main()