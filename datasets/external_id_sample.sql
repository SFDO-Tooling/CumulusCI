BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"Extid__c" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'Sitwell-Bluth','10');
INSERT INTO "Account" VALUES(2,'Pitts-Zimmerman','11');
INSERT INTO "Account" VALUES(3,'Morales, Patterson and Shepherd','12');
INSERT INTO "Account" VALUES(4,'Downs PLC','13');
INSERT INTO "Account" VALUES(5,'Patterson-Copeland','14');
INSERT INTO "Account" VALUES(6,'Tucker, Nixon and Romero','15');
INSERT INTO "Account" VALUES(7,'Donovan-Rodriguez','16');
INSERT INTO "Account" VALUES(8,'Harris-Hodges','17');
INSERT INTO "Account" VALUES(9,'Page LLC','18');
INSERT INTO "Account" VALUES(10,'Shepard Ltd','19');
INSERT INTO "Account" VALUES(11,'The Bluth Company','20');
INSERT INTO "Account" VALUES(12,'Donovan Group','21');
INSERT INTO "Account" VALUES(13,'Murphy, Esparza and Allen','1');
INSERT INTO "Account" VALUES(14,'Macdonald Inc','2');
INSERT INTO "Account" VALUES(15,'Obrien-Ruiz','3');
INSERT INTO "Account" VALUES(16,'Henry LLC','4');
INSERT INTO "Account" VALUES(17,'Frazier-Hester','');
INSERT INTO "Account" VALUES(18,'Flowers-Reid','');
INSERT INTO "Account" VALUES(19,'Benjamin Ltd','5');
INSERT INTO "Account" VALUES(20,'Golden-Olsen','6');
INSERT INTO "Account" VALUES(21,'Nelson-Cross','7');
INSERT INTO "Account" VALUES(22,'Fleming LLC','');
INSERT INTO "Account" VALUES(23,'Moyer-Casey','9');
INSERT INTO "Account" VALUES(24,'Barker-Thornton','8');
INSERT INTO "Account" VALUES(25,'French LLC','');
COMMIT;
