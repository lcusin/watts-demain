source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 05 - Mesurer la couverture annuelle, sans sélectionner définitivement les stations.
library(data.table)

meteo <- readRDS(file.path(dossier, "synop_metropole_nettoye.rds"))
stations <- fread(file.path(dossier, "stations_metropole.csv"),
                  colClasses = c(geo_id_wmo = "character"))
noms <- stations[, .(nom = paste(sort(unique(name)), collapse = " / ")), by = geo_id_wmo]

# Vérifier les horaires avant d'utiliser une grille de 3 heures.
print(meteo[, .N, by = .(heure_utc = format(date_utc, "%H:%M:%S", tz = "UTC"))][order(heure_utc)])
stopifnot(nrow(meteo) > 0, !anyNA(meteo$date_utc),
          anyDuplicated(meteo, by = c("geo_id_wmo", "date_utc")) == 0,
          all(as.numeric(meteo$date_utc) %% (3 * 3600) == 0))
fin <- max(meteo$date_utc)
grille <- data.table(date_utc = seq(as.POSIXct("2012-01-01", tz = "UTC"), fin, by = "3 hours"))
grille[, annee := as.integer(format(date_utc, "%Y", tz = "UTC"))]
attendus <- grille[, .(nb_attendus = .N), by = annee]

meteo[, annee := as.integer(format(date_utc, "%Y", tz = "UTC"))]
comptages <- meteo[, .(
  nb_observations = .N, nb_temperature = sum(!is.na(t)),
  nb_rr1 = sum(!is.na(rr1)), nb_rr3 = sum(!is.na(rr3))
), by = .(geo_id_wmo, annee)]

# Toutes les combinaisons station/année, même lorsqu'il n'y a aucune donnée.
couverture <- CJ(geo_id_wmo = unique(meteo$geo_id_wmo), annee = attendus$annee)
couverture <- merge(couverture, comptages, by = c("geo_id_wmo", "annee"), all.x = TRUE)
for (col in c("nb_observations", "nb_temperature", "nb_rr1", "nb_rr3")) {
  set(couverture, i = which(is.na(couverture[[col]])), j = col, value = 0L)
}
couverture <- merge(couverture, attendus, by = "annee")
couverture[, `:=`(
  couverture_observations = 100 * nb_observations / nb_attendus,
  couverture_temperature = 100 * nb_temperature / nb_attendus,
  couverture_rr1 = 100 * nb_rr1 / nb_attendus,
  couverture_rr3 = 100 * nb_rr3 / nb_attendus
)]
couverture <- merge(couverture, noms, by = "geo_id_wmo", all.x = TRUE)
setorder(couverture, geo_id_wmo, annee)
tableau <- dcast(couverture, geo_id_wmo + nom ~ annee, value.var = "couverture_temperature")

fwrite(couverture, file.path(dossier, "couverture_stations_par_annee.csv"))
fwrite(tableau, file.path(dossier, "couverture_temperature_tableau.csv"))

# Afficher les stations déjà présentes en 2012 (ce n'est pas un seuil de qualité).
ids <- couverture[annee == 2012 & nb_observations > 0, geo_id_wmo]
affichage <- copy(tableau[geo_id_wmo %in% ids])
annees <- setdiff(names(affichage), c("geo_id_wmo", "nom"))
affichage[, (annees) := lapply(.SD, round, 1), .SDcols = annees]
cat(length(ids), "stations présentes en 2012. Couverture de température (%) :\n")
print(affichage, nrows = nrow(affichage))
cat("Pour 2026, couverture calculée seulement jusqu'au", format(fin, tz = "UTC"), "UTC.\n")
