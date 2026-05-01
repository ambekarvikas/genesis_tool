CREATE DATABASE IF NOT EXISTS rhino_gene CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'rhino_app'@'localhost' IDENTIFIED BY 'rhino_app';
CREATE USER IF NOT EXISTS 'rhino_app'@'127.0.0.1' IDENTIFIED BY 'rhino_app';

GRANT ALL PRIVILEGES ON rhino_gene.* TO 'rhino_app'@'localhost';
GRANT ALL PRIVILEGES ON rhino_gene.* TO 'rhino_app'@'127.0.0.1';

FLUSH PRIVILEGES;

USE rhino_gene;

CREATE TABLE IF NOT EXISTS interventions (
	id INT PRIMARY KEY AUTO_INCREMENT,
	patient_id INT NOT NULL,
	report_id INT NULL,
	system VARCHAR(50) NOT NULL,
	interventions JSON NOT NULL,
	adherence VARCHAR(20) DEFAULT 'unknown',
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	INDEX idx_interventions_patient (patient_id),
	INDEX idx_interventions_report (report_id),
	INDEX idx_interventions_system (system),
	CONSTRAINT fk_interventions_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
	CONSTRAINT fk_interventions_report FOREIGN KEY (report_id) REFERENCES reports(id)
);
