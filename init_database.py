from database.db_connection import init_db, create_user, create_drug, create_neuro_effect, add_interaction

def main():
    init_db()

    # --- Sample user for login ---
    # login with: U001 + harshit@example.com
    try:
        create_user("U001", "Harshit", "harshit@example.com", age=20, medical_history="None")
    except Exception:
        pass

    # --- Sample drugs ---
    for d in [
        ("D001", "Sertraline", "SSRI", "Increases serotonin in synapse"),
        ("D002", "Clonazepam", "Benzodiazepine", "GABA-A receptor potentiation"),
        ("D003", "Modafinil", "Wakefulness agent", "Dopamine transporter inhibition"),
    ]:
        try:
            create_drug(*d)
        except Exception:
            pass

    # --- Sample neuro effects (includes requested ones) ---
    effects = [
        ("E001", "Drowsiness", "Sedation", "Medium"),
        ("E010", "Sedation", "Sedation", "High"),
        ("E011", "Weight Gain", "Metabolic", "Medium"),
        ("E012", "Seizures", "Neurological", "High"),
    ]
    for e in effects:
        try:
            create_neuro_effect(*e)
        except Exception:
            pass

    # --- More sample drugs (to demonstrate interactions) ---
    more_drugs = [
        ("D004", "Bupropion", "NDRI", "Norepinephrine/Dopamine reuptake inhibition"),
        ("D005", "Tramadol", "Opioid/Serotonergic", "μ-opioid agonist + serotonin/norepinephrine reuptake inhibition"),
        ("D006", "Olanzapine", "Atypical antipsychotic", "D2/5-HT2 antagonism (metabolic side effects possible)"),
        ("D007", "Valproate", "Mood stabilizer", "Increases GABA; broad antiepileptic"),
    ]
    for d in more_drugs:
        try:
            create_drug(*d)
        except Exception:
            pass

    # --- Sample interactions (requested: Weight Gain / Sedation / Seizures) ---
    # NOTE: Alerts are generated when user adds drugs to Timeline (better logic).
    interactions = [
        # Sedation (high)
        ("I001", "D001", "D002", "E010", 8.5, "Additive CNS depression / sedation"),
        # Seizures (high)
        ("I002", "D004", "D005", "E012", 9.2, "Both may lower seizure threshold; serotonergic/opioid overlap"),
        # Weight gain (high-ish)
        ("I003", "D006", "D007", "E011", 7.4, "Additive metabolic impact: appetite + weight changes"),
    ]
    for it in interactions:
        try:
            add_interaction(*it)
        except Exception:
            pass

    print("Initialized NeuroPharmDB. Run: streamlit run app.py")

if __name__ == "__main__":
    main()
