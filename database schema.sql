CREATE DATABASE smartshelf_db;
USE smartshelf_db;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    role ENUM('admin', 'staff') DEFAULT 'staff'
);

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(80),
    supplier VARCHAR(100),
    unit_price DECIMAL(10,2),
    expiry_date DATE,
    reorder_level INT DEFAULT 10
);

CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    quantity INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    quantity INT NOT NULL,
    sale_date DATE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    alert_type VARCHAR(50),
    message VARCHAR(255),
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    predicted_demand INT,
    recommended_reorder_qty INT,
    generated_on DATE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);


INSERT INTO products (name, category, supplier, unit_price, expiry_date, reorder_level)
VALUES ('Milk', 'Dairy', 'Nestle', 3.50, '2026-07-01', 10);
USE smartshelf_db;

INSERT INTO inventory (product_id, quantity)
VALUES (1, 50);

UPDATE products
SET expiry_date = '2026-05-26'
WHERE product_id = 1;

-- Admin account
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'Admin User',
    'admin@smartshelf.com',
    'scrypt:32768:8:1$RDOy9BIJXCKwCpSN$d006f074198de07c3804ad521815e9756595a8c6be873f520e18edbb711bfe8aac57a3a1b9b8974ab08811923299dd2db926ab5c347cddf0449f9174f0acd0bf',
    'admin'
);

-- Staff account
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'Staff User',
    'staff@smartshelf.com',
    'scrypt:32768:8:1$gM89VguGrqVYVJ6f$5ded188a22c1cd670cdc35ca6460e59c7b3ceae3f88ca3fed24fe2c50b5e56f90d6603673b5c9929b9f3721631611f1c34dda9fee64067e55735ee23372b7e6d',
    'staff'
);
