CREATE DATABASE IF NOT EXISTS rhino_gene CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'rhino_app'@'localhost' IDENTIFIED BY 'rhino_app';
CREATE USER IF NOT EXISTS 'rhino_app'@'127.0.0.1' IDENTIFIED BY 'rhino_app';

GRANT ALL PRIVILEGES ON rhino_gene.* TO 'rhino_app'@'localhost';
GRANT ALL PRIVILEGES ON rhino_gene.* TO 'rhino_app'@'127.0.0.1';

FLUSH PRIVILEGES;
