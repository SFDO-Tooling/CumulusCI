BEGIN TRANSACTION;
CREATE TABLE "accounts" (
	sf_id VARCHAR(255) NOT NULL, 
	"Name" VARCHAR(255), 
	"parent_id" VARCHAR(255), 
	PRIMARY KEY (sf_id)
);
INSERT INTO "accounts" VALUES("001DEADBEEF",'Bluth','');
INSERT INTO "accounts" VALUES("002DEADBEEF",'Funke-Bluth',1);

CREATE TABLE "accounts_sf_ids" (
	id INTEGER NOT NULL, 
	sf_id VARCHAR(255)
);
INSERT INTO "accounts_sf_ids" VALUES(1,'001DEADBEEF');
INSERT INTO "accounts_sf_ids" VALUES(2,'002DEADBEEF');
COMMIT;
