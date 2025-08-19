#!/usr/bin/env python3
"""
Script para encontrar o mapeamento real das entradas digitais
"""

from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus
import time

def encontrar_mapeamento_real():
    """Encontra o mapeamento real das entradas digitais"""
    print("=== Encontrando Mapeamento Real das Entradas ===")
    
    # Inicializa conexão
    modbus = Modbus25IOB16Pymodbus("10.0.2.218")
    
    if not modbus.connect():
        print("❌ Erro ao conectar!")
        return False
    
    try:
        print("✅ Conectado com sucesso")
        
        print("\n🔍 Agora ative a I/O 13 fisicamente e pressione Enter...")
        input()
        
        # Testa uma ampla faixa de registradores para encontrar mudanças
        print("\n--- Procurando Registradores que Mudaram ---")
        registradores_mudaram = []
        
        # Testa registradores de 0 a 300
        for reg in range(0, 301):
            try:
                result = modbus.client.read_holding_registers(reg, count=1, device_id=modbus.unit_id)
                if not result.isError():
                    valor = result.registers[0]
                    if valor != 0:  # Só mostra registradores com dados
                        print(f"  Registrador {reg:3d}: {valor:4d} (0x{valor:04X})")
                        
                        # Analisa se pode ser entrada digital
                        if 0 <= valor <= 65535:  # Valor válido de 16 bits
                            bits_ativos = []
                            for bit in range(16):
                                if valor & (1 << bit):
                                    bits_ativos.append(bit + 1)
                            if bits_ativos:
                                print(f"           Bits ativos: {bits_ativos}")
                                registradores_mudaram.append((reg, valor, bits_ativos))
                        
                time.sleep(0.01)  # Pequena pausa para não sobrecarregar
                
            except Exception as e:
                # Ignora erros e continua
                pass
        
        print(f"\n📊 Total de registradores com dados: {len(registradores_mudaram)}")
        
        if registradores_mudaram:
            print("\n--- Registradores com Dados (Possíveis Entradas) ---")
            for reg, valor, bits in registradores_mudaram:
                print(f"Registrador {reg:3d}: {valor:4d} (0x{valor:04X}) - Bits: {bits}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a investigação: {e}")
        return False
    
    finally:
        modbus.disconnect()
        print("\n🔌 Conexão fechada")

if __name__ == "__main__":
    sucesso = encontrar_mapeamento_real()
    if sucesso:
        print("\n🎯 Investigação concluída!")
    else:
        print("\n💥 Investigação falhou!")
