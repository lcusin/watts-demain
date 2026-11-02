source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 09 - Moyennes mensuelles de temperature et cumuls mensuels de pluie.
# Apres 08 ; installer ggplot2 si besoin : install.packages("ggplot2")
library(data.table)
library(ggplot2)
x <- readRDS(file.path(dossier, "moyennes_reseau_horaires.rds"))

dir.create(sortie, recursive = TRUE, showWarnings = FALSE)
variables <- c("temperature_c", "precipitation_1h_mm")
stopifnot(setequal(unique(x$variable), variables), !anyNA(x$date_utc),
          anyDuplicated(x, by = c("variable", "date_utc")) == 0,
          all(as.numeric(x$date_utc) %% 3600 == 0),
          all(x[, .(reguliere = all(diff(sort(as.numeric(date_utc))) == 3600)), by = variable]$reguliere))

agreger_mois <- function(donnees) {
  z <- copy(donnees)
  # Pluie datee en fin d'intervalle : 1er du mois a 00 h -> mois precedent.
  z[, date_mois := date_utc - 3600 * (variable == "precipitation_1h_mm")]
  z[, mois_debut := as.Date(format(date_mois, "%Y-%m-01", tz = "UTC"))]
  m <- z[, .(nb_heures = .N, nb_heures_valides = sum(!is.na(moyenne)),
              nb_heures_sous_80pct_stations = sum(moins_de_80pct_stations),
              total = sum(moyenne, na.rm = TRUE)), by = .(variable, mois_debut)]
  m[, heures_attendues := as.integer(as.Date(format(mois_debut + 32, "%Y-%m-01")) - mois_debut) * 24L]
  m[, valeur := fifelse(variable == "temperature_c", total / nb_heures_valides, total)]
  m[nb_heures_valides == 0, valeur := NA_real_]
  m[, `:=`(annee = format(mois_debut, "%Y"), mois = as.integer(format(mois_debut, "%m")),
           couverture_horaire_pct = 100 * nb_heures_valides / heures_attendues,
           mois_entier = nb_heures == heures_attendues,
           completude = fifelse(nb_heures_valides == heures_attendues, "Toutes les heures", "Heures manquantes"))]
  m[, affiche := mois_entier & couverture_horaire_pct >= 95 & annee >= "2012"]
  m[, total := NULL]
  setorder(m, variable, mois_debut)
  m
}
mensuel <- agreger_mois(x)
# Garder les valeurs partielles dans le CSV, meme lorsqu'elles ne sont pas affichees.
fwrite(mensuel, file.path(sortie, "resume_mensuel.csv"))
annees <- sort(unique(mensuel[annee >= "2012", annee]))
couleurs <- setNames(hcl.colors(length(annees), "Dark 3"), annees)
mois_fr <- c("Jan", "F\u00e9v", "Mar", "Avr", "Mai", "Juin", "Juil", "Ao\u00fbt", "Sep", "Oct", "Nov", "D\u00e9c")

tracer <- function(v, titre, axe, sous_titre, fichier) {
  # Les NA coupent les lignes aux mois exclus, sans relier artificiellement les points.
  g <- ggplot(mensuel[variable == v & annee >= "2012"],
              aes(mois, fifelse(affiche, valeur, NA_real_), color = annee, group = annee)) +
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
