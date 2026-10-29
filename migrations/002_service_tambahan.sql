-- Fitur 2: kunjungan ulang dengan SPK baru yang merujuk SPK lama (customer)
CREATE TABLE service_tambahan (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  customer_id        INT NOT NULL,
  no_spk_baru        VARCHAR(50) NOT NULL,
  tgl_spk            DATE NOT NULL,
  teknisi_id         INT NULL,
  tanggal_kunjungan  DATE NULL,
  tanggal_selesai    DATE NULL,
  remark_unit        VARCHAR(255) NULL,
  status_pekerjaan   VARCHAR(20) NULL,
  keterangan         TEXT NULL,
  biaya              DECIMAL(15,2) NULL,
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_service_tambahan_spk (no_spk_baru),
  KEY idx_service_tambahan_customer (customer_id),
  KEY idx_service_tambahan_tgl_spk (tgl_spk),
  CONSTRAINT fk_service_tambahan_customer FOREIGN KEY (customer_id) REFERENCES customer (id),
  CONSTRAINT fk_service_tambahan_teknisi FOREIGN KEY (teknisi_id) REFERENCES teknisi (id) ON DELETE SET NULL
);
