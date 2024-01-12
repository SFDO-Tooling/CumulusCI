BEGIN TRANSACTION;
CREATE TABLE "Account" (
	"id" VARCHAR(255) NOT NULL, 
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
INSERT INTO "Account" VALUES("Account-1",'alpha','','','Baker St.','','','','','','','','','','','','','');
INSERT INTO "Account" VALUES("Account-2",'beta','','','Baker St.','','','','','','','','','','','','','');
INSERT INTO "Account" VALUES("Account-3",'gamma','','','Baker St.','','','','','','','','','','','','','');

CREATE TABLE "Contact" (
	"id" VARCHAR(255) NOT NULL, 
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
INSERT INTO "Contact" VALUES("Contact-1",'alphass','Mannwereerevhefwingefew','','krithvtffder@example.com','','','','','Account-1');
INSERT INTO "Contact" VALUES("Contact-2",'betasss','Blackefefererf','','kathjvhryn85@exaerfemple.com','','','','','Account-2');
INSERT INTO "Contact" VALUES("Contact-3",'deltasss','Hunteererbhjbefrewererfef','','dfdfvgh@example.com','','','','','Account-3');
INSERT INTO "Contact" VALUES("Contact-4",'gammasss','Carererfbhjhjbrlsonere','','johnmjbbhontddfgfdcsdcsces@example.com','','','','','');
CREATE TABLE "Event" (
	"id" VARCHAR(255) NOT NULL, 
	"Subject" VARCHAR(255), 
	"DurationInMinutes" VARCHAR(255), 
	"ActivityDateTime" VARCHAR(255), 
	"WhoId" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Event" VALUES("Event-1",'helllo','60','2024-01-10T05:30:00.000Z','Contact-1');
INSERT INTO "Event" VALUES("Event-2",'newer','60','2024-01-10T05:30:00.000Z','Lead-1');

CREATE TABLE "Lead" (
	"id" VARCHAR(255) NOT NULL, 
	"LastName" VARCHAR(255), 
	"Company" VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Lead" VALUES("Lead-1",'deltassssds','Farmers Coop. of Florida');
INSERT INTO "Lead" VALUES("Lead-2",'gauramm','Abbott Insurance');

COMMIT;
