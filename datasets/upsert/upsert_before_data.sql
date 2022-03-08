BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'Sitwell-Bluth');
CREATE TABLE "Contact" (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Email" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(1,'Lindsay','Sitwell','lindsay.bluth@example.com');
INSERT INTO "Contact" VALUES(2,'Audrey','Cain','audrey.cain@example.com');
INSERT INTO "Contact" VALUES(3,'Micheal','Bernard','michael.bernard@example.com');
INSERT INTO "Contact" VALUES(4,'Chloe','Myers','Chloe.Myers@example.com');
INSERT INTO "Contact" VALUES(5,'Rose','Larson','Rose.Larson@example.com');
INSERT INTO "Contact" VALUES(6,'Brent','Ali','Brent.Ali@example.com');
INSERT INTO "Contact" VALUES(7,'Julia','Townsend','Julia.Townsend@example.com');
INSERT INTO "Contact" VALUES(8,'Benjamin','Cunningham','Benjamin.Cunningham@example.com');
INSERT INTO "Contact" VALUES(9,'Christy','Stanton','Christy.Stanton@example.com');
INSERT INTO "Contact" VALUES(10,'Sabrina','Roberson','Sabrina.Roberson@example.com');
INSERT INTO "Contact" VALUES(11,'Michael','Bluth','Michael.Bluth@example.com');
INSERT INTO "Contact" VALUES(12,'Javier','Banks','Javier.Banks@example.com');
INSERT INTO "Contact" VALUES(13,'GOB','Bluth','GOB.Bluth@example.com');
INSERT INTO "Contact" VALUES(14,'Kaitlyn','Rubio','Kaitlyn.Rubio@example.com');
INSERT INTO "Contact" VALUES(15,'Jerry','Eaton','Jerry.Eaton@example.com');
INSERT INTO "Contact" VALUES(16,'Gabrielle','Vargas','Gabrielle.Vargas@example.com');
COMMIT;
