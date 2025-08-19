#!/usr/bin/env python3
"""
Controle do módulo Eletechsup 25IOB16 via Modbus TCP usando socket puro
"""

import socket
import struct

class Modbus25IOB16Socket:
    def __init__(self, host, port=502, unit_id=1, timeout=5):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.transaction_id = 0
    
    def _send_command(self, function_code, register, value):
        """Envia comando Modbus TCP usando socket"""
        self.transaction_id += 1
        
        # Modbus TCP Header: Transaction ID (2) + Protocol ID (2) + Length (2)
        # Modbus PDU: Unit ID (1) + Function Code (1) + Register (2) + Value (2)
        mbap_header = struct.pack('>HHHB', 
                                 self.transaction_id,  # Transaction ID
                                 0,                    # Protocol ID (0 para Modbus)
                                 6,                    # Length (6 bytes: unit_id + fc + register + value)
                                 self.unit_id)         # Unit ID
        
        pdu = struct.pack('>BHH', function_code, register, value)
        
        frame = mbap_header + pdu
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.send(frame)
            
            # Recebe resposta (6+ bytes esperados - gateway específico)
            response = sock.recv(12)
            sock.close()
            
            if len(response) >= 6:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erro na comunicação: {e}")
            return False
    
    def liga_tudo(self):
        """Liga todas as saídas (reg 0 = 1792 = 0x0700)"""
        return self._send_command(0x06, 0, 1792)
    
    def desliga_tudo(self):
        """Desliga todas as saídas (reg 0 = 2048 = 0x0800)"""
        return self._send_command(0x06, 0, 2048)
    
    def toggle_canal(self, canal):
        """Toggle do canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1  # Canal 1 = reg 0, canal 2 = reg 1, etc.
        return self._send_command(0x06, register, 768)  # 0x0300
    
    def liga_canal(self, canal):
        """Liga canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1
        return self._send_command(0x06, register, 256)  # 0x0100
    
    def desliga_canal(self, canal):
        """Desliga canal específico (1-16)"""
        if not (1 <= canal <= 16):
            raise ValueError("Canal deve estar entre 1 e 16")
        
        register = canal - 1
        return self._send_command(0x06, register, 512)  # 0x0200


# Exemplo de uso
if __name__ == "__main__":
    # Configura conexão
    modbus = Modbus25IOB16Socket("10.0.2.218")
    
    print("Testando controle do módulo 25IOB16...")
    
    # Liga todas as saídas
    print("Ligando todas as saídas...")
    if modbus.liga_tudo():
        print("✓ Comando enviado com sucesso")
    else:
        print("✗ Erro no comando")
    
    import time
    time.sleep(2)
    
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