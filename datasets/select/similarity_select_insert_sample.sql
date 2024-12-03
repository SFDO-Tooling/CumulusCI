BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id VARCHAR(255) NOT NULL,
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
	"ParentId" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES('Account-1','Tom Cruise','Some Description','','','','','','','','','','','','123456','','','123','');
INSERT INTO "Account" VALUES('Account-2','Bob The Builder','Some Description','','','','','','','','','','','','123456','','','123','Account-1');
CREATE TABLE "Contact" (
	id VARCHAR(255) NOT NULL,
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
INSERT INTO "Contact" VALUES('Contact-1','Test','Contact','','','','','','','Account-1');
INSERT INTO "Contact" VALUES('Contact-2','Test','Contact','','','','','','','Account-2');
INSERT INTO "Contact" VALUES('Contact-3','Another','Contact','','','','','','','Account-3');
CREATE TABLE "Lead" (
	id VARCHAR(255) NOT NULL,
	"LastName" VARCHAR(255),
	"Company" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Lead" VALUES('Lead-1','First Lead','Salesforce');
INSERT INTO "Lead" VALUES('Lead-2','Second Lead','Salesforce');
CREATE TABLE "Event" (
	id VARCHAR(255) NOT NULL,
	"Subject" VARCHAR(255),
	"ActivityDateTime" VARCHAR(255),
	"DurationInMinutes" VARCHAR(255),
	"WhoId" VARCHAR(255),
	"WhatId" VARCHAR(255),
	PRIMARY KEY (id)
);
INSERT INTO "Event" VALUES('Event-1','Test Event 1', '2024-11-07T07:00:00.000+0000', '60','Contact-1','Account-1');
INSERT INTO "Event" VALUES('Event-2','Test Event 2', '2024-11-07T07:00:00.000+0000', '60','Contact-1','');
INSERT INTO "Event" VALUES('Event-3','third record!!!!!!!!', '2024-11-07T07:00:00.000+0000', '31','Contact-2','Account-1');
COMMIT;