source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 02 - Lire les archives et inventorier les stations.
# Installation si nécessaire : install.packages(c("data.table", "R.utils"))
library(data.table)
stopifnot(requireNamespace("R.utils", quietly = TRUE))

dir.create(dossier, recursive = TRUE, showWarnings = FALSE)
fichiers <- file.path(dossier_brut,
                      paste0("synop_", 2012:2026, ".csv.gz"))
stopifnot(all(file.exists(fichiers)))
debut <- as.POSIXct("2012-01-01", tz = "UTC")
fin <- as.POSIXct("2026-10-16", tz = "UTC") # Borne exclusive.

colonnes <- c("geo_id_wmo", "geo_id_wigos", "name", "lat", "lon",
              "validity_time", "reference_time", "insert_time",
              "t", "tn12", "tn24", "tx12", "tx24",
              "rr1", "rr3", "rr6", "rr12", "rr24")

lire_archive <- function(fichier) {
  cat("Lecture :", basename(fichier), "\n")
  stopifnot(all(colonnes %in% names(fread(fichier, nrows = 0))))
  x <- fread(fichier, select = colonnes, na.strings = c("", "NA", "mq"),
             colClasses = list(character = c("geo_id_wmo", "geo_id_wigos", "name",
                                              "validity_time", "reference_time", "insert_time")))
  for (col in c("geo_id_wmo", "geo_id_wigos", "name")) {
    set(x, j = col, value = trimws(x[[col]]))
  }
  x[, date_utc := as.POSIXct(validity_time, format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")]
  stopifnot(!anyNA(x$date_utc), !anyNA(x$geo_id_wmo), all(nzchar(x$geo_id_wmo)))
  x <- x[date_utc >= debut & date_utc < fin]
  x[, fichier_source := basename(fichier)]
  x
}

meteo <- rbindlist(lapply(fichiers, lire_archive))
stopifnot(nrow(meteo) > 0)
setorder(meteo, geo_id_wmo, date_utc)

# Les doublons sont signalés ici, mais pas encore supprimés.
doublons <- meteo[, .N, by = .(geo_id_wmo, date_utc)][N > 1]
stations <- meteo[, .(
  noms = paste(sort(unique(name[!is.na(name)])), collapse = " / "),
  latitude = lat[1], longitude = lon[1],
  premiere_date = min(date_utc), derniere_date = max(date_utc),
  nb_lignes = .N, nb_dates_distinctes = uniqueN(date_utc),
  nb_temperature = sum(!is.na(t)),
  nb_precipitation_1h = sum(!is.na(rr1)),
  nb_precipitation_3h = sum(!is.na(rr3))
), by = geo_id_wmo]
# Les coordonnées ci-dessus sont celles de la première ligne de chaque station.

saveRDS(meteo, file.path(dossier, "synop_variables_brutes.rds"))
fwrite(stations, file.path(dossier, "inventaire_stations.csv"))
fwrite(doublons, file.path(dossier, "doublons_station_date.csv"))
cat(nrow(meteo), "lignes ;", nrow(stations), "stations ;",
    nrow(doublons), "couples station/date répétés.\n")
print(range(meteo$date_utc))
