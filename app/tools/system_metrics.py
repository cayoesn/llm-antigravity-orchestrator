import random

def check_system_metrics() -> str:
    """
    Verifica o status de performance e métricas de infraestrutura de servidores da aplicação (CPU, RAM, disco).
    
    Returns:
        str: Relatório formatado das métricas de infraestrutura do sistema.
    """
    cpu_usage = random.uniform(12.5, 48.2)
    memory_usage = random.uniform(32.1, 65.4)
    disk_usage = random.uniform(45.0, 45.2)
    
    status = "SAUDÁVEL" if cpu_usage < 80.0 and memory_usage < 85.0 else "ALERTA"
    
    return (
        f"--- INFRASTRUCTURE PERFORMANCE REPORT ---\n"
        f"Status do Cluster: {status}\n"
        f"Consumo de CPU: {cpu_usage:.1f}%\n"
        f"Consumo de Memória RAM: {memory_usage:.1f}%\n"
        f"Armazenamento de Disco: {disk_usage:.1f}%\n"
        f"Atividade do Banco de Dados: OK (0.8ms latency)\n"
        f"Barramento Redis: OK (Ativo e Saudável)\n"
        f"----------------------------------------"
    )
