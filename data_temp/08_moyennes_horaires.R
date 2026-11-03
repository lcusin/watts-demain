# 08 - Reconstruction horaire par station, puis moyennes du reseau.
# Methode retrospective : les heures intermediaires utilisent la mesure suivante.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
x <- as.data.frame(readRDS(file.path(dossier, "synop_stations_selectionnees.rds")))
stations <- read.csv(file.path(dossier, "stations_selectionnees.csv"), colClasses = c(geo_id_wmo = "character"))
nb_stations <- nrow(stations)
stopifnot(nrow(x) > 0, nb_stations > 0, !anyNA(x$date_utc), !anyNA(stations$geo_id_wmo),
          !anyDuplicated(stations$geo_id_wmo), setequal(x$geo_id_wmo, stations$geo_id_wmo),
          !anyDuplicated(x[, c("geo_id_wmo", "date_utc")]), all(as.numeric(x$date_utc) %% 10800 == 0),
          all(is.na(x$t) | is.finite(x$t)), all(is.na(x$rr3) | is.finite(x$rr3)))
debut <- as.POSIXct("2012-01-01", tz = "UTC")
fin <- max(x$date_utc)
liste_horaire <- list()

for (id in stations$geo_id_wmo) {
  z <- x[x$geo_id_wmo == id, ]
  z <- z[order(z$date_utc), ]
  z$t <- z$t - 273.15
  temperature <- data.frame(geo_id_wmo = id, date_utc = z$date_utc, temperature_c = z$t,
                            temperature_interpolee = FALSE, source_temperature_fin_utc = z$date_utc)

  # Interpoler seulement entre deux mesures valides separees de trois heures.
  paires <- which(diff(as.numeric(z$date_utc)) == 10800 &
                   !is.na(head(z$t, -1)) & !is.na(tail(z$t, -1)))
  for (h in 1:2) {
    ajout <- temperature[paires, ]
    ajout$date_utc <- z$date_utc[paires] + h * 3600
    ajout$temperature_c <- z$t[paires] + h / 3 * (z$t[paires + 1] - z$t[paires])
    ajout$temperature_interpolee <- rep(TRUE, length(paires))
    ajout$source_temperature_fin_utc <- z$date_utc[paires + 1]
    temperature <- rbind(temperature, ajout)
  }

  # Repartir le cumul sur les trois heures precedentes, datees en fin d'intervalle.
  trace <- !is.na(z$rr3) & z$rr3 == -0.1
  z$rr3[trace] <- 0
  stopifnot(all(z$rr3 >= 0, na.rm = TRUE))
  pluie <- list()
  for (h in 0:2) {
    pluie[[h + 1]] <- data.frame(geo_id_wmo = id, date_utc = z$date_utc - h * 3600,
      precipitation_1h_mm = z$rr3 / 3, trace_pluie = trace, source_pluie_fin_utc = z$date_utc)
  }
  pluie <- do.call(rbind, pluie)
  station <- merge(temperature, pluie, by = c("geo_id_wmo", "date_utc"), all = TRUE)
  liste_horaire[[id]] <- station[station$date_utc >= debut & station$date_utc <= fin, ]
}
horaire <- do.call(rbind, liste_horaire)
horaire <- horaire[order(horaire$geo_id_wmo, horaire$date_utc), ]
rownames(horaire) <- NULL
stopifnot(!anyDuplicated(horaire[, c("geo_id_wmo", "date_utc")]))
saveRDS(horaire, file.path(dossier, "synop_stations_horaires.rds"))
rm(liste_horaire)

# Une seule ligne par heure, avec les deux series de statistiques cote a cote.
grille <- seq(debut, fin, by = "hour")
resultats <- data.frame(date_utc = grille)
position <- match(horaire$date_utc, grille)
for (v in c("temperature_c", "precipitation_1h_mm")) {
  groupes <- split(horaire[[v]], position)
  moyennes <- sapply(groupes, mean, na.rm = TRUE)
  ecarts <- sapply(groupes, sd, na.rm = TRUE)
  moyennes[is.nan(moyennes)] <- NA_real_
  lignes <- as.integer(names(groupes))
  resultats[[paste0(v, "_moyenne")]] <- NA_real_
  resultats[[paste0(v, "_ecart_type")]] <- NA_real_
  resultats[lignes, paste0(v, "_moyenne")] <- moyennes
  resultats[lignes, paste0(v, "_ecart_type")] <- ecarts
}
saveRDS(resultats, file.path(dossier, "moyennes_reseau_horaires.rds"))

export <- resultats
export$date_utc <- format(export$date_utc, "%Y-%m-%d %H:%M:%S", tz = "UTC")
write.csv(export, file.path(dossier, "moyennes_reseau_horaires.csv"),
          row.names = FALSE, na = "")

cat(nrow(resultats), "heures ;", nb_stations, "stations.\n")
print(head(export))
