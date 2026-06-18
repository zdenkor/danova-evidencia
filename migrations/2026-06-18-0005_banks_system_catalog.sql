-- Migration: 2026-06-18-0005
-- Date: 2026-06-18
-- Description: Add Slovak banks to system catalog

-- Banky podľa NBS directory_ic_dps_sr.pdf
INSERT OR IGNORE INTO system_catalog (kategoria, kod, nazov, hodnota, popis, je_aktivny) VALUES
('banka', 'NBSRSKBX', 'Národná banka Slovenska', 'NBSRSKBX', 'Národná banka Slovenska', 1),
('banka', 'SPSRSKBA', 'Štátna pokladnica', 'SPSRSKBA', 'Štátna pokladnica', 1),
('banka', 'GIBASKBX', 'Slovenská sporiteľňa', 'GIBASKBX', 'Slovenská sporiteľňa, a.s.', 1),
('banka', 'SUBASKBX', 'Všeobecná úverová banka', 'SUBASKBX', 'Všeobecná úverová banka, a.s.', 1),
('banka', 'TATRSKBX', 'Tatra banka', 'TATRSKBX', 'Tatra banka, a.s.', 1),
('banka', 'CEKOSKBX', 'ČSOB', 'CEKOSKBX', 'ČSOB banka, a.s.', 1),
('banka', 'OTPVSKBX', 'OTP Banka Slovensko', 'OTPVSKBX', 'OTP Banka Slovensko, a.s.', 1),
('banka', 'KOMASK2X', 'Prima banka Slovensko', 'KOMASK2X', 'Prima banka Slovensko, a.s.', 1),
('banka', 'RZBASKBX', 'Raiffeisen Bank International', 'RZBASKBX', 'Raiffeisen Bank International AG', 1),
('banka', 'INGBSKBX', 'ING Bank', 'INGBSKBX', 'ING Bank N.V.', 1),
('banka', 'CITISKBA', 'Citibank Europe', 'CITISKBA', 'Citibank Europe plc', 1),
('banka', 'JTBASKBX', 'J&T Banka', 'JTBASKBX', 'J&T BANKA, a.s.', 1),
('banka', 'POBNSKBA', 'Poštová banka', 'POBNSKBA', 'Poštová banka, a.s.', 1),
('banka', 'LUBASKBX', 'Sberbank Slovensko', 'LUBASKBX', 'Sberbank Slovensko, a.s.', 1),
('banka', 'BREASKBX', 'mBank', 'BREASKBX', 'mBank S.A.', 1),
('banka', 'UNCRSKBX', 'UniCredit Bank', 'UNCRSKBX', 'UniCredit Bank Czech Republic and Slovakia, a.s.', 1),
('banka', 'FIOZSKBA', 'Fio banka', 'FIOZSKBA', 'Fio banka, a.s.', 1),
('banka', 'PRVASKBA', 'Privatbanka', 'PRVASKBA', 'Privatbanka, a.s.', 1),
('banka', 'OBKLSKBA', 'Oberbank AG', 'OBKLSKBA', 'Oberbank AG', 1),
('banka', 'BFKKSKBB', 'BKS Bank AG', 'BFKKSKBB', 'BKS Bank AG', 1),
('banka', 'KODBSKBX', 'KDB Bank Europe', 'KODBSKBX', 'KDB Bank Europe Ltd.', 1),
('banka', 'WUEHSKBA', 'Wüstenrot hypotečná banka', 'WUEHSKBA', 'Wüstenrot hypotečná banka, a.s.', 1),
('banka', 'DEUTSKBX', 'Deutsche Bank AG', 'DEUTSKBX', 'Deutsche Bank AG', 1),
('banka', 'MIDLSKBX', 'HSBC Continental Europe', 'MIDLSKBX', 'HSBC Continental Europe', 1),
('banka', 'KOMBSKBA', 'Komerční banka Bratislava', 'KOMBSKBA', 'Komerční banka Bratislava, a.s.', 1),
('banka', 'BNPASKBX', 'BNP Paribas Personal Finance', 'BNPASKBX', 'BNP Paribas Personal Finance S.A.', 1),
('banka', 'ECBKSKB1', 'Európska centrálna banka', 'ECBKSKB1', 'Európska centrálna banka', 1),
('banka', 'EXPNCZPP', 'ExpoBank', 'EXPNCZPP', 'ExpoBank CZ, a.s.', 1),
('banka', 'NVRBSK22', '365.bank', 'NVRBSK22', '365.bank, a.s.', 1);

INSERT OR IGNORE INTO schema_version (version, description) VALUES ('2026-06-18-0005', 'Add Slovak banks to system catalog');
