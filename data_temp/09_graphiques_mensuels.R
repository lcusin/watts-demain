# 09 - Graphiques mensuels : une couleur par annee.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
library(ggplot2)
x <- as.data.frame(readRDS(file.path(dossier, "moyennes_reseau_horaires.rds")))
x <- x[order(x$date_utc), ]
stopifnot(nrow(x) > 0, !anyNA(x$date_utc), !anyDuplicated(x$date_utc),
          all(as.numeric(x$date_utc) %% 3600 == 0), all(diff(as.numeric(x$date_utc)) == 3600))
dir.create(sortie, recursive = TRUE, showWarnings = FALSE)

# Calculer la moyenne de temperature et la somme de pluie de chaque mois.
liste_mois <- list()
for (v in c("temperature_c", "precipitation_1h_mm")) {
  dates <- x$date_utc
  if (v == "precipitation_1h_mm") dates <- dates - 3600 # Pluie de minuit : mois precedent.
  groupes <- split(seq_len(nrow(x)), format(dates, "%Y-%m-01", tz = "UTC"))
  for (mois in names(groupes)) {
    lignes <- groupes[[mois]]
    valeurs <- x[[paste0(v, "_moyenne")]][lignes]
    n <- sum(!is.na(valeurs))
    valeur <- if (v == "temperature_c") mean(valeurs, na.rm = TRUE) else sum(valeurs, na.rm = TRUE)
    if (n == 0) valeur <- NA_real_
    debut <- as.Date(mois)
    suivant <- as.Date(format(debut + 32, "%Y-%m-01"))
    attendues <- as.integer(suivant - debut) * 24L
    liste_mois[[paste(v, mois)]] <- data.frame(variable = v, mois_debut = debut,
      nb_heures = length(lignes), nb_heures_valides = n,
      heures_attendues = attendues, valeur = valeur, annee = format(debut, "%Y"),
      mois = as.integer(format(debut, "%m")), couverture_horaire_pct = 100 * n / attendues,
      mois_entier = length(lignes) == attendues,
      completude = if (n == attendues) "Toutes les heures" else "Heures manquantes")
  }
}
mensuel <- do.call(rbind, liste_mois)
mensuel <- mensuel[order(mensuel$variable, mensuel$mois_debut), ]
mensuel$affiche <- mensuel$mois_entier & mensuel$couverture_horaire_pct >= 95 & mensuel$annee >= "2012"
write.csv(mensuel, file.path(sortie, "resume_mensuel.csv"), row.names = FALSE, na = "")
annees <- sort(unique(mensuel$annee[mensuel$annee >= "2012"]))
couleurs <- setNames(hcl.colors(length(annees), "Dark 3"), annees)
mois_fr <- c("Jan", "F\u00e9v", "Mar", "Avr", "Mai", "Juin", "Juil", "Ao\u00fbt", "Sep", "Oct", "Nov", "D\u00e9c")

tracer <- function(variable, titre, axe, sous_titre, fichier) {
  donnees <- mensuel[mensuel$variable == variable & mensuel$annee >= "2012", ]
  donnees$valeur[!donnees$affiche] <- NA # Couper les lignes aux mois exclus.
  g <- ggplot(donnees, aes(mois, valeur, color = annee, group = annee)) +
    geom_line(linewidth = 0.8, na.rm = TRUE) +
    geom_point(aes(shape = completude), size = 2, na.rm = TRUE) +
    scale_color_manual(values = couleurs, breaks = annees) +
    scale_shape_manual(values = c("Toutes les heures" = 16, "Heures manquantes" = 1)) +
    scale_x_continuous(breaks = 1:12, labels = mois_fr, limits = c(1, 12)) +
    labs(title = titre, subtitle = sous_titre, x = NULL, y = axe, color = "Ann\u00e9e", shape = NULL,
         caption = paste0("Moyennes du r\u00e9seau, poids \u00e9gaux ; calendrier UTC.\n",
           "Mois tronqu\u00e9s ou < 95 % d'heures disponibles : non affich\u00e9s.\n",
           "Point creux : heures manquantes (cumul de pluie partiel, non corrig\u00e9).")) +
    theme_minimal(base_size = 12) +
    theme(panel.grid.minor = element_blank(), plot.title = element_text(face = "bold"),
          plot.caption = element_text(hjust = 0)) +
    guides(color = guide_legend(order = 1), shape = guide_legend(order = 2))
  ggsave(file.path(sortie, fichier), g, width = 12, height = 7, dpi = 180, bg = "white")
  if (interactive()) print(g)
  invisible(g)
}
graphe_temperature <- tracer("temperature_c", "Temp\u00e9rature moyenne mensuelle", "Temp\u00e9rature (\u00b0C)",
  "Moyenne des temp\u00e9ratures horaires du r\u00e9seau", "temperature_mensuelle.png")
graphe_pluie <- tracer("precipitation_1h_mm", "Pr\u00e9cipitations mensuelles", "Cumul disponible (mm)",
  "Somme des pr\u00e9cipitations horaires moyennes du r\u00e9seau", "precipitations_mensuelles.png")
cat("Graphiques et tableau mensuel :", sortie, "\n")
