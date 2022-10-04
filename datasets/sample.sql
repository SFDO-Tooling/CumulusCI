BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL,
	"Name" VARCHAR(255),
	"Description" VARCHAR(255),
	"NumberOfEmployees" VARCHAR(255),
	"BillingStreet" VARCHAR(255),
	"BillingCity" VARCHAR(255),
	"BillingState" VARCHAR(255),
	"BillingPostalCode" VARCHAR(255),
	"BillingCountry" VARCHAR(255),
	"ShippingStreet" VARCHAR(255),
	"ShippingCity" VARCHAR(255),
	"ShippingState" VARCHAR(255),
	"ShippingPostalCode" VARCHAR(255),
	"ShippingCountry" VARCHAR(255),
	"Phone" VARCHAR(255),
	"Fax" VARCHAR(255),
	"Website" VARCHAR(255),
	"AccountNumber" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'Sample Account for Entitlements','','','','','','','','','','','','','','','','');
INSERT INTO "Account" VALUES(2,'The Bluth Company','Solid as a rock','6','','','','','','','','','','','','','','');
INSERT INTO "Account" VALUES(3,'Camacho PLC','Total logistical task-force','59908','2852 Caleb Village Suite 428','Porterside','Maryland','14525','Canada','6070 Davidson Rapids','Gibsonland','North Dakota','62676','Lithuania','221.285.1033','+1-081-230-6073x31438','http://jenkins.info/category/tag/tag/terms/','2679965');
CREATE TABLE "Contact" (
	id INTEGER NOT NULL,
	"FirstName" VARCHAR(255),
	"LastName" VARCHAR(255),
	"Salutation" VARCHAR(255),
	"Email" VARCHAR(255),
	"Phone" VARCHAR(255),
	"MobilePhone" VARCHAR(255),
	"Title" VARCHAR(255),
	"Birthdate" VARCHAR(255),
	"AccountId" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(1,'Michael','Bluth','','','','','','','2');
INSERT INTO "Contact" VALUES(2,'Jared','Burnett','Ms.','ja-burnett2011@example.net','372.865.5762x5990','033.134.7156x7943','Systems analyst','2000-04-18','3');
CREATE TABLE "Opportunity" (
	id INTEGER NOT NULL,
	"Name" VARCHAR(255),
	"CloseDate" VARCHAR(255),
	"Amount" VARCHAR(255),
	"StageName" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Opportunity" VALUES(1,'democratic Opportunity','2022-07-27','69.0','In Progress');
INSERT INTO "Opportunity" VALUES(2,'your Opportunity','2022-10-09','76.0','Closed Won');
INSERT INTO "Opportunity" VALUES(3,'heart Opportunity','2022-11-04','32.0','Closed Won');
INSERT INTO "Opportunity" VALUES(4,'treat Opportunity','2022-12-12','137.0','Closed Won');
COMMIT;
