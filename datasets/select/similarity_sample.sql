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

INSERT INTO "Account" VALUES('Account-1','Tom Cruise','Some Description','','','','','','','','','','','','12345632','','','123','');
INSERT INTO "Account" VALUES('Account-2','Bob The Builder','Some Description','','','','','','','','','','','','12345632','','','123','Account-1');
INSERT INTO "Account" VALUES('Account-3','Shah Rukh Khan','Bollywood actor','','','','','','','','','','','','12345612','','','123','Account-1');
INSERT INTO "Account" VALUES('Account-4','Aamir Khan','Mr perfectionist, bollywood actor','','','','','','','','','','','','12345623','','','123','Account-1');
INSERT INTO "Account" VALUES('Account-5','Salman Khan','Mr perfectionist, bollywood actor','','','','','','','','','','','','12345623','','','123','Account-1');


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


INSERT INTO "Contact" VALUES('Contact-1','Mr','Contact of Tom Cruise','','','','','','','Account-1');
INSERT INTO "Contact" VALUES('Contact-2','Test','Contact of Bob the Builder','','','','','','','Account-2');
INSERT INTO "Contact" VALUES('Contact-3','Another','Contact of SRK','','','','','','','Account-3');
