# 03 - Supprimer les doublons exacts et reperer les contradictions.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
meteo <- as.data.frame(readRDS(file.path(dossier, "synop_variables_brutes.rds")))
variables <- c("t", "tn12", "tn24", "tx12", "tx24", "rr1", "rr3", "rr6", "rr12", "rr24")
colonnes <- setdiff(names(meteo), "fichier_source")

# Comparer seulement les lignes dont le couple station/date est repete.
cle <- paste(meteo$geo_id_wmo, as.numeric(meteo$date_utc))
repete <- duplicated(cle) | duplicated(cle, fromLast = TRUE)
a_retirer <- rep(FALSE, nrow(meteo))
a_retirer[repete] <- duplicated(meteo[repete, colonnes])
x <- meteo[!a_retirer, ]
cat(sum(a_retirer), "doublons exacts retires.\n")

cle <- paste(x$geo_id_wmo, as.numeric(x$date_utc))
repete <- duplicated(cle) | duplicated(cle, fromLast = TRUE)
groupes <- split(which(repete), cle[repete])
diagnostic <- x[integer(0), c("geo_id_wmo", "date_utc")]
for (v in variables) diagnostic[[v]] <- integer(0)
for (lignes in groupes) {
  ligne <- x[lignes[1], c("geo_id_wmo", "date_utc")]
  for (v in variables) ligne[[v]] <- length(unique(na.omit(x[lignes, v])))
  diagnostic <- rbind(diagnostic, ligne)
}
diagnostic$conflit <- rowSums(diagnostic[, variables] > 1) > 0
row.names(x) <- NULL
saveRDS(x, file.path(dossier, "synop_sans_doublons_exacts.rds"))
write.csv(diagnostic, file.path(dossier, "diagnostic_conflits.csv"), row.names = FALSE, na = "")
cat(nrow(diagnostic), "couples repetes, dont", sum(diagnostic$conflit), "avec conflit.\n")
