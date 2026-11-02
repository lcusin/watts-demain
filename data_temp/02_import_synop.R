# 02 - Importer les archives et inventorier les stations.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
dir.create(dossier, recursive = TRUE, showWarnings = FALSE)
debut <- as.POSIXct("2012-01-01", tz = "UTC")
fin <- as.POSIXct("2026-10-16", tz = "UTC") # Fin exclusive.
colonnes <- c("geo_id_wmo", "geo_id_wigos", "name", "lat", "lon",
              "validity_time", "reference_time", "insert_time", "t", "tn12", "tn24",
              "tx12", "tx24", "rr1", "rr3", "rr6", "rr12", "rr24")
texte <- c("geo_id_wmo", "geo_id_wigos", "name", "validity_time", "reference_time", "insert_time")
archives <- list()
for (annee in 2012:2026) {
  fichier <- file.path(dossier_brut, paste0("synop_", annee, ".csv.gz"))
  cat("Lecture :", basename(fichier), "\n")
  entete <- names(read.csv(fichier, sep = ";", nrows = 0, check.names = FALSE))
  stopifnot(all(colonnes %in% entete))
  # NULL ignore une colonne ; character preserve les zeros des identifiants.
  classes <- rep("NULL", length(entete))
  classes[entete %in% colonnes] <- "numeric"
  classes[entete %in% texte] <- "character"
  x <- read.csv(fichier, sep = ";", colClasses = classes, na.strings = c("", "NA", "mq"),
                check.names = FALSE, stringsAsFactors = FALSE)
  x <- x[, colonnes]
  for (v in c("geo_id_wmo", "geo_id_wigos", "name")) x[[v]] <- trimws(x[[v]])
  x$date_utc <- as.POSIXct(x$validity_time, format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  stopifnot(!anyNA(x$date_utc), !anyNA(x$geo_id_wmo), all(nzchar(x$geo_id_wmo)))
  x <- x[x$date_utc >= debut & x$date_utc < fin, ]
  x$fichier_source <- rep(basename(fichier), nrow(x))
  archives[[as.character(annee)]] <- x
}
meteo <- do.call(rbind, archives)
meteo <- meteo[order(meteo$geo_id_wmo, meteo$date_utc), ]
rownames(meteo) <- NULL
rm(archives, x)
stopifnot(nrow(meteo) > 0)

# Un identifiant commun permet de reperer les couples station/date repetes.
cle <- paste(meteo$geo_id_wmo, as.numeric(meteo$date_utc))
repete <- duplicated(cle) | duplicated(cle, fromLast = TRUE)
doublons <- meteo[repete, c("geo_id_wmo", "date_utc")]
doublons$N <- rep(1L, nrow(doublons))
if (nrow(doublons) > 0) doublons <- aggregate(N ~ geo_id_wmo + date_utc, doublons, sum)
doublons <- doublons[order(doublons$geo_id_wmo, doublons$date_utc), ]

inventaire <- list()
groupes <- split(seq_len(nrow(meteo)), meteo$geo_id_wmo)
for (id in names(groupes)) {
  s <- meteo[groupes[[id]], ]
  inventaire[[id]] <- data.frame(geo_id_wmo = id,
    noms = paste(sort(unique(na.omit(s$name))), collapse = " / "),
    latitude = s$lat[1], longitude = s$lon[1],
    premiere_date = min(s$date_utc), derniere_date = max(s$date_utc),
    nb_lignes = nrow(s), nb_dates_distinctes = length(unique(s$date_utc)),
    nb_temperature = sum(!is.na(s$t)), nb_precipitation_1h = sum(!is.na(s$rr1)),
    nb_precipitation_3h = sum(!is.na(s$rr3)))
}
stations <- do.call(rbind, inventaire)
saveRDS(meteo, file.path(dossier, "synop_variables_brutes.rds"))
write.csv(stations, file.path(dossier, "inventaire_stations.csv"), row.names = FALSE, na = "")
write.csv(doublons, file.path(dossier, "doublons_station_date.csv"), row.names = FALSE, na = "")
cat(nrow(meteo), "lignes ;", nrow(stations), "stations.\n")
