source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 04 - Garder la métropole et obtenir une ligne par station/date.
library(data.table)

x <- readRDS(file.path(dossier, "synop_sans_doublons_exacts.rds"))
variables <- c("t", "tn12", "tn24", "tx12", "tx24", "rr1", "rr3", "rr6", "rr12", "rr24")

# Filtre adapté à notre inventaire métropolitain, Corse comprise.
x <- x[grepl("^07[0-9]{3}$", geo_id_wmo)]
stopifnot(nrow(x) > 0)
stations <- unique(x[, .(geo_id_wmo, geo_id_wigos, name, lat, lon)])

# Garder les versions répétées et les conflits pour pouvoir les examiner.
cles <- x[, .N, by = .(geo_id_wmo, date_utc)][N > 1]
versions <- x[cles, on = .(geo_id_wmo, date_utc)]
conflits <- rbindlist(lapply(variables, function(v) {
  bilan <- versions[, .(
    nb_valeurs = uniqueN(get(v), na.rm = TRUE),
    valeurs = paste(sort(unique(na.omit(get(v)))), collapse = " | ")
  ), by = .(geo_id_wmo, date_utc)]
  bilan <- bilan[nb_valeurs > 1]
  bilan[, variable := v]
  bilan
}))

# Une valeur disponible : la garder. Aucune ou plusieurs : NA.
valeur_unique <- function(z) {
  valeurs <- unique(z[!is.na(z)])
  if (length(valeurs) == 1) as.numeric(valeurs) else NA_real_
}
# Ne regrouper que les couples repetes : les autres lignes sont deja uniques.
meteo <- x[!cles, on = .(geo_id_wmo, date_utc),
           c("geo_id_wmo", "date_utc", variables), with = FALSE]
meteo[, nb_versions := 1L]
meteo[, (variables) := lapply(.SD, as.numeric), .SDcols = variables]
if (nrow(versions) > 0) {
  regroupement <- versions[, c(lapply(.SD, valeur_unique), list(nb_versions = .N)),
                           by = .(geo_id_wmo, date_utc), .SDcols = variables]
  meteo <- rbindlist(list(meteo, regroupement), use.names = TRUE)
}
meteo[, conflit_present := FALSE]
meteo[unique(conflits[, .(geo_id_wmo, date_utc)]),
      on = .(geo_id_wmo, date_utc), conflit_present := TRUE]
setorder(meteo, geo_id_wmo, date_utc)
stopifnot(anyDuplicated(meteo, by = c("geo_id_wmo", "date_utc")) == 0)

saveRDS(versions, file.path(dossier, "versions_repetees_metropole.rds"))
fwrite(conflits, file.path(dossier, "conflits_metropole.csv"))
fwrite(stations, file.path(dossier, "stations_metropole.csv"))
saveRDS(meteo, file.path(dossier, "synop_metropole_nettoye.rds"))
cat(nrow(meteo), "observations ;", sum(meteo$conflit_present), "couples avec conflit.\n")
print(range(meteo$date_utc))
