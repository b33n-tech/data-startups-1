import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analyse des levées de fonds", layout="wide")

st.title("📊 Outil d’analyse des levées de fonds des incubés")

uploaded_file = st.file_uploader("Chargez votre fichier .csv ou .xlsx", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
    else:
        df = pd.read_excel(uploaded_file)

    year_cols = [
        'Montant 2021 (si >100K)',
        'Montant 2022 (si >100K)',
        'Montant 2023 (si >100K)',
        'Montant 2024 (si >100K)'
    ]

    # Convertir les colonnes montant en numérique (float), gérer erreurs
    for col in year_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Synthèse générale ---
    st.header("📈 Synthèse des levées de fonds")

    levées = []
    for _, row in df.iterrows():
        for i, col in enumerate(year_cols):
            montant = row[col]
            if pd.notnull(montant):
                levées.append({
                    'Année': 2021 + i,
                    'Montant': montant
                })

    df_levées = pd.DataFrame(levées)
    total_levées = df_levées.groupby('Année')['Montant'].sum()
    count_levées = df_levées.groupby('Année')['Montant'].count()
    mean_levées = df_levées.groupby('Année')['Montant'].mean()

    synthèse = pd.DataFrame({
        "Nb levées": count_levées,
        "Montant total (€)": total_levées,
        "Montant moyen (€)": mean_levées
    }).astype({"Nb levées": int})

    st.subheader("📌 Informations générales par année")
    st.dataframe(synthèse, use_container_width=True)

    # --- Synthèse par filière ---
    st.header("🏭 Synthèse par filière (Indus+Bioéco, Numérique, Santé)")

    filières = {
        "Indus+Bioéco": "Indus+Bioéco",
        "Numérique": "Numérique",
        "Santé": "Santé"
    }

    synthèse_filière = pd.DataFrame(columns=["Nb levées", "Montant total (€)", "Montant moyen (€)"], index=filières.keys())

    for nom, col_filière in filières.items():
        fdf = df[df[col_filière] == 1]
        montants = fdf[year_cols].values.flatten()
        montants = pd.to_numeric(montants, errors='coerce')
        montants = montants[~pd.isnull(montants)]
        if len(montants) > 0:
            synthèse_filière.loc[nom] = [
                len(montants),
                round(montants.sum(), 2),
                round(montants.mean(), 2)
            ]
        else:
            synthèse_filière.loc[nom] = [0, 0.0, 0.0]

    st.dataframe(synthèse_filière, use_container_width=True)

    # --- Analyse par thème ---
    st.header("🔍 Analyse par thème : filtres et visualisations")

    with st.expander("🎛️ Filtres"):
        selected_filière = st.multiselect("Filière", filières.keys())
        filtre = df.copy()
        if selected_filière:
            mask = pd.Series([False]*len(df))
            for f in selected_filière:
                mask = mask | (df[filières[f]] == 1)
            filtre = filtre[mask]

        deeptech = st.checkbox("Deeptech uniquement", value=False)
        if deeptech:
            filtre = filtre[filtre["Deeptech"] == 1]

        lien = st.checkbox("Lien avec la recherche publique uniquement", value=False)
        if lien:
            filtre = filtre[filtre["Lien recherche publique fr?"] == 1]

        endo_exo = st.selectbox("Origine du projet", ["Tous", "Endogène", "Exogène"])
        if endo_exo == "Endogène":
            filtre = filtre[filtre["ENDOGENE"] == 1]
        elif endo_exo == "Exogène":
            filtre = filtre[filtre["EXOGENE"] == 1]

    st.write(f"Nombre de projets correspondant : {filtre.shape[0]}")

    montant_total = filtre[year_cols].sum().sum()
    montant_moyen = filtre[year_cols].stack().mean()
    st.metric("💰 Montant total filtré", f"{montant_total:,.0f} €")
    st.metric("📊 Montant moyen filtré", f"{montant_moyen:,.0f} €")

    # --- Détail par filière, critère, année ---
    st.header("📂 Détail par filière, par critère et par année")

    catégories = {
        "Endogène": "ENDOGENE",
        "Exogène": "EXOGENE",
        "Lien recherche": "Lien recherche publique fr?",
        "Deeptech": "Deeptech"
    }

    for nom_filière, col_filière in filières.items():
        st.subheader(f"🧬 Filière : {nom_filière}")
        fdf = df[df[col_filière] == 1]
        total_projets = fdf.shape[0] if fdf.shape[0] > 0 else 1  # éviter division par 0

        # Création des colonnes pour chaque année / type d'info
        colonnes = []
        for year in [2021, 2022, 2023, 2024]:
            colonnes.extend([
                f"{year} Montant (€)",
                f"{year} Nb projets",
                f"{year} % projets"
            ])

        tableau = pd.DataFrame(index=catégories.keys(), columns=colonnes)

        for cat_label, cat_col in catégories.items():
            cdf = fdf[fdf[cat_col] == 1]
            for year, col_montant in zip([2021, 2022, 2023, 2024], year_cols):
                montant = cdf[col_montant].sum(skipna=True)
                nb_proj = cdf[cdf[col_montant].notnull()].shape[0]
                pct = (nb_proj / total_projets) * 100 if total_projets > 0 else 0

                tableau.at[cat_label, f"{year} Montant (€)"] = f"{montant:,.0f} €"
                tableau.at[cat_label, f"{year} Nb projets"] = nb_proj
                tableau.at[cat_label, f"{year} % projets"] = f"{pct:.1f} %"

        st.dataframe(tableau.fillna("-"), use_container_width=True)

else:
    st.info("Veuillez importer un fichier CSV ou Excel pour démarrer.")
