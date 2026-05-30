// =============================================================================
// FSMP Clinical Nutrition Knowledge Graph — Schema & Constraints
// =============================================================================

// ---------- Constraints ----------

// Disease nodes
CREATE CONSTRAINT disease_icd11 IF NOT EXISTS
FOR (d:Disease) REQUIRE d.icd11_code IS UNIQUE;

CREATE CONSTRAINT disease_name IF NOT EXISTS
FOR (d:Disease) REQUIRE d.name IS UNIQUE;

// Surgery nodes
CREATE CONSTRAINT surgery_code IF NOT EXISTS
FOR (s:Surgery) REQUIRE s.code IS UNIQUE;

CREATE CONSTRAINT surgery_name IF NOT EXISTS
FOR (s:Surgery) REQUIRE s.name IS UNIQUE;

// Nutrient nodes
CREATE CONSTRAINT nutrient_name IF NOT EXISTS
FOR (n:Nutrient) REQUIRE n.name IS UNIQUE;

// FSMP Product nodes
CREATE CONSTRAINT fsmp_reg_no IF NOT EXISTS
FOR (p:FSMPProduct) REQUIRE p.nmpa_registration_no IS UNIQUE;

// Drug nodes
CREATE CONSTRAINT drug_atc IF NOT EXISTS
FOR (d:Drug) REQUIRE d.atc_code IS UNIQUE;

CREATE CONSTRAINT drug_generic IF NOT EXISTS
FOR (d:Drug) REQUIRE d.generic_name IS UNIQUE;

// Manufacturer nodes
CREATE CONSTRAINT manufacturer_name IF NOT EXISTS
FOR (m:Manufacturer) REQUIRE m.name IS UNIQUE;

// MetabolicState nodes
CREATE CONSTRAINT metabolic_state_name IF NOT EXISTS
FOR (ms:MetabolicState) REQUIRE ms.name IS UNIQUE;

// ---------- Indexes ----------

CREATE INDEX disease_category IF NOT EXISTS FOR (d:Disease) ON (d.category);
CREATE INDEX fsmp_category IF NOT EXISTS FOR (p:FSMPProduct) ON (p.category);
CREATE INDEX fsmp_target IF NOT EXISTS FOR (p:FSMPProduct) ON (p.target_population);
CREATE INDEX drug_class IF NOT EXISTS FOR (d:Drug) ON (d.drug_class);
CREATE INDEX nutrient_category IF NOT EXISTS FOR (n:Nutrient) ON (n.category);
