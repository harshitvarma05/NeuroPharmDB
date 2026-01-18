import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Base, Drug, DrugInteraction

# Add current directory to path
sys.path.append(os.getcwd())

# Database configuration - using values from what seemed to be implied or standard
# Assuming localhost, root/password or similar. 
# Better to reuse db_connection.py if possible, let's check it.
# from database.db_connection import get_db_connection

def verify_schema():
    print("Verifying schema changes...")
    
    # Connect
    try:
        # We need to use sqlalchemy engine for model creation
        # Using a direct connection string here for simplicity if db_connection doesn't expose engine
        # But let's try to get a session or connection
        # Actually, let's just use the models to create the table.
        
        # NOTE: Using a hardcoded url for local testing if db_connection is complex
        # But let's try to read db_connection first? No, I'll just try to use the existing init logic style.
        # Let's assume the user has a local mysql running.
        
        # I will use the definition from init_database.py if possible, but I don't see it open.
        # Let's assume standard local connection for now, or just print the SQL generated.
        
        from database.db_connection import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Drop table if exists to force update (since we modified schema)
        print("Dropping existing drug_interactions table...")
        session.execute(text("DROP TABLE IF EXISTS drug_interactions"))
        session.commit()
        
        # Re-create tables
        print("Creating tables...")
        Base.metadata.create_all(engine)
        
        # Check if drugs exist, if not create some
        drug1 = session.query(Drug).filter_by(generic_name="TestDrugA").first()
        if not drug1:

            # Looking at Drug model: generic_name, brand_names, drug_class, indications, dosage, side_effects, contraindications
            drug1 = Drug(generic_name="TestDrugA", drug_class="ClassA", indications="None")
            session.add(drug1)
            
        drug2 = session.query(Drug).filter_by(generic_name="TestDrugB").first()
        if not drug2:
            drug2 = Drug(generic_name="TestDrugB", drug_class="ClassB", indications="None")
            session.add(drug2)
            
        session.commit()
        
        # Create Interaction
        print("Creating test interaction...")
        print(f"Drug1 ID: {drug1.id}, Drug2 ID: {drug2.id}")
        
        interaction = DrugInteraction(
            drug_a_id=drug1.id,
            drug_b_id=drug2.id,
            interaction_id="INT-001",
            evidence_level="High",
            severity_score=8,
            neurological_effect="Increased risk of serotonin syndrome",
            severity="Severe",
            description="Bad interaction",
            recommendations="Avoid"
        )
        session.add(interaction)
        session.commit()
        
        # Verify
        print("Verifying inserted data...")
        saved_interaction = session.query(DrugInteraction).filter_by(interaction_id="INT-001").first()
        
        if saved_interaction:
            print(f"SUCCESS: Found interaction {saved_interaction.interaction_id}")
            print(f"Evidence Level: {saved_interaction.evidence_level}")
            print(f"Severity Score: {saved_interaction.severity_score}")
            print(f"Neurological Effect: {saved_interaction.neurological_effect}")
            print(f"Drug A: {saved_interaction.drug_a.generic_name}")
            print(f"Drug B: {saved_interaction.drug_b.generic_name}")
        else:
            print("FAILURE: Could not find inserted interaction")
            
        session.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_schema()
