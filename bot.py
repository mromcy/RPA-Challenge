"""
Script principal de entrada do projeto RPA Challenge.

Fluxo:
    1. Importa a função de orquestração do módulo Executer.
    2. Executa o fluxo completo do RPA Challenge.
"""

from resources.Executers.execute_challenge import executar_challenge

if __name__ == '__main__':
    # Ponto de entrada do projeto — delega toda a lógica ao Executer
    executar_challenge()
