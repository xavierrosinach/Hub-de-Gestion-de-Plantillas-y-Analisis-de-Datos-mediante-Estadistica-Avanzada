import bronze.sofascore_cleaning as ss
import bronze.scoresway_cleaning as sw
import bronze.unifier as un
import bronze.eventing_cleaning as ev

# --------------------------------------------------------------------------------------
# Función main de scraping
# --------------------------------------------------------------------------------------
def main(print_info: bool = True) -> None:

    if print_info:
        print("_"*100)

    # Ejecución de las limpiezas de Sofascore y Scoresway
    ss_player, ss_team, ss_manager, ss_match, ss_stats_team, ss_stats_player = ss.main_cleaning(print_info=print_info)
    sw_player, sw_team, sw_manager, sw_match, sw_stats_player = sw.main_cleaning(print_info=print_info)

    if print_info:
        print("_"*100)

    # Unificación de los datos
    unifier_output = un.main_data_unification(ss_player=ss_player, ss_team=ss_team, ss_manager=ss_manager, ss_match=ss_match, ss_stats_player=ss_stats_player, ss_stats_team=ss_stats_team, sw_stats_player=sw_stats_player, sw_player=sw_player, sw_team=sw_team, sw_manager=sw_manager, sw_match=sw_match)
    teams_df, players_df, managers_df, matches_df, team_stats_df, player_stats_df = unifier_output

    if print_info:
        print("_"*100)
        print("Starting the eventing cleaning")

    # Limpieza de los datos de eventing
    passes_df, shots_df = ev.main_eventing_cleaning(team_df=teams_df, player_df=players_df, match_df=matches_df)

    if print_info:
        print("_"*100)