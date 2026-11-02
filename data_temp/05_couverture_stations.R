# 05 - Couverture annuelle sur une grille de trois heures.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
meteo <- as.data.frame(readRDS(file.path(dossier, "synop_metropole_nettoye.rds")))
stations <- read.csv(file.path(dossier, "stations_metropole.csv"), colClasses = c(geo_id_wmo = "character"))
stopifnot(nrow(meteo) > 0, !anyNA(meteo$date_utc),
          !anyDuplicated(meteo[, c("geo_id_wmo", "date_utc")]),
          all(as.numeric(meteo$date_utc) %% 10800 == 0))
print(table(format(meteo$date_utc, "%H:%M:%S", tz = "UTC")))
fin <- max(meteo$date_utc)
grille <- seq(as.POSIXct("2012-01-01", tz = "UTC"), fin, by = "3 hours")
attendus <- as.data.frame(table(format(grille, "%Y", tz = "UTC")))
names(attendus) <- c("annee", "nb_attendus")
attendus$annee <- as.integer(as.character(attendus$annee))

# Compter les valeurs presentes, puis ajouter les annees entierement absentes.
comptages <- data.frame(geo_id_wmo = meteo$geo_id_wmo,
  annee = as.integer(format(meteo$date_utc, "%Y", tz = "UTC")), nb_observations = 1L,
  nb_temperature = as.integer(!is.na(meteo$t)), nb_rr1 = as.integer(!is.na(meteo$rr1)),
  nb_rr3 = as.integer(!is.na(meteo$rr3)))
comptages <- aggregate(comptages[, 3:6], comptages[, 1:2], sum)
couverture <- expand.grid(geo_id_wmo = unique(meteo$geo_id_wmo), annee = attendus$annee,
                          stringsAsFactors = FALSE)
couverture <- merge(couverture, comptages, by = c("geo_id_wmo", "annee"), all.x = TRUE)
couverture[is.na(couverture)] <- 0
couverture <- merge(couverture, attendus, by = "annee")
for (v in c("observations", "temperature", "rr1", "rr3")) {
  couverture[[paste0("couverture_", v)]] <- 100 * couverture[[paste0("nb_", v)]] / couverture$nb_attendus
}
noms <- aggregate(name ~ geo_id_wmo, stations, function(z) paste(sort(unique(z)), collapse = " / "))
names(noms)[2] <- "nom"
couverture <- merge(couverture, noms, by = "geo_id_wmo", all.x = TRUE)
couverture <- couverture[order(couverture$geo_id_wmo, couverture$annee), ]

# Une colonne par annee pour lire facilement la couverture de temperature.
tableau <- reshape(couverture[, c("geo_id_wmo", "nom", "annee", "couverture_temperature")],
                   idvar = c("geo_id_wmo", "nom"), timevar = "annee", direction = "wide")
names(tableau) <- sub("couverture_temperature.", "", names(tableau), fixed = TRUE)
write.csv(couverture, file.path(dossier, "couverture_stations_par_annee.csv"), row.names = FALSE, na = "")
write.csv(tableau, file.path(dossier, "couverture_temperature_tableau.csv"), row.names = FALSE, na = "")
ids <- couverture$geo_id_wmo[couverture$annee == 2012 & couverture$nb_observations > 0]
affichage <- tableau[tableau$geo_id_wmo %in% ids, ]
affichage[, -(1:2)] <- round(affichage[, -(1:2)], 1)
print(affichage, row.names = FALSE)
cat("Couverture arretee au", format(fin, tz = "UTC"), "UTC.\n")
