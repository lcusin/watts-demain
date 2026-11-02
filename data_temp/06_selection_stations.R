source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 06 - Sélectionner les stations avec plus de 95 % de température ET de pluie.
# Variables retenues : température t et cumul de précipitations sur 3 heures rr3.
# À lancer après le script 05, depuis le dossier du projet.
library(data.table)

seuil <- 95

couverture <- fread(file.path(dossier, "couverture_stations_par_annee.csv"),
                    colClasses = c(geo_id_wmo = "character"))
stopifnot(nrow(couverture) > 0, seuil >= 0, seuil < 100,
          anyDuplicated(couverture, by = c("geo_id_wmo", "annee")) == 0,
          all(couverture$nb_attendus > 0),
          all(couverture$nb_temperature >= 0 & couverture$nb_temperature <= couverture$nb_attendus),
          all(couverture$nb_rr3 >= 0 & couverture$nb_rr3 <= couverture$nb_attendus))

# Couverture globale : somme des valeurs disponibles / somme des créneaux attendus.
# Les années absentes comptent aussi ; 2026 s'arrête à la dernière date disponible.
# On ne fait pas la moyenne des pourcentages annuels, car leurs durées diffèrent.
bilan <- couverture[, .(
  nom = nom[1],
  nb_temperature = sum(nb_temperature),
  nb_rr3 = sum(nb_rr3),
  nb_attendus = sum(nb_attendus)
), by = geo_id_wmo]
bilan[, `:=`(couverture_temperature = 100 * nb_temperature / nb_attendus,
              couverture_rr3 = 100 * nb_rr3 / nb_attendus)]
# Chaque variable doit dépasser le seuil ; leurs valeurs peuvent manquer à des dates différentes.
bilan[, selectionnee := couverture_temperature > seuil & couverture_rr3 > seuil]
setorder(bilan, -couverture_temperature)
selection <- bilan[selectionnee == TRUE]

# Sauvegarder le bilan de toutes les stations et la liste retenue.
fwrite(bilan, file.path(dossier, "bilan_selection_stations.csv"))
fwrite(selection, file.path(dossier, "stations_selectionnees.csv"))

# Conserver uniquement la température et la pluie, sans combler les NA.
meteo <- readRDS(file.path(dossier, "synop_metropole_nettoye.rds"))
meteo_selection <- meteo[geo_id_wmo %in% selection$geo_id_wmo,
                         .(geo_id_wmo, date_utc, t, rr3)]
saveRDS(meteo_selection, file.path(dossier, "synop_stations_selectionnees.rds"))

cat(nrow(selection), "stations retenues sur", nrow(bilan),
    "avec une couverture globale >", seuil, "% pour t ET rr3.\n")
cat("Période évaluée : du 2012-01-01 00:00:00 au",
    format(max(meteo$date_utc), tz = "UTC"), "UTC.\n")
print(selection[, .(geo_id_wmo, nom,
                     couverture_temperature = round(couverture_temperature, 2),
                     couverture_rr3 = round(couverture_rr3, 2))],
      nrows = nrow(selection))
