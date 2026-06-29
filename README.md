# GHOST — Global Heuristic OSINT Search Tool

> Le moteur d'OSINT anti-anonymisation le plus puissant pour les particuliers.

Objectif : tout profil toxique/profil privé doit comprendre que l'anonymat est un mythe.
Aucune info fictive. Aucun fake. Juste des résultats légalement accessibles, bien présentés.

---

## Features v1
- Pseudo checker sur 50+ plateformes (gratuites)
- Email checker (HaveIBeenPwned, Hunter.io, Epieos)
- Reverse Image search (Yandex, Google, TinEye)
- Social Graph mapping (followers suivis, clusters)
- Behavioral fingerprinting (timezone, style, langue)
- Export rapport Markdown JSON
- Dashboard web (Phase B)

## Architecture
```
ghost/
├── src/
│   ├── main.py          # CLI entry point
│   ├── runner.py        # Orchestrateur
│   ├── modules/
│   │   ├── platforms/   # Un fichier par plateforme
│   │   ├── leaks/       # Fuites de données
│   │   ├── image/       # Reverse image
│   │   ├── graph/       # Social graph
│   │   ├── behavior/    # Fingerprinting
│   │   └── report/      # Génération rapport
│   └── utils/
│       ├── http.py      # Requêtes HTTP + rotation UA
│       ├── cache.py     # Cache local
│       └── export.py    # Export JSON/MD
├── config/
│   └── platforms.yaml   # Liste plateformes + URLs
├── data/
│   ├── results/         # Résultats intermédiaires
│   └── reports/         # Rapports finaux
└── requirements.txt
```

## Usage
```bash
python src/main.py --pseudo eth.git --deep
python src/main.py --email test@mail.com --deep
python src/main.py --image photo.jpg --deep
```

## APIs (gratuites)
- GitHub API
- HaveIBeenPwned
- WhatsMyName
- Yandex/Bing/TinEye (scraping)

## License
MIT — usage éthique uniquement.
