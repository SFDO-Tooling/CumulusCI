BEGIN TRANSACTION;
CREATE TABLE "accounts" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"parent_id" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "accounts" VALUES(1,'Bluth','');
INSERT INTO "accounts" VALUES(2,'Funke-Bluth',1);

CREATE TABLE "cumulusci_id_table" (
	id VARCHAR(255) NOT NULL, 
	sf_id VARCHAR(255)
);
INSERT INTO "cumulusci_id_table" VALUES("accounts-1",'001DEADBEEF');
INSERT INTO "cumulusci_id_table" VALUES("accounts-2",'002DEADBEEF');
COMMIT;
