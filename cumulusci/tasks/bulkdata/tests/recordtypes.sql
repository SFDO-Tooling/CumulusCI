BEGIN TRANSACTION;
CREATE TABLE "Account_rt_mapping" (
	record_type_id VARCHAR(18) NOT NULL, 
	developer_name VARCHAR(255),
	is_person_type BOOLEAN,
	PRIMARY KEY (record_type_id)
);
INSERT INTO "Account_rt_mapping" VALUES('012P0000000bCMdIAM','Organization',0);
INSERT INTO "Account_rt_mapping" VALUES('012P0000000bCQqIAM','Subsidiary',0);
CREATE TABLE accounts (
	sf_id VARCHAR(255) NOT NULL, 
	"Name" VARCHAR(255), 
	"Description" VARCHAR(255), 
	"Street" VARCHAR(255), 
	"City" VARCHAR(255), 
	"State" VARCHAR(255), 
	"PostalCode" VARCHAR(255), 
	"Country" VARCHAR(255), 
	"Phone" VARCHAR(255), 
	"Fax" VARCHAR(255), 
	"Website" VARCHAR(255), 
	"NumberOfEmployees" VARCHAR(255), 
	"AccountNumber" VARCHAR(255), 
	"Site" VARCHAR(255), 
	"Type" VARCHAR(255), 
	"RecordTypeId" VARCHAR(255), 
	parent_id VARCHAR(255), 
	PRIMARY KEY (sf_id)
);
INSERT INTO "accounts" VALUES('001P000001ZgnJYIAZ','','This is the parent account.','111 Main St.','Nowhereton','NE','11111','USA','5055551212','5055551213','www.acme.com','100','1','Local','Prospect','012P0000000bCMdIAM','');
INSERT INTO "accounts" VALUES('001P000001ZgnJZIAZ','','','','','','','','','','','','','','','012P0000000bCQqIAM','001P000001ZgnJYIAZ');
INSERT INTO "accounts" VALUES('001P000001ZgnJaIAJ','','','','','','','','','','','','','','','','');
INSERT INTO "accounts" VALUES('001P000001ZgnTHIAZ','','','','','','','','','','','','','','','012P0000000bCQqIAM','001P000001ZgnJZIAZ');
