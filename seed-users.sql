USE smartshelf_db;

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
