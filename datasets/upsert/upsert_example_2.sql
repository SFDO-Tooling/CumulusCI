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
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(1,'Nichael','Bluth','Michael.Bluth@example.com');
INSERT INTO "Contact" VALUES(2,'George Oscar','Bluth','GOB.Bluth@example.com');
INSERT INTO "Contact" VALUES(3,'Lindsay','Bluth','lindsay.bluth@example.com');
COMMIT;