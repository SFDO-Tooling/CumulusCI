BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"Extid__c" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'Sitwell-Bluth','10');
INSERT INTO "Account" VALUES(2,'Tyrell Corporation','11');
INSERT INTO "Account" VALUES(3,'Morales, Patterson and Shepherd','12');
INSERT INTO "Account" VALUES(4,'Downs PLC','13');
INSERT INTO "Account" VALUES(5,'Patterson-Copeland','14');
INSERT INTO "Account" VALUES(6,'Tucker, Nixon and Romero','15');
INSERT INTO "Account" VALUES(7,'Donovan-Rodriguez','16');
INSERT INTO "Account" VALUES(8,'Harris-Hodges','17');
INSERT INTO "Account" VALUES(9,'Page LLC','18');
INSERT INTO "Account" VALUES(10,'Shepard Ltd','19');
INSERT INTO "Account" VALUES(11,'Frazier-Hester','30');
INSERT INTO "Account" VALUES(12,'Flowers-Reid','31');
INSERT INTO "Account" VALUES(14,'French LLC','32');
INSERT INTO "Account" VALUES(15,'The Bluth Company','20');
INSERT INTO "Account" VALUES(16,'Donovan Group','21');
INSERT INTO "Account" VALUES(17,'Murphy, Esparza and Allen','1');
INSERT INTO "Account" VALUES(18,'Macdonald Inc','2');
INSERT INTO "Account" VALUES(19,'Obrien-Ruiz','3');
INSERT INTO "Account" VALUES(20,'Henry LLC','4');
INSERT INTO "Account" VALUES(23,'Benjamin Ltd','5');
INSERT INTO "Account" VALUES(24,'Golden-Olsen','6');
INSERT INTO "Account" VALUES(25,'Nelson-Cross','7');
INSERT INTO "Account" VALUES(27,'Frazier-Hester','25');
INSERT INTO "Account" VALUES(28,'Flowers-Reid','26');
INSERT INTO "Account" VALUES(29,'Fleming LLC','27');
INSERT INTO "Account" VALUES(30,'French LLC','28');
INSERT INTO "Account" VALUES(31,'Moyer-Casey','9');
INSERT INTO "Account" VALUES(32,'Barker-Thornton','8');
CREATE TABLE "Contact" (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Extid__c" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(1,'Eric','Ayala','21');
INSERT INTO "Contact" VALUES(2,'Audrey','Cain','22');
INSERT INTO "Contact" VALUES(3,'Micheal','Bernard','23');
INSERT INTO "Contact" VALUES(4,'Chloe','Myers','24');
INSERT INTO "Contact" VALUES(5,'Rose','Larson','25');
INSERT INTO "Contact" VALUES(6,'Brent','Ali','26');
INSERT INTO "Contact" VALUES(7,'Julia','Townsend','27');
INSERT INTO "Contact" VALUES(8,'Benjamin','Cunningham','28');
INSERT INTO "Contact" VALUES(9,'Christy','Stanton','29');
INSERT INTO "Contact" VALUES(10,'Sabrina','Roberson','30');
INSERT INTO "Contact" VALUES(11,'Michael','Bluth','31');
INSERT INTO "Contact" VALUES(12,'Javier','Banks','32');
INSERT INTO "Contact" VALUES(13,'Michael','Bluth','43');
INSERT INTO "Contact" VALUES(14,'Kaitlyn','Rubio','34');
INSERT INTO "Contact" VALUES(15,'Jerry','Eaton','35');
INSERT INTO "Contact" VALUES(16,'Gabrielle','Vargas','36');
COMMIT;
