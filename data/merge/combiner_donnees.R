# Depuis la racine du projet : source("data/merge/combiner_donnees.R")
# Indiquer le fuseau des heures de consommation, apres verification.
# Le calendrier optionnel doit avoir une colonne date_utc (une ligne par heure).
combiner_donnees <- function(fuseau_conso, fichier_calendrier = NULL) {
  stopifnot(fuseau_conso %in% OlsonNames())
  conso <- read.csv("data/conso/processed/consommation_horaire_eco2mix_2012_2025.csv")
  meteo <- as.data.frame(readRDS("Archives/data_temp/meteo_synop_2012_2026/prepare/moyennes_reseau_horaires.rds"))

  # Interpreter les heures dans leur fuseau, puis les representer en UTC.
  conso$date_utc <- as.POSIXct(conso$horodatage, tz = fuseau_conso)
  attr(conso$date_utc, "tzone") <- "UTC"
  stopifnot(!anyNA(conso$date_utc), !anyDuplicated(conso$date_utc),
            !anyNA(meteo$date_utc), !anyDuplicated(meteo$date_utc))
  if (any(format(conso$date_utc, tz = fuseau_conso, format = "%Y-%m-%d %H:%M:%S") != conso$horodatage)) {
    stop("Heures de consommation incompatibles avec ce fuseau : verifier les changements d'heure.")
  }
  conso$horodatage <- NULL

  # Garder toutes les heures de consommation et tous les indicateurs meteo.
  donnees <- merge(conso, meteo, by = "date_utc", all.x = TRUE)

  if (!is.null(fichier_calendrier)) {
    calendrier <- read.csv(fichier_calendrier)
    calendrier$date_utc <- as.POSIXct(calendrier$date_utc, tz = "UTC")
    stopifnot(!anyNA(calendrier$date_utc), !anyDuplicated(calendrier$date_utc),
              all(donnees$date_utc %in% calendrier$date_utc))
    donnees <- merge(donnees, calendrier, by = "date_utc", all.x = TRUE)
  }
  donnees
}
