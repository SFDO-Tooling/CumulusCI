BEGIN TRANSACTION;
CREATE TABLE "accounts" (
	sf_id VARCHAR(255) NOT NULL, 
	"Name" VARCHAR(255), 
	"parent_id" VARCHAR(255), 
	PRIMARY KEY (sf_id)
);
INSERT INTO "accounts" VALUES("001DEADBEEF",'Bluth','');
INSERT INTO "accounts" VALUES("002DEADBEEF",'Funke-Bluth',1);

CREATE TABLE "cumulusci_id_table" (
	id VARCHAR(255) NOT NULL, 
	sf_id VARCHAR(255)
);
INSERT INTO "cumulusci_id_table" VALUES("accounts-1",'001DEADBEEF');
INSERT INTO "cumulusci_id_table" VALUES("accounts-2",'002DEADBEEF');
COMMIT;
