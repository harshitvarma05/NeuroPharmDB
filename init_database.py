from database.db_connection import (
    init_db,
    create_user,
    create_drug,
    create_neuro_effect,
    add_interaction
)

def main():
    init_db()

    # --- Demo accounts for login ---
    # Patient login: U001 + harshit@example.com
    # Doctor/Admin login: DOC001 + doctor@neuropharmdb.com

    # DO NOT swallow errors; print them so you can debug
    try:
        create_user(
            user_id="U001",
            name="Harshit",
            email="harshit@example.com",
            role="patient",
            age=20,
            medical_history="None"
        )
        print("Created/updated patient demo user: U001")
    except Exception as e:
        print("Patient creation error:", e)

    try:
        create_user(
            user_id="DOC001",
            name="Doctor Admin",
            email="doctor@neuropharmdb.com",
            role="admin",
            age=None,
            medical_history=None
        )
        print("Created/updated doctor demo user: DOC001")
    except Exception as e:
        print("Doctor creation error:", e)

    # --- Sample drugs ---
    for d in [
        ("D001", "Sertraline", "SSRI", "Increases serotonin in synapse"),
        ("D002", "Clonazepam", "Benzodiazepine", "GABA-A receptor potentiation"),
        ("D003", "Modafinil", "Wakefulness agent", "Dopamine transporter inhibition"),
        ("D008", "Diazepam", "Benzodiazepine", "GABA-A receptor potentiation"),
    ]:
        try:
            create_drug(*d)
        except Exception as e:
            print("Drug insert error:", d[0], e)

    # --- Sample neuro effects ---
    effects = [
        ("E001", "Drowsiness", "Sedation", "Medium"),
        ("E010", "Sedation", "Sedation", "High"),
        ("E011", "Weight Gain", "Metabolic", "Medium"),
        ("E012", "Seizures", "Neurological", "High"),
        ("E013", "Dizziness", "Neurological", "Medium"),
    ]
    for e in effects:
        try:
            create_neuro_effect(*e)
        except Exception as ex:
            print("Neuro effect insert error:", e[0], ex)

    # --- More sample drugs ---
    more_drugs = [
        ("D004", "Bupropion", "NDRI", "Norepinephrine/Dopamine reuptake inhibition"),
        ("D005", "Tramadol", "Opioid/Serotonergic", "μ-opioid agonist + serotonin/norepinephrine reuptake inhibition"),
        ("D006", "Olanzapine", "Atypical antipsychotic", "D2/5-HT2 antagonism (metabolic side effects possible)"),
        ("D007", "Valproate", "Mood stabilizer", "Increases GABA; broad antiepileptic"),
    ]
    for d in more_drugs:
        try:
            create_drug(*d)
        except Exception as e:
            print("Drug insert error:", d[0], e)

    # --- Sample interactions ---
    interactions = [
        ("I001", "D001", "D002", "E010", 8.5, "Additive CNS depression / sedation"),
        ("I004", "D001", "D008", "E013", 5.8, "Possible additive CNS effects (dizziness/drowsiness)"),
        ("I002", "D004", "D005", "E012", 9.2, "Both may lower seizure threshold; serotonergic/opioid overlap"),
        ("I003", "D006", "D007", "E011", 7.4, "Additive metabolic impact: appetite + weight changes"),
    ]
    for it in interactions:
        try:
            add_interaction(*it)
        except Exception as e:
            print("Interaction insert error:", it[0], e)

    print("Initialized NeuroPharmDB. Run: streamlit run app.py")

if __name__ == "__main__":
    main()
