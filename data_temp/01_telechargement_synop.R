# 01 - Telecharger les archives annuelles SYNOP.
chemin <- "00_chemins.R"
if (file.exists("data_temp/00_chemins.R")) chemin <- "data_temp/00_chemins.R"
source(chemin, local = TRUE)
options(timeout = max(1800, getOption("timeout")))
dir.create(dossier_brut, recursive = TRUE, showWarnings = FALSE)
base_url <- "https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/OBS/SYNOP/"

# Controle rapide du format gzip et de l'entete CSV, pas de toute l'archive.
archive_valide <- function(fichier) {
  if (!file.exists(fichier)) return(FALSE)
  tryCatch({
    signature <- readBin(fichier, "raw", n = 2)
    if (!identical(signature, as.raw(c(31, 139)))) return(FALSE)
    connexion <- gzfile(fichier, "rt")
    on.exit(close(connexion))
    entete <- readLines(connexion, n = 1, warn = FALSE)
    length(entete) == 1 && grepl(";", entete, fixed = TRUE)
  }, error = function(e) FALSE)
}

journal <- data.frame(annee = 2012:2026, fichier = paste0("synop_", 2012:2026, ".csv.gz"),
                      statut = "deja_present", erreur = "")
for (i in seq_len(nrow(journal))) {
  fichier <- file.path(dossier_brut, journal$fichier[i])
  if (archive_valide(fichier)) next # Pas d'actualisation automatique.
  temporaire <- paste0(fichier, ".part")
  erreur <- tryCatch({
    code <- download.file(paste0(base_url, journal$fichier[i]), temporaire, mode = "wb", method = "libcurl")
    if (code != 0 || !archive_valide(temporaire)) stop("Archive non valide")
    if (!file.copy(temporaire, fichier, overwrite = TRUE)) stop("Echec de copie")
    unlink(temporaire)
    ""
  }, error = function(e) conditionMessage(e))
  journal$erreur[i] <- erreur
  journal$statut[i] <- if (erreur == "") "telecharge" else "erreur"
}
write.csv(journal, file.path(racine_meteo, "journal_telechargement.csv"), row.names = FALSE)
print(journal)
if (any(journal$statut == "erreur")) warning("Relancer le script pour les archives en erreur.")
