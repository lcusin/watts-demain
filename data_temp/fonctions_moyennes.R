# Statistiques communes aux scripts 07 et 08, avec uniquement du R de base.
# Les quantiles decrivent les differences entre stations, pas un IC de la moyenne.
resumer_reseau <- function(valeurs, dates, grille, nb_stations, estimees = rep(FALSE, length(valeurs))) {
  position <- match(dates, grille)
  stopifnot(!anyNA(position), all(is.na(valeurs) | is.finite(valeurs)))
  groupes <- split(valeurs, position)

  calculer <- function(z) {
    z <- z[!is.na(z)]
    n <- length(z)
    moyenne <- if (n > 0) mean(z) else NA_real_
    ecart_type <- if (n > 1) sd(z) else NA_real_
    bornes <- if (n > 1) quantile(z, c(0.025, 0.975), names = FALSE) else c(NA, NA)
    c(n_stations = n, moyenne = moyenne, ecart_type_spatial = ecart_type,
      q025_spatial = bornes[1], q975_spatial = bornes[2])
  }

  # Une ligne par date attendue, meme sans aucune observation.
  resultat <- data.frame(date_utc = grille, n_stations = 0L, moyenne = NA_real_,
                        ecart_type_spatial = NA_real_, q025_spatial = NA_real_, q975_spatial = NA_real_)
  if (length(groupes) > 0) {
    statistiques <- t(sapply(groupes, calculer))
    lignes <- as.integer(rownames(statistiques))
    resultat[lignes, colnames(statistiques)] <- statistiques
  }
  resultat$n_stations <- as.integer(resultat$n_stations)
  resultat$n_estimees <- 0L
  effectifs <- tapply(!is.na(valeurs) & estimees, position, sum)
  resultat$n_estimees[as.integer(names(effectifs))] <- as.integer(effectifs)
  resultat$n_observees <- resultat$n_stations - resultat$n_estimees
  resultat$stations_selectionnees <- nb_stations
  resultat$couverture_stations_pct <- 100 * resultat$n_stations / nb_stations
  resultat$moins_de_80pct_stations <- resultat$couverture_stations_pct < 80
  resultat
}
