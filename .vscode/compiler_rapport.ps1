param([string]$Document, [string]$Sortie)

# Priorite a TeX Live pour latexmk, les moteurs LaTeX et Biber.
# Le PATH de Windows reste inchange : seul ce processus est concerne.
$texlive = 'C:\texlive\2025\bin\windows'
$env:Path = "$texlive;$env:Path"
& "$texlive\latexmk.exe" -synctex=1 -interaction=nonstopmode -file-line-error -cd -pdf "-outdir=$Sortie" $Document
$codeCompilation = $LASTEXITCODE

# Garder aussi le PDF final a cote de main.tex, pour le retrouver facilement.
if ($codeCompilation -eq 0) {
    $nomPdf = [System.IO.Path]::GetFileNameWithoutExtension($Document) + '.pdf'
    $pdfCompile = Join-Path $Sortie $nomPdf
    $pdfFinal = Join-Path (Split-Path $Document -Parent) $nomPdf
    if ([System.IO.Path]::GetFullPath($pdfCompile) -ne [System.IO.Path]::GetFullPath($pdfFinal)) {
        Copy-Item -LiteralPath $pdfCompile -Destination $pdfFinal -Force
    }
}
exit $codeCompilation
