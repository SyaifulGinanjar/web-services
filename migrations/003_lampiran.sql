-- Fitur 3 & 4: lampiran file untuk karyawan, service, dan service tambahan
CREATE TABLE lampiran (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  owner_type    VARCHAR(20) NOT NULL,
  owner_id      INT NOT NULL,
  nama_file     VARCHAR(255) NOT NULL,
  storage_key   VARCHAR(500) NOT NULL,
  content_type  VARCHAR(100) NOT NULL,
  ukuran        INT NOT NULL,
  keterangan    VARCHAR(100) NULL,
  uploaded_by   VARCHAR(50) NOT NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_lampiran_owner (owner_type, owner_id)
);
