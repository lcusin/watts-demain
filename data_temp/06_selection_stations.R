# 06 - Retenir les stations ayant plus de 95 % de temperature ET de pluie.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
seuil <- 95
couverture <- read.csv(file.path(dossier, "couverture_stations_par_annee.csv"),
                       colClasses = c(geo_id_wmo = "character"))
stopifnot(nrow(couverture) > 0, seuil >= 0, seuil < 100,
          !anyDuplicated(couverture[, c("geo_id_wmo", "annee")]),
          all(couverture$nb_attendus > 0),
          all(couverture$nb_temperature >= 0 & couverture$nb_temperature <= couverture$nb_attendus),
          all(couverture$nb_rr3 >= 0 & couverture$nb_rr3 <= couverture$nb_attendus))

# Additionner les effectifs : ne pas faire la moyenne des pourcentages annuels.
bilan <- aggregate(cbind(nb_temperature, nb_rr3, nb_attendus) ~ geo_id_wmo + nom,
                    data = couverture, FUN = sum)
bilan$couverture_temperature <- 100 * bilan$nb_temperature / bilan$nb_attendus
bilan$couverture_rr3 <- 100 * bilan$nb_rr3 / bilan$nb_attendus
bilan$selectionnee <- bilan$couverture_temperature > seuil & bilan$couverture_rr3 > seuil
bilan <- bilan[order(-bilan$couverture_temperature), ]
selection <- bilan[bilan$selectionnee, ]
write.csv(bilan, file.path(dossier, "bilan_selection_stations.csv"), row.names = FALSE, na = "")
write.csv(selection, file.path(dossier, "stations_selectionnees.csv"), row.names = FALSE, na = "")

meteo <- as.data.frame(readRDS(file.path(dossier, "synop_metropole_nettoye.rds")))
meteo_selection <- meteo[meteo$geo_id_wmo %in% selection$geo_id_wmo,
                          c("geo_id_wmo", "date_utc", "t", "rr3")]
saveRDS(meteo_selection, file.path(dossier, "synop_stations_selectionnees.rds"))
cat(nrow(selection), "stations retenues sur", nrow(bilan), "avec une couverture >", seuil, "%.\n")
print(selection[, c("geo_id_wmo", "nom", "couverture_temperature", "couverture_rr3")], row.names = FALSE)
