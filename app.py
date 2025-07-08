import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Analyse des startups - Levées de fonds et indicateurs clés")

uploaded_file = st.file_uploader("Chargez un fichier Excel avec les données des startups", type=["xlsx", "xls"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # Colonnes clés
    required_columns = [
        "Année RCS", "Année entrée incubation", "Année de primolevée",
        "Montant 2021 (si >100K)", "Montant 2022 (si >100K)",
        "Montant 2023 (si >100K)", "Montant 2024 (si >100K)",
        "Indus+Bioéco", "Numérique", "Santé",
        "EXOGENE", "ENDOGENE",
        "Le projet est-il labellisé Deeptech par la BPI ?",
        "Lien recherche publique fr?"
    ]
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        st.error(f"Colonnes manquantes : {missing_cols}")
        st.stop()

    # Pré-traitements
    for col in ["Année RCS", "Année entrée incubation", "Année de primolevée"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in ["Montant 2021 (si >100K)", "Montant 2022 (si >100K)",
                "Montant 2023 (si >100K)", "Montant 2024 (si >100K)"]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    for col in ["Indus+Bioéco", "Numérique", "Santé", "EXOGENE", "ENDOGENE",
                "Le projet est-il labellisé Deeptech par la BPI ?",
                "Lien recherche publique fr?"]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    st.write(f"**Total projets dans les données : {len(df)}**")

    # --- Analyse principale (non filtrée) ---

    # Calcul écarts RCS → levée
    df["Écart RCS → levée"] = df["Année de primolevée"] - df["Année RCS"]
    df["Écart entrée incubation → levée"] = df["Année de primolevée"] - df["Année entrée incubation"]

    st.header("Statistiques globales (toutes données)")

    annees_levée = [2021, 2022, 2023, 2024]
    stats = {}
    for annee in annees_levée:
        col = f"Montant {annee} (si >100K)"
        mask = df[col] > 0
        nb_projets = mask.sum()
        montant_total = int(df.loc[mask, col].sum())
        ecart_moyen = (df.loc[mask, "Année de primolevée"] - df.loc[mask, "Année RCS"]).mean() if nb_projets > 0 else np.nan
        stats[annee] = {
            "Nb projets levés": nb_projets,
            "Montant total levé (€)": montant_total,
            "Délai moyen RCS→Levée (années)": round(ecart_moyen, 2) if not np.isnan(ecart_moyen) else "N/A"
        }
    st.table(pd.DataFrame(stats).T)

    # Âge projets par année de levée (avec choix année référence)
    st.header("Âge des projets par année de levée")

    annee_ref = st.radio(
        "Année de référence pour calcul âge et écarts",
        options=["Année RCS", "Année entrée incubation"],
        index=0,
        key="annee_ref_global"
    )

    age_bins_labels = ["<1 an", "1-2 ans", "2-3 ans", ">3 ans"]
    age_bins_edges = [-np.inf, 1, 2, 3, np.inf]

    table_age_global = pd.DataFrame(0, index=age_bins_labels, columns=annees_levée)
    for annee_lev in annees_levée:
        col_lev = f"Montant {annee_lev} (si >100K)"
        mask_lev = df[col_lev] > 0
        ages = annee_lev - df.loc[mask_lev, annee_ref]
        tranches = pd.cut(ages, bins=age_bins_edges, labels=age_bins_labels, right=False)
        counts = tranches.value_counts().reindex(age_bins_labels, fill_value=0)
        table_age_global[annee_lev] = counts

    st.dataframe(table_age_global)

    # Levées par tranche et année (tableau + graphique)
    st.header("Répartition des levées par tranche et année")

    bins_labels = ["<500k", "500k-1M", "1M-2M", "2M-5M", ">5M"]
    bins_edges = [-np.inf, 500_000, 1_000_000, 2_000_000, 5_000_000, np.inf]

    df_tranches_global = pd.DataFrame(0, index=bins_labels, columns=annees_levée)
    for annee_lev in annees_levée:
        col_lev = f"Montant {annee_lev} (si >100K)"
        levs = df.loc[df[col_lev] > 0, col_lev]
        tranches = pd.cut(levs, bins=bins_edges, labels=bins_labels, right=False)
        counts = tranches.value_counts().reindex(bins_labels, fill_value=0)
        df_tranches_global[annee_lev] = counts

    st.subheader("Tableau croisé : nombre de levées par tranche et année")
    st.dataframe(df_tranches_global)

    df_tranches_pct = df_tranches_global.div(df_tranches_global.sum(axis=0), axis=1).fillna(0) * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    df_tranches_pct.T.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')
    ax.set_ylabel("Pourcentage des projets (%)")
    ax.set_xlabel("Année de levée")
    ax.set_title("Répartition des levées par tranche (en %)")
    ax.legend(title="Tranches Montant")
    st.pyplot(fig)

    # --- Section filtres par thème en-dessous ---

    st.markdown("---")
    st.header("Analyse par thème : filtres et visualisations")

    def analyse_par_filtre(df_source, filtre_col, label_oui="Oui", label_non="Non"):
        with st.expander(f"Filtrer par {filtre_col}"):
            choix = st.radio(f"Choisissez la valeur à filtrer pour '{filtre_col}':", options=["Tous", label_oui, label_non], key=f"filter_{filtre_col}")
            if choix == label_oui:
                df_filtre = df_source[df_source[filtre_col] == 1]
            elif choix == label_non:
                df_filtre = df_source[df_source[filtre_col] == 0]
            else:
                df_filtre = df_source

            st.write(f"**Nombre de projets retenus : {len(df_filtre)}**")
            if len(df_filtre) == 0:
                st.warning("Aucun projet correspondant à ce filtre.")
                return

            # Réutilisation âge projets
            table_age = pd.DataFrame(0, index=age_bins_labels, columns=annees_levée)
            for annee_lev in annees_levée:
                col_lev = f"Montant {annee_lev} (si >100K)"
                mask_lev = df_filtre[col_lev] > 0
                ages = annee_lev - df_filtre.loc[mask_lev, annee_ref]
                tranches = pd.cut(ages, bins=age_bins_edges, labels=age_bins_labels, right=False)
                counts = tranches.value_counts().reindex(age_bins_labels, fill_value=0)
                table_age[annee_lev] = counts
            st.write("### Âge des projets par année de levée")
            st.dataframe(table_age)

            # Levées par tranche et année (tableau)
            df_tranches = pd.DataFrame(0, index=bins_labels, columns=annees_levée)
            for annee_lev in annees_levée:
                col_lev = f"Montant {annee_lev} (si >100K)"
                levs = df_filtre.loc[df_filtre[col_lev] > 0, col_lev]
                tranches = pd.cut(levs, bins=bins_edges, labels=bins_labels, right=False)
                counts = tranches.value_counts().reindex(bins_labels, fill_value=0)
                df_tranches[annee_lev] = counts

            st.write("### Répartition des levées par tranche et année")
            st.dataframe(df_tranches)

            df_tranches_pct = df_tranches.div(df_tranches.sum(axis=0), axis=1).fillna(0) * 100
            fig, ax = plt.subplots(figsize=(10, 5))
            df_tranches_pct.T.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')
            ax.set_ylabel("Pourcentage des projets (%)")
            ax.set_xlabel("Année de levée")
            ax.set_title(f"Répartition des levées par tranche (en %) - filtre {filtre_col} = {choix}")
            ax.legend(title="Tranches Montant")
            st.pyplot(fig)

    # Filières
    st.subheader("Par filière")
    for filiere_col, label in zip(["Indus+Bioéco", "Numérique", "Santé"], ["Indus+Bioéco", "Numérique", "Santé"]):
        analyse_par_filtre(df, filiere_col, label_oui="1", label_non="0")

    # Deeptech
    st.subheader("Par Deeptech")
    analyse_par_filtre(df, "Le projet est-il labellisé Deeptech par la BPI ?", label_oui="Oui", label_non="Non")

    # Lien recherche
    st.subheader("Par lien recherche publique")
    analyse_par_filtre(df, "Lien recherche publique fr?", label_oui="Oui", label_non="Non")

    # Exogène / Endogène
    st.subheader("Par exogène / endogène")
    with st.expander("Filtrer par Exogène / Endogène"):
        choix_exoendo = st.radio("Choisissez la catégorie à filtrer:", options=["Tous", "EXOGENE", "ENDOGENE"], key="filter_exoendo")
        if choix_exoendo == "EXOGENE":
            df_exoendo = df[df["EXOGENE"] == 1]
        elif choix_exoendo == "ENDOGENE":
            df_exoendo = df[df["ENDOGENE"] == 1]
        else:
            df_exoendo = df

        st.write(f"**Nombre de projets retenus : {len(df_exoendo)}**")
        if len(df_exoendo) > 0:
            # Âge projets
            table_age = pd.DataFrame(0, index=age_bins_labels, columns=annees_levée)
            for annee_lev in annees_levée:
                col_lev = f"Montant {annee_lev} (si >100K)"
                mask_lev = df_exoendo[col_lev] > 0
                ages = annee_lev - df_exoendo.loc[mask_lev, annee_ref]
                tranches = pd.cut(ages, bins=age_bins_edges, labels=age_bins_labels, right=False)
                counts = tranches.value_counts().reindex(age_bins_labels, fill_value=0)
                table_age[annee_lev] = counts
            st.write("### Âge des projets par année de levée")
            st.dataframe(table_age)

            # Levées par tranche et année
            df_tranches = pd.DataFrame(0, index=bins_labels, columns=annees_levée)
            for annee_lev in annees_levée:
                col_lev = f"Montant {annee_lev} (si >100K)"
                levs = df_exoendo.loc[df_exoendo[col_lev] > 0, col_lev]
                tranches = pd.cut(levs, bins=bins_edges, labels=bins_labels, right=False)
                counts = tranches.value_counts().reindex(bins_labels, fill_value=0)
                df_tranches[annee_lev] = counts

            st.write("### Répartition des levées par tranche et année")
            st.dataframe(df_tranches)

            df_tranches_pct = df_tranches.div(df_tranches.sum(axis=0), axis=1).fillna(0) * 100
            fig, ax = plt.subplots(figsize=(10, 5))
            df_tranches_pct.T.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')
            ax.set_ylabel("Pourcentage des projets (%)")
            ax.set_xlabel("Année de levée")
            ax.set_title(f"Répartition des levées par tranche (en %) - filtre Exogène/Endogène = {choix_exoendo}")
            ax.legend(title="Tranches Montant")
            st.pyplot(fig)

else:
    st.info("Veuillez charger un fichier Excel pour commencer l'analyse.")
