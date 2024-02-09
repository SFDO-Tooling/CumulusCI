BEGIN TRANSACTION;

CREATE TABLE "contacts" (
	id VARCHAR(255) NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "contacts" VALUES("Contact-1",'Alpha','gamma');
INSERT INTO "contacts" VALUES("Contact-2",'Temp','Bluth');

CREATE TABLE "events" (
	id VARCHAR(255) NOT NULL, 
	"Subject" VARCHAR(255), 
	"WhoId" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "events" VALUES("Event-1",'helllo','Contact-1');
INSERT INTO "events" VALUES("Event-2",'newer','Lead-2');

CREATE TABLE "leads" (
	id VARCHAR(255) NOT NULL, 
	"LastName" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "leads" VALUES("Lead-1",'Boxer');
INSERT INTO "leads" VALUES("Lead-2",'Cotton');

CREATE TABLE "cumulusci_id_table" (
	id VARCHAR(255) NOT NULL, 
	sf_id VARCHAR(255)
);
INSERT INTO "cumulusci_id_table" VALUES("Contact-1",'001DEADBEEF');
INSERT INTO "cumulusci_id_table" VALUES("Contact-2",'002DEADBEEF');
INSERT INTO "cumulusci_id_table" VALUES("Lead-1",'001DEADBEEA');
INSERT INTO "cumulusci_id_table" VALUES("Lead-2",'002DEADBEEE');
COMMIT;