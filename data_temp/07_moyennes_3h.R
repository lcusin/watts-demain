source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 07 - Moyennes du réseau toutes les 3 h et dispersion géographique.
# À lancer après 06. Chaque station disponible a le même poids.
# Les quantiles 2,5 et 97,5 % ne sont PAS un IC de la moyenne nationale.
# Ils décrivent les différences entre stations, sans supposer leur indépendance.
library(data.table)

x <- readRDS(file.path(dossier, "synop_stations_selectionnees.rds"))
stations <- fread(file.path(dossier, "stations_selectionnees.csv"),
                  colClasses = c(geo_id_wmo = "character"))
nb_stations <- nrow(stations)
stopifnot(nb_stations > 0, nrow(x) > 0,
          !anyNA(x$date_utc), !anyNA(stations$geo_id_wmo),
          anyDuplicated(stations$geo_id_wmo) == 0,
          setequal(x$geo_id_wmo, stations$geo_id_wmo),
          all(is.na(x$t) | is.finite(x$t)), all(is.na(x$rr3) | is.finite(x$rr3)),
          anyDuplicated(x, by = c("geo_id_wmo", "date_utc")) == 0,
          all(as.numeric(x$date_utc) %% (3 * 3600) == 0))

# Unités SYNOP : t en K, rr3 en mm sur les 3 heures précédant date_utc.
# https://donneespubliques.meteofrance.fr/client/document/parametres-inclus-dans-les-fichiers-de-donnees-synop_283.pdf
# Code -0.1 = traces ; approximation à 0 mm, pas une absence de mesure.
# https://wetterdienst.readthedocs.io/en/latest/data/special_values.html
x[, temperature_c := t - 273.15]
x[, trace_pluie := !is.na(rr3) & rr3 == -0.1]
x[, precipitation_3h_mm := fifelse(trace_pluie, 0, rr3)]
stopifnot(all(x$precipitation_3h_mm >= 0, na.rm = TRUE))

# Garder aussi les échéances entièrement absentes, sans interpolation.
grille <- data.table(date_utc = seq(as.POSIXct("2012-01-01", tz = "UTC"),
                                   max(x$date_utc), by = "3 hours"))

resumer <- function(z) {
  z <- z[!is.na(z)]
  n <- length(z)
  bornes <- if (n >= 2) quantile(z, c(0.025, 0.975), names = FALSE, type = 7) else c(NA_real_, NA_real_)
  list(n_stations = n,
       moyenne = if (n > 0) mean(z) else NA_real_,
       ecart_type_spatial = if (n >= 2) sd(z) else NA_real_,
       q025_spatial = bornes[1], q975_spatial = bornes[2])
}

resultats <- rbindlist(lapply(c("temperature_c", "precipitation_3h_mm"), function(v) {
  bilan <- x[, c(resumer(get(v)), list(n_traces_pluie = sum(trace_pluie))), by = date_utc]
  bilan <- merge(grille, bilan, by = "date_utc", all.x = TRUE)
  bilan[is.na(n_stations), `:=`(n_stations = 0L, n_traces_pluie = 0L)]
  if (v == "temperature_c") bilan[, n_traces_pluie := NA_integer_]
  bilan[, `:=`(variable = v, stations_selectionnees = nb_stations,
               couverture_stations_pct = 100 * n_stations / nb_stations)]
  # Repère descriptif de disponibilité, pas une garantie de représentativité.
  bilan[, moins_de_80pct_stations := couverture_stations_pct < 80]
  bilan
}))

setorder(resultats, date_utc, variable)

fwrite(resultats, file.path(dossier, "moyennes_reseau_3h.csv"))
saveRDS(resultats, file.path(dossier, "moyennes_reseau_3h.rds"))
cat(nrow(grille), "échéances de 3 heures ;", nb_stations, "stations sélectionnées.\n")
cat(sum(x$trace_pluie), "traces de pluie représentées par 0 mm.\n")
print(resultats[, .(nb_echeances = .N, minimum_stations = min(n_stations),
                    echeances_sous_80pct = sum(moins_de_80pct_stations)), by = variable])
print(head(resultats, 6))
