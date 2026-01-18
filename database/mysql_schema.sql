
CREATE DATABASE IF NOT EXISTS neuropharmdb;
USE neuropharmdb;


CREATE TABLE IF NOT EXISTS drugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    generic_name VARCHAR(200) NOT NULL UNIQUE,
    brand_names TEXT,
    drug_class VARCHAR(100) NOT NULL,
    indications TEXT,
    dosage VARCHAR(200),
    side_effects TEXT,
    contraindications TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS neurological_conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    icd_code VARCHAR(50),
    category VARCHAR(100),
    description TEXT NOT NULL,
    symptoms TEXT,
    treatment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS drug_interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    drug_a_id INT NOT NULL,
    drug_b_id INT NOT NULL,
    interaction_id VARCHAR(50),
    evidence_level VARCHAR(100),
    severity_score INT,
    neurological_effect TEXT,
    severity ENUM('Mild', 'Moderate', 'Severe') NOT NULL,
    description TEXT NOT NULL,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drug_a_id) REFERENCES drugs(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_b_id) REFERENCES drugs(id) ON DELETE CASCADE,
    CONSTRAINT unique_interaction UNIQUE (drug_a_id, drug_b_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    priority ENUM('Low', 'Medium', 'High') NOT NULL DEFAULT 'Medium',
    alert_type VARCHAR(50),
    patient_id VARCHAR(50),
    status ENUM('Active', 'Resolved', 'Dismissed') NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    doctor VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    user_age INT,
    drug1 VARCHAR(255),
    drug2 VARCHAR(255),
    drug_time VARCHAR(100),
    drug_dosage VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_drug_name ON drugs(generic_name);
CREATE INDEX idx_condition_name ON neurological_conditions(name);
CREATE INDEX idx_alert_patient ON alerts(patient_id);
CREATE INDEX idx_timeline_patient ON timeline_events(patient_id);
