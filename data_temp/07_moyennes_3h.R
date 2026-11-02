# 07 - Moyennes toutes les trois heures et dispersion entre stations.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
source(file.path(racine_scripts, "fonctions_moyennes.R"), local = TRUE)
x <- as.data.frame(readRDS(file.path(dossier, "synop_stations_selectionnees.rds")))
stations <- read.csv(file.path(dossier, "stations_selectionnees.csv"), colClasses = c(geo_id_wmo = "character"))
nb_stations <- nrow(stations)
stopifnot(nb_stations > 0, nrow(x) > 0, !anyNA(x$date_utc), !anyNA(stations$geo_id_wmo),
          !anyDuplicated(stations$geo_id_wmo), setequal(x$geo_id_wmo, stations$geo_id_wmo),
          !anyDuplicated(x[, c("geo_id_wmo", "date_utc")]), all(as.numeric(x$date_utc) %% 10800 == 0))

# t est en kelvins. -0.1 indique des traces de pluie, approximees a 0 mm.
# Sources : donneespubliques.meteofrance.fr (parametres SYNOP) ;
# https://wetterdienst.readthedocs.io/en/latest/data/special_values.html
x$temperature_c <- x$t - 273.15
x$trace_pluie <- !is.na(x$rr3) & x$rr3 == -0.1
x$precipitation_3h_mm <- x$rr3
x$precipitation_3h_mm[x$trace_pluie] <- 0
stopifnot(all(x$precipitation_3h_mm >= 0, na.rm = TRUE))
grille <- seq(as.POSIXct("2012-01-01", tz = "UTC"), max(x$date_utc), by = "3 hours")
traces <- tapply(x$trace_pluie, match(x$date_utc, grille), sum)

bilans <- list()
for (v in c("temperature_c", "precipitation_3h_mm")) {
  bilan <- resumer_reseau(x[[v]], x$date_utc, grille, nb_stations)
  bilan$n_estimees <- NULL
  bilan$n_observees <- NULL
  bilan$variable <- v
  bilan$n_traces_pluie <- NA_integer_
  if (v == "precipitation_3h_mm") {
    bilan$n_traces_pluie <- 0L
    bilan$n_traces_pluie[as.integer(names(traces))] <- as.integer(traces)
  }
  bilans[[v]] <- bilan
}
resultats <- do.call(rbind, bilans)
resultats <- resultats[order(resultats$date_utc, resultats$variable), ]
rownames(resultats) <- NULL
saveRDS(resultats, file.path(dossier, "moyennes_reseau_3h.rds"))
write.csv(resultats, file.path(dossier, "moyennes_reseau_3h.csv"), row.names = FALSE, na = "")
cat(length(grille), "echeances ;", nb_stations, "stations.\n")
print(head(resultats))
