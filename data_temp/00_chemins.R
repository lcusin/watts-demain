# Chemins communs : execution depuis le projet ou depuis data_temp.
racine_scripts <- "."
if (file.exists("data_temp/00_chemins.R")) racine_scripts <- "data_temp"
racine_scripts <- normalizePath(racine_scripts, winslash = "/")
racine_meteo <- file.path(racine_scripts, "meteo_synop_2012_2026")
dossier_brut <- file.path(racine_meteo, "brut")
dossier <- file.path(racine_meteo, "prepare")
sortie <- file.path(racine_scripts, "graphiques")
