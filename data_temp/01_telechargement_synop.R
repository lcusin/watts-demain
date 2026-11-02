source(if (file.exists("data_temp/00_chemins.R")) "data_temp/00_chemins.R" else "00_chemins.R", local = TRUE)
# 01 - Télécharger les archives annuelles SYNOP (à lancer depuis le projet).
options(timeout = max(1800, getOption("timeout")))
dossier <- dossier_brut
dir.create(dossier, recursive = TRUE, showWarnings = FALSE)
base_url <- "https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/OBS/SYNOP/"

# Contrôle rapide du format, pas de l'intégrité complète de l'archive.
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

journal <- data.frame(annee = 2012:2026,
                      fichier = paste0("synop_", 2012:2026, ".csv.gz"),
                      statut = "deja_present", erreur = "")

for (i in seq_len(nrow(journal))) {
  fichier <- file.path(dossier, journal$fichier[i])
  cat(journal$annee[i], "\n")
  # Un fichier déjà présent n'est pas actualisé automatiquement.
  if (archive_valide(fichier)) next

  journal$statut[i] <- tryCatch({
    temporaire <- paste0(fichier, ".part")
    code <- download.file(paste0(base_url, journal$fichier[i]),
                          temporaire, mode = "wb", method = "libcurl")
    if (code != 0 || !archive_valide(temporaire)) stop("Archive non valide")
    if (!file.copy(temporaire, fichier, overwrite = TRUE)) stop("Echec de copie")
    unlink(temporaire)
    "telecharge"
  }, error = function(e) {
    journal$erreur[i] <<- conditionMessage(e)
    "erreur"
  })
}

write.csv(journal, file.path(racine_meteo, "journal_telechargement.csv"),
          row.names = FALSE)
print(journal)
if (any(journal$statut == "erreur")) warning("Relancer le script pour les archives en erreur.")
