BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	PRIMARY KEY (id)
);
CREATE TABLE "Contact" (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Email" VARCHAR(255),
	"Ext_id__c"  VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(11,'Nichael','Bluth','Michael.Bluth@example.com', 1);
INSERT INTO "Contact" VALUES(12,'JaJavier','Banks','Javier.Banks@example.com', 2);
INSERT INTO "Contact" VALUES(13,'George Oscar','Bluth','GOB.Bluth@example.com', 3);
INSERT INTO "Contact" VALUES(1, 'Annyong', 'Bluth', 'Annyong.Bluth@example.com', 4);
COMMIT;
