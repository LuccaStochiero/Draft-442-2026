from features import live_stats
print("Iniciando atualização manual forçada...")
live_stats.run_auto_update(force=True)
print("Atualização manual concluída!")
