-- Datumsspalten von VARCHAR(64) auf DATETIME umstellen
-- entspricht der Alembic-Revision b7d41e9c8a02
--
-- Nur nötig, wenn Alembic nicht läuft (alembic.ini liegt nicht im Repository).
-- Sonst genügt:  alembic upgrade head
--
-- VORHER UNBEDINGT SICHERN:
--   mysqldump -h HOST -u BENUTZER -p DATENBANK > sicherung.sql
--
-- Die App muss währenddessen nicht abgeschaltet werden, die Umstellung dauert
-- bei dieser Datenmenge rund zwei Sekunden. Sicherer ist es trotzdem, sie
-- kurz nicht zu benutzen: zwischen UPDATE und ALTER geschriebene Zeilen
-- könnten sonst wieder im alten Format landen.

-- Schritt 1: Text vereinheitlichen.
-- 'T' wird zum Leerzeichen, Sekundenbruchteile werden abgeschnitten.
-- Abschneiden statt runden: CAST würde 06:26:57.620538 zu 06:26:58 aufrunden.
UPDATE `users`         SET `ts`            = SUBSTRING_INDEX(REPLACE(`ts`,            'T', ' '), '.', 1) WHERE `ts`            IS NOT NULL;
UPDATE `coffee_log`    SET `ts`            = SUBSTRING_INDEX(REPLACE(`ts`,            'T', ' '), '.', 1) WHERE `ts`            IS NOT NULL;
UPDATE `payments`      SET `ts`            = SUBSTRING_INDEX(REPLACE(`ts`,            'T', ' '), '.', 1) WHERE `ts`            IS NOT NULL;
UPDATE `invoices`      SET `monat`         = SUBSTRING_INDEX(REPLACE(`monat`,         'T', ' '), '.', 1) WHERE `monat`         IS NOT NULL;
UPDATE `invoices`      SET `ts`            = SUBSTRING_INDEX(REPLACE(`ts`,            'T', ' '), '.', 1) WHERE `ts`            IS NOT NULL;
UPDATE `invoices`      SET `bezahlt`       = SUBSTRING_INDEX(REPLACE(`bezahlt`,       'T', ' '), '.', 1) WHERE `bezahlt`       IS NOT NULL;
UPDATE `invoices`      SET `email_versand` = SUBSTRING_INDEX(REPLACE(`email_versand`, 'T', ' '), '.', 1) WHERE `email_versand` IS NOT NULL;
UPDATE `mietzahlungen` SET `monat`         = SUBSTRING_INDEX(REPLACE(`monat`,         'T', ' '), '.', 1) WHERE `monat`         IS NOT NULL;
UPDATE `mietzahlungen` SET `ts`            = SUBSTRING_INDEX(REPLACE(`ts`,            'T', ' '), '.', 1) WHERE `ts`            IS NOT NULL;

-- Schritt 2: Spaltentypen ändern.
ALTER TABLE `users`         MODIFY `ts`            DATETIME NOT NULL;
ALTER TABLE `coffee_log`    MODIFY `ts`            DATETIME NOT NULL;
ALTER TABLE `payments`      MODIFY `ts`            DATETIME NOT NULL;
ALTER TABLE `invoices`      MODIFY `monat`         DATETIME NOT NULL;
ALTER TABLE `invoices`      MODIFY `ts`            DATETIME NOT NULL;
ALTER TABLE `invoices`      MODIFY `bezahlt`       DATETIME NULL;
ALTER TABLE `invoices`      MODIFY `email_versand` DATETIME NULL;
ALTER TABLE `mietzahlungen` MODIFY `monat`         DATETIME NOT NULL;
ALTER TABLE `mietzahlungen` MODIFY `ts`            DATETIME NOT NULL;

-- Schritt 3: Indizes. (user_id, ts) für "ein Monat einer Person",
-- (ts) für "ein Monat, alle Personen" -- dort hilft der zusammengesetzte
-- Index nicht, weil die erste Spalte nicht eingeschränkt wird.
CREATE INDEX `ix_coffee_log_user_ts`       ON `coffee_log`    (`user_id`, `ts`);
CREATE INDEX `ix_coffee_log_ts`            ON `coffee_log`    (`ts`);
CREATE INDEX `ix_payments_user_ts`         ON `payments`      (`user_id`, `ts`);
CREATE INDEX `ix_payments_ts`              ON `payments`      (`ts`);
CREATE INDEX `ix_invoices_user_monat`      ON `invoices`      (`user_id`, `monat`);
CREATE INDEX `ix_invoices_monat`           ON `invoices`      (`monat`);
CREATE INDEX `ix_mietzahlungen_user_monat` ON `mietzahlungen` (`user_id`, `monat`);
CREATE INDEX `ix_mietzahlungen_monat`      ON `mietzahlungen` (`monat`);

-- Schritt 4: Alembic den neuen Stand mitteilen.
UPDATE `alembic_version` SET `version_num` = 'b7d41e9c8a02';

-- Kontrolle: alle Spalten sollten jetzt 'datetime' sein.
-- SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS
--  WHERE TABLE_SCHEMA = DATABASE()
--    AND COLUMN_NAME IN ('ts', 'monat', 'bezahlt', 'email_versand')
--  ORDER BY TABLE_NAME, COLUMN_NAME;
