source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 08 - Reconstruire les heures par station, puis calculer les moyennes du réseau.
# À lancer depuis le projet, après 06 (07 n'a pas besoin d'être relancé).
# Reconstruction rétrospective : les heures intermédiaires utilisent le relevé suivant.
# Les dates source sont des dates de mesure, PAS des dates de publication.
library(data.table)

x <- readRDS(file.path(dossier, "synop_stations_selectionnees.rds"))
stations <- fread(file.path(dossier, "stations_selectionnees.csv"),
                  colClasses = c(geo_id_wmo = "character"))
nb_stations <- nrow(stations)
stopifnot(nrow(x) > 0, nb_stations > 0,
          !anyNA(x$date_utc), !anyNA(stations$geo_id_wmo),
          anyDuplicated(stations$geo_id_wmo) == 0,
          setequal(x$geo_id_wmo, stations$geo_id_wmo),
          all(is.na(x$t) | is.finite(x$t)), all(is.na(x$rr3) | is.finite(x$rr3)),
          anyDuplicated(x, by = c("geo_id_wmo", "date_utc")) == 0,
          all(as.numeric(x$date_utc) %% 10800 == 0))
setorder(x, geo_id_wmo, date_utc)
debut <- as.POSIXct("2012-01-01", tz = "UTC")
fin <- max(x$date_utc)

# 1. Température : garder les mesures et interpoler seulement les intervalles de 3 h.
x[, temperature_c := t - 273.15]
x[, `:=`(date_suivante = shift(date_utc, type = "lead"),
          temperature_suivante = shift(temperature_c, type = "lead")), by = geo_id_wmo]
paires <- x[!is.na(temperature_c) & !is.na(temperature_suivante) &
              as.numeric(date_suivante) - as.numeric(date_utc) == 10800]
temperature <- rbindlist(c(list(x[, .(
  geo_id_wmo, date_utc, temperature_c, temperature_interpolee = FALSE,
  source_temperature_fin_utc = date_utc
)]), lapply(1:2, function(h) paires[, .(
  geo_id_wmo, date_utc = date_utc + h * 3600,
  temperature_c = temperature_c + h / 3 * (temperature_suivante - temperature_c),
  temperature_interpolee = TRUE, source_temperature_fin_utc = date_suivante
)])))

# 2. Pluie : cumul rr3 / 3 pour chacune des trois heures précédentes.
# Date en FIN d'intervalle : 03 h désigne la pluie de 02 à 03 h.
# Comme en 07, les traces (-0.1) sont approximées à 0 mm, et restent signalées.
x[, trace_pluie := !is.na(rr3) & rr3 == -0.1]
x[, pluie_3h_mm := fifelse(trace_pluie, 0, rr3)]
stopifnot(all(x$pluie_3h_mm >= 0, na.rm = TRUE))
pluie <- rbindlist(lapply(0:2, function(h) x[, .(
  geo_id_wmo, date_utc = date_utc - h * 3600,
  precipitation_1h_mm = pluie_3h_mm / 3,
  trace_pluie, source_pluie_fin_utc = date_utc
)]))
# Vérifier la conservation des cumuls avant de couper aux bornes de la période.
cumuls <- pluie[, .(reconstitue = sum(precipitation_1h_mm)),
                 by = .(geo_id_wmo, source_pluie_fin_utc)]
controle <- merge(x[, .(geo_id_wmo, source_pluie_fin_utc = date_utc, pluie_3h_mm)],
                  cumuls, by = c("geo_id_wmo", "source_pluie_fin_utc"))
stopifnot(isTRUE(all.equal(controle$pluie_3h_mm, controle$reconstitue)))
rm(cumuls, controle, paires)

# 3. Tableau horaire par station. Aucune extrapolation ou longue lacune comblée.
horaire <- merge(temperature, pluie, by = c("geo_id_wmo", "date_utc"), all = TRUE)
horaire <- horaire[date_utc >= debut & date_utc <= fin]
stopifnot(anyDuplicated(horaire, by = c("geo_id_wmo", "date_utc")) == 0)
saveRDS(horaire, file.path(dossier, "synop_stations_horaires.rds"))
rm(temperature, pluie)

# 4. Moyennes et dispersion spatiale recalculées à partir des valeurs des stations.
# Quantiles empiriques : PAS un IC de la moyenne ni une incertitude d'interpolation.
resumer <- function(z) {
  z <- z[!is.na(z)]
  n <- length(z)
  q <- if (n >= 2) quantile(z, c(.025, .975), names = FALSE) else c(NA_real_, NA_real_)
  list(n_stations = n, moyenne = if (n > 0) mean(z) else NA_real_,
       ecart_type_spatial = if (n >= 2) sd(z) else NA_real_,
       q025_spatial = q[1], q975_spatial = q[2])
}
grille <- data.table(date_utc = seq(debut, fin, by = "hour"))
resultats <- rbindlist(lapply(c("temperature_c", "precipitation_1h_mm"), function(v) {
  bilan <- horaire[, c(resumer(get(v)), list(n_estimees =
    if (v == "temperature_c") sum(!is.na(temperature_c) & temperature_interpolee, na.rm = TRUE)
    else sum(!is.na(precipitation_1h_mm)))), by = date_utc]
  bilan <- merge(grille, bilan, by = "date_utc", all.x = TRUE)
  bilan[is.na(n_stations), `:=`(n_stations = 0L, n_estimees = 0L)]
  bilan[, `:=`(variable = v, n_observees = n_stations - n_estimees,
               stations_selectionnees = nb_stations,
               couverture_stations_pct = 100 * n_stations / nb_stations)]
  bilan[, moins_de_80pct_stations := couverture_stations_pct < 80]
  bilan
}))
setorder(resultats, date_utc, variable)
fwrite(resultats, file.path(dossier, "moyennes_reseau_horaires.csv"))
saveRDS(resultats, file.path(dossier, "moyennes_reseau_horaires.rds"))
cat(nrow(grille), "heures ;", nb_stations, "stations. Cumuls de pluie vérifiés.\n")
print(resultats[, .(heures_sans_donnees = sum(n_stations == 0),
                    heures_sous_80pct = sum(moins_de_80pct_stations)), by = variable])
print(head(resultats, 8))
