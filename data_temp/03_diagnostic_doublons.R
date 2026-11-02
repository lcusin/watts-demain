source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 03 - Retirer les doublons exacts et repérer les valeurs contradictoires.
library(data.table)

meteo <- readRDS(file.path(dossier, "synop_variables_brutes.rds"))
variables <- c("t", "tn12", "tn24", "tx12", "tx24", "rr1", "rr3", "rr6", "rr12", "rr24")

# Deux lignes identiques peuvent provenir de fichiers différents.
colonnes <- setdiff(names(meteo), "fichier_source")
x <- unique(meteo, by = colonnes)
cat(nrow(meteo) - nrow(x), "doublons exacts retirés.\n")

cles <- x[, .N, by = .(geo_id_wmo, date_utc)][N > 1]
repetitions <- x[cles, on = .(geo_id_wmo, date_utc)]

# Compter les valeurs distinctes disponibles : 12 + NA n'est pas un conflit.
diagnostic <- repetitions[, lapply(.SD, uniqueN, na.rm = TRUE),
                          by = .(geo_id_wmo, date_utc), .SDcols = variables]
diagnostic[, conflit := rowSums(.SD > 1) > 0, .SDcols = variables]

saveRDS(x, file.path(dossier, "synop_sans_doublons_exacts.rds"))
fwrite(diagnostic, file.path(dossier, "diagnostic_conflits.csv"))
cat(nrow(diagnostic), "couples encore répétés, dont",
    sum(diagnostic$conflit), "avec conflit.\n")
