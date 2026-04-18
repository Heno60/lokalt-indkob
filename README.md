# 🛒 Lokalt Indkøb

Streamlit-app der sammenligner supermarkedspriser i dit nærområde.

## Hvad er nyt (v2)

- ✅ **eTilbudsavis/Tjek API** erstatter Coop (Rema 1000, Lidl, Aldi, Fakta m.fl.)
- ✅ **Ingen nøgle nødvendig** til eTilbudsavis – anonym session oprettes automatisk
- ✅ **Salling Group API** for realtidspriser (Netto, Føtex, Bilka)
- ⚠️ SuperBrugsen er pt. **ikke** med i eTilbudsavis (fravalgt af Coop i 2025)

## Butiksdækning

| Kæde | API | Nøgle nødvendig |
|---|---|---|
| Netto | Salling Group | ✅ Gratis nøgle |
| Føtex | Salling Group | ✅ Gratis nøgle |
| Bilka | Salling Group | ✅ Gratis nøgle |
| Rema 1000 | eTilbudsavis/Tjek | ❌ Ingen nøgle |
| Lidl | eTilbudsavis/Tjek | ❌ Ingen nøgle |
| Aldi | eTilbudsavis/Tjek | ❌ Ingen nøgle |
| Fakta/365discount | eTilbudsavis/Tjek | ❌ Ingen nøgle |
| SuperBrugsen | ❌ Ingen API tilgængeligt | — |

## Opsætning

### 1. Installer

```bash
pip install -r requirements.txt
```

### 2. Salling API-nøgle (gratis)

1. Gå til [developer.sallinggroup.com](https://developer.sallinggroup.com)
2. Opret gratis konto og generer API-nøgle
3. Opret `.streamlit/secrets.toml`:

```toml
SALLING_API_KEY = "din-nøgle-her"
```

### 3. Kør lokalt

```bash
streamlit run app.py
```

## Deploy (gratis hosting)

1. Push til GitHub (secrets.toml må **ikke** med — se .gitignore)
2. Gå til [share.streamlit.io](https://share.streamlit.io)
3. Vælg dit repo → Settings → Secrets → indsæt `SALLING_API_KEY`
4. Deploy 🎉

## Filstruktur

```
shopping-app/
├── app.py                    # Streamlit app
├── requirements.txt
├── api/
│   ├── salling.py            # Salling Group API (Netto, Føtex, Bilka)
│   └── tjek.py               # eTilbudsavis/Tjek API (Rema, Lidl, Aldi m.fl.)
└── .streamlit/
    ├── config.toml
    └── secrets.toml          # ← Opret selv (ikke i git!)
```

## Tale-input

Virker i **Google Chrome** på Android og desktop. Sig varerne adskilt af korte pauser.
