#!/usr/bin/env python3
"""
Exemplo de uso simples dos módulos de controle do 25IOB16
"""

# Escolha uma das implementações:

# Versão 1: Socket puro (mais simples, sem dependências)
from modbus_25iob16_socket import Modbus25IOB16Socket

# Versão 2: Pymodbus (mais recursos, precisa instalar: pip install pymodbus)
# from modbus_25iob16_pymodbus import Modbus25IOB16Pymodbus

def exemplo_socket():
    """Exemplo usando socket puro"""
    print("=== Exemplo com Socket Puro ===")
    
    # Inicializa conexão
    modbus = Modbus25IOB16Socket("10.0.2.218")
    
    # Comandos básicos
    print("Ligando todas as saídas...")
    modbus.liga_tudo()
    
    input("Pressione Enter para continuar...")
    
    print("Desligando todas as saídas...")
    modbus.desliga_tudo()
    
    input("Pressione Enter para continuar...")
    
    print("Ligando canal 5...")
    modbus.liga_canal(5)
    
    input("Pressione Enter para continuar...")
    
    print("Toggle canal 5...")
    modbus.toggle_canal(5)
    
    print("Exemplo concluído!")

def exemplo_pymodbus():
    """Exemplo usando pymodbus"""
    print("=== Exemplo com Pymodbus ===")
    
    # Inicializa conexão
    modbus = Modbus25IOB16Pymodbus("10.0.2.218")
    
    if not modbus.connect():
        print("Erro ao conectar!")
        return
    
    try:
        # Comandos básicos
        print("Ligando todas as saídas...")
        modbus.liga_tudo()
        
        # Lê status
        status = modbus.le_status_saidas()
        print(f"Status das saídas: {status}")
        
        input("Pressione Enter para continuar...")
        
        print("Desligando todas as saídas...")
        modbus.desliga_tudo()
        
        input("Pressione Enter para continuar...")
        
        # Testa canais individuais
        for canal in [1, 3, 5]:
            print(f"Ligando canal {canal}...")
            modbus.liga_canal(canal)
        
        status = modbus.le_status_saidas()
        print(f"Status após ligar canais 1,3,5: {status}")
        
        input("Pressione Enter para finalizar...")
        
        print("Desligando tudo...")
        modbus.desliga_tudo()
        
    finally:
        modbus.disconnect()
    
    print("Exemplo concluído!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "pymodbus":
        exemplo_pymodbus()
    else:
        exemplo_socket()
