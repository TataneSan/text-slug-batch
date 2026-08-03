# text-slug-batch

Generateur de slugs URL-safe en lot — une ligne de texte en entree, un slug en sortie.

Convertit des titres, noms d'articles, ou n'importe quel texte en slugs compatibles SEO : minuscules, accents supprimes (NFKD), ponctuation remplacee par des separateurs, suffixes de dedoublonnage automatiques, longueur maximale configurable.

## Fonctionnalites

- Translitteration Unicode (NFKD) : `Creme brulee a Paris` -> `creme-brulee-a-paris`
- Separateur personnalisable (`-`, `_`, etc.)
- `--max-length N` pour tronquer proprement
- Dedoublonnage automatique : `hello`, `hello-2`, `hello-3`
- Mode `--pairs` (affiche `original => slug`)
- Mode `--json` pour integration pipeline
- Gates CI : `--check`, `--require-change`, `--require-unchanged`, `--require-unique` (exit 2)
- Lecture fichier ou stdin
- Zero dependance, Python >= 3.9

## Installation

```bash
git clone https://github.com/TataneSan/text-slug-batch
cd text-slug-batch
pip install .
```

## Usage

### Slugs simples (stdin)

```bash
cat titles.txt | text-slug-batch
```

```
Hello World!
Mon deuxieme article
```

->

```
hello-world
mon-deuxieme-article
```

### Pairs original => slug

```bash
text-slug-batch titles.txt --pairs
```

```
Hello World! => hello-world
Mon deuxieme article => mon-deuxieme-article
```

### Avec separateur custom et max-length

```bash
text-slug-batch titles.txt -s _ --max-length 30
```

### Gates CI

```bash
# Echoue si des titres ne sont pas deja des slugs valides
text-slug-batch titles.txt --check

# Echoue si des slugs sont dupliques (meme apres suffixe -2)
text-slug-batch titles.txt --require-unique

# Echoue si aucune ligne ne change
text-slug-batch titles.txt --require-change
```

### JSON pour pipelines

```bash
text-slug-batch titles.txt --json | jq '.mappings[] | .slug'
```

## Options

| Option | Description |
|--------|-------------|
| `-s, --separator` | Separateur (defaut: `-`) |
| `--max-length N` | Tronque a N car. max |
| `--keep-case` | Preserver la casse |
| `--no-dedup` | Pas de suffixe -2/-3 pour doublons |
| `--skip-empty` | Ignorer les lignes produisant un slug vide |
| `--pairs` | Output `original => slug` |
| `--json` | Output JSON machine |
| `--check` | Exit 2 si une ligne n'est pas deja un slug valide |
| `--require-change` | Exit 2 si aucune ligne changee |
| `--require-unchanged` | Exit 2 si une ligne a change |
| `--require-unique` | Exit 2 si des slugs sont dupliques |

## Exit codes

| Code | Signification |
|------|---------------|
| 0 | OK |
| 1 | Erreur I/O ou CLI |
| 2 | Gate CI echouee |

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT — voir [LICENSE](LICENSE).
