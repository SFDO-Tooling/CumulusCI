BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"Extid__c" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'Bluth-Sitwell','10');
INSERT INTO "Account" VALUES(2,'PKD Corporation','11');
INSERT INTO "Account" VALUES(23,'Benny Ltd','5');
CREATE TABLE "Contact" (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Extid__c" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(3,'Bernard','Cusinard','23');
INSERT INTO "Contact" VALUES(12,'Javier','Bardem','32');
COMMIT;
