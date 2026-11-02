# 04 - Garder la metropole et une seule ligne par station/date.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
x <- as.data.frame(readRDS(file.path(dossier, "synop_sans_doublons_exacts.rds")))
x <- x[grepl("^07[0-9]{3}$", x$geo_id_wmo), ] # Filtre de notre inventaire, Corse incluse.
stopifnot(nrow(x) > 0)
variables <- c("t", "tn12", "tn24", "tx12", "tx24", "rr1", "rr3", "rr6", "rr12", "rr24")
stations <- unique(x[, c("geo_id_wmo", "geo_id_wigos", "name", "lat", "lon")])
cle <- paste(x$geo_id_wmo, as.numeric(x$date_utc))
repete <- duplicated(cle) | duplicated(cle, fromLast = TRUE)
versions <- x[repete, ]
versions$N <- as.integer(ave(rep(1L, sum(repete)), cle[repete], FUN = sum))
groupes <- split(which(repete), cle[repete])

# Garder directement les lignes uniques ; corriger seulement les repetitions.
meteo <- x[!repete, c("geo_id_wmo", "date_utc", variables)]
meteo$nb_versions <- 1L
meteo$conflit_present <- FALSE
corrections <- list()
conflits <- data.frame(geo_id_wmo = character(), date_utc = as.POSIXct(character(), tz = "UTC"),
                       nb_valeurs = integer(), valeurs = character(), variable = character())
for (g in names(groupes)) {
  lignes <- groupes[[g]]
  ligne <- x[lignes[1], c("geo_id_wmo", "date_utc", variables)]
  ligne$nb_versions <- length(lignes)
  ligne$conflit_present <- FALSE
  for (v in variables) {
    valeurs <- sort(unique(na.omit(x[lignes, v])))
    ligne[[v]] <- if (length(valeurs) == 1) valeurs else NA_real_
    if (length(valeurs) > 1) {
      ligne$conflit_present <- TRUE
      conflits <- rbind(conflits, data.frame(geo_id_wmo = ligne$geo_id_wmo,
        date_utc = ligne$date_utc, nb_valeurs = length(valeurs),
        valeurs = paste(valeurs, collapse = " | "), variable = v))
    }
  }
  corrections[[g]] <- ligne
}
if (length(corrections) > 0) meteo <- rbind(meteo, do.call(rbind, corrections))
meteo <- meteo[order(meteo$geo_id_wmo, meteo$date_utc), ]
rownames(meteo) <- NULL
saveRDS(meteo, file.path(dossier, "synop_metropole_nettoye.rds"))
saveRDS(versions, file.path(dossier, "versions_repetees_metropole.rds"))
write.csv(stations, file.path(dossier, "stations_metropole.csv"), row.names = FALSE, na = "")
write.csv(conflits, file.path(dossier, "conflits_metropole.csv"), row.names = FALSE, na = "")
cat(nrow(meteo), "observations ;", sum(meteo$conflit_present), "couples avec conflit.\n")
