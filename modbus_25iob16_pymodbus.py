#!/usr/bin/env python3
"""
Controle do módulo Eletechsup 25IOB16 via Modbus TCP usando pymodbus
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

class Modbus25IOB16Pymodbus:
    def __init__(self, host, port=502, unit_id=1, timeout=5):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.client = None
    
    def connect(self):
        """Estabelece conexão com o gateway"""
        try:
            self.client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
            return self.client.connect()
        except Exception as e:
            print(f"Erro na conexão: {e}")
            return False
    
    def disconnect(self):
        """Fecha conexão"""
        if self.client:
            self.client.close()
    
    def _write_register(self, register, value):
        """Escreve valor em registrador usando Function Code 06"""
        if not self.client or not self.client.connected:
            if not self.connect():
                return False
        
        try:
            result = self.client.write_register(register, value, device_id=self.unit_id)
            return not result.isError()
        except ModbusException as e:
            print(f"Erro Modbus: {e}")
            return False
        except Exception as e:
            print(f"Erro na comunicação: {e}")
            return False
    
    def liga_tudo(self):
        """Liga todas as saídas (reg 0 = 1792 = 0x0700)"""
        return self._write_register(0, 1792)
    
    def desliga_tudo(self):
        """Desliga todas as saídas (reg 0 = 2048 = 0x0800)"""
        return self._write_register(0, 2048)
    
    def toggle_canal(self, canal):
        """Toggle do canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1  # Canal 1 = reg 0, canal 2 = reg 1, etc.
        return self._write_register(register, 768)  # 0x0300
    
    def liga_canal(self, canal):
        """Liga canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1
        return self._write_register(register, 256)  # 0x0100
    
    def desliga_canal(self, canal):
        """Desliga canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1
        return self._write_register(register, 512)  # 0x0200
    
    def le_status_entradas(self):
        """Lê status das entradas digitais (registradores 16-31)"""
        if not self.client or not self.client.connected:
            if not self.connect():
                return None
        
        try:
            # Lê 16 registradores a partir do 16 (entradas)
            result = self.client.read_holding_registers(16, count=16, device_id=self.unit_id)
            if not result.isError():
                return result.registers
            else:
                print(f"Erro ao ler entradas: {result}")
                return None
        except Exception as e:
            print(f"Erro na leitura: {e}")
            return None
    
    def le_status_saidas(self):
        """Lê status das saídas digitais (registradores 0-15)"""
        if not self.client or not self.client.connected:
            if not self.connect():
                return None
        
        try:
            # Lê 16 registradores a partir do 0 (saídas)
            result = self.client.read_holding_registers(0, count=16, device_id=self.unit_id)
            if not result.isError():
                return result.registers
            else:
                print(f"Erro ao ler saídas: {result}")
                return None
        except Exception as e:
            print(f"Erro na leitura: {e}")
            return None


# Exemplo de uso
if __name__ == "__main__":
    # Configura conexão
    modbus = Modbus25IOB16Pymodbus("10.0.2.218")
    
    print("Testando controle do módulo 25IOB16 com pymodbus...")
    
    # Conecta
    if not modbus.connect():
        print("Erro ao conectar!")
        exit(1)
    
    try:
        # Liga todas as saídas
        print("Ligando todas as saídas...")
        if modbus.liga_tudo():
            print("✓ Comando enviado com sucesso")
        else:
            print("✗ Erro no comando")
        
        import time
        time.sleep(2)
        
        # Lê status das saídas
        print("Lendo status das saídas...")
        status = modbus.le_status_saidas()
        if status:
            print(f"Status das saídas: {status}")
        
        # Desliga todas as saídas
        print("Desligando todas as saídas...")
        if modbus.desliga_tudo():
            print("✓ Comando enviado com sucesso")
        else:
            print("✗ Erro no comando")
        
        time.sleep(1)
        
        # Liga canal 1
        print("Ligando canal 1...")
        if modbus.liga_canal(1):
            print("✓ Comando enviado com sucesso")
        else:
            print("✗ Erro no comando")
        
        time.sleep(1)
        
        # Toggle canal 1
        print("Toggle canal 1...")
        if modbus.toggle_canal(1):
            print("✓ Comando enviado com sucesso")
        else:
            print("✗ Erro no comando")
            
        # Lê status das entradas
        print("Lendo status das entradas...")
        entradas = modbus.le_status_entradas()
        if entradas:
            print(f"Status das entradas: {entradas}")
    
    finally:
        modbus.disconnect()
        print("Conexão fechada.")