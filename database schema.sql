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
    'scrypt:32768:8:1$LDFvokFU5PMqaZsM$fda9590a25719589ff260b67a2ae684b271726bcb9bc69503503e5bb0e7b4daa0fe86e78ad17d638f76304372c4849f0694f08d09a813fff3d11bf76a8a8ba0e048',
    'admin'
);

-- Staff account
INSERT INTO users (name, email, password_hash, role)
VALUES (
    'Staff User',
    'staff@smartshelf.com',
    'scrypt:32768:8:1$XDsXhsxZczPxmV3y$b5b5903b3f9be915ab90da392f3c8186c3d82f577c548f0ad9b432f583421cad054285f246c31ba8ccf0a21f5a6276c2b60bcebba56fc6aff459149e9d013bbe',
    'staff'
);