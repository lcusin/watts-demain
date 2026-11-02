# Chemins communs : lancer les scripts depuis le projet ou depuis data_temp.
racine_scripts <- normalizePath(if (file.exists("data_temp/00_chemins.R")) "data_temp" else ".",
                                winslash = "/", mustWork = TRUE)
racine_meteo <- file.path(racine_scripts, "meteo_synop_2012_2026")
dossier_brut <- file.path(racine_meteo, "brut")
dossier <- file.path(racine_meteo, "prepare")
sortie <- file.path(racine_scripts, "graphiques")
