BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"AccountNumber" VARCHAR(255), 
	"RecordTypeId" VARCHAR(255), 
	"IsPersonAccount" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'Sitwell-Bluth', "12345", '0125j000000bo4yAAA','true');
INSERT INTO "Account" VALUES(2,'John-Doe', "456789", '0125j000000bo53AAA','false');
INSERT INTO "Account" VALUES(3,'Jane-Doe', "422", '0125j000000bo53AAA','false');
CREATE TABLE "Account_rt_mapping" (
	record_type_id VARCHAR(18) NOT NULL, 
	developer_name VARCHAR(255), 
	is_person_type BOOLEAN, 
	PRIMARY KEY (record_type_id)
);
INSERT INTO "Account_rt_mapping" VALUES('0125j000000RqVkAAK','HH_Account',0);
INSERT INTO "Account_rt_mapping" VALUES('0125j000000RqVlAAK','Organization',0);
INSERT INTO "Account_rt_mapping" VALUES('0125j000000bo4yAAA','PersonAccount',1);
INSERT INTO "Account_rt_mapping" VALUES('0125j000000bo53AAA','PersonAccount',0);
COMMIT;